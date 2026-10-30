"""Transcription tests: WAV validation, request shape, retries, parsing."""
from __future__ import annotations

import json
import struct
import wave
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from app.services import transcription as tx


def write_wav(
    path: Path, *, channels: int = 1, width: int = 2, rate: int = 16000,
    seconds: float = 1.0,
) -> Path:
    """Small valid WAV written with the stdlib (silence)."""
    frames = int(rate * seconds)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(channels)
        handle.setsampwidth(width)
        handle.setframerate(rate)
        handle.writeframes(b"\0" * frames * channels * width)
    return path


def craft_wav_header(
    path: Path, *, channels: int = 1, width: int = 2, rate: int = 16000,
    seconds: float = 610.0,
) -> Path:
    """Header-only WAV claiming `seconds` of audio (no sample data)."""
    frames = int(rate * seconds)
    data_size = frames * channels * width
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + data_size, b"WAVE", b"fmt ", 16, 1, channels,
        rate, rate * channels * width, channels * width, width * 8,
        b"data", data_size,
    )
    path.write_bytes(header)
    return path


def test_valid_wav_passes_inspection(tmp_path: Path) -> None:
    """16 and 24 kHz mono 16-bit WAVs inspect cleanly."""
    info = tx.inspect_wav(write_wav(tmp_path / "a.wav", rate=16000))
    assert (info.sample_rate, info.duration_s) == (16000, 1.0)
    info24 = tx.inspect_wav(write_wav(tmp_path / "b.wav", rate=24000))
    assert info24.sample_rate == 24000
    assert tx.validate_wav(tmp_path / "a.wav").size_bytes > 0


def test_wav_format_rejections(tmp_path: Path) -> None:
    """Stereo, 8-bit, 48 kHz and non-WAV inputs are rejected pre-call."""
    with pytest.raises(tx.AudioRejected, match="mono"):
        tx.validate_wav(write_wav(tmp_path / "stereo.wav", channels=2))
    with pytest.raises(tx.AudioRejected, match="16-bit"):
        tx.validate_wav(write_wav(tmp_path / "eight.wav", width=1))
    with pytest.raises(tx.AudioRejected, match="16 or 24 kHz"):
        tx.validate_wav(write_wav(tmp_path / "hq.wav", rate=48000))
    junk = tmp_path / "junk.wav"
    junk.write_text("not a wav")
    with pytest.raises(tx.AudioRejected, match="readable WAV"):
        tx.validate_wav(junk)
    with pytest.raises(tx.AudioRejected, match="cannot read"):
        tx.validate_wav(tmp_path / "missing.wav")


def test_wav_duration_and_size_limits(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Over-10-minute audio rejected; size guard checked with a low cap."""
    with pytest.raises(tx.AudioRejected, match="600s"):
        tx.validate_wav(craft_wav_header(tmp_path / "long.wav", seconds=610.0))
    small = write_wav(tmp_path / "small.wav", seconds=0.5)
    monkeypatch.setattr(tx, "MAX_AUDIO_BYTES", 100)
    with pytest.raises(tx.AudioRejected, match="32 MB|MB"):
        tx.validate_wav(small)


def test_request_part_shape() -> None:
    """Request JSON carries mode, model, encoding, bias and keywords."""
    part = json.loads(
        tx.build_request_part(
            "muse-voice-transcribe-1.0",
            language_bias=["English"],
            keywords=["econometrics", "regression"],
        )
    )
    assert part == {
        "mode": "DIARIZATION",
        "model": "muse-voice-transcribe-1.0",
        "audioEncoding": "WAV",
        "languageBias": ["English"],
        "keywords": ["econometrics", "regression"],
    }
    minimal = json.loads(tx.build_request_part("m"))
    assert minimal == {"mode": "DIARIZATION", "model": "m", "audioEncoding": "WAV"}


def test_diagnosis_keywords_order_and_cap() -> None:
    """Expertise keywords first, then categories, then long gap words."""
    diagnosis = {
        "expertise_keywords": ["econometrics", "identification"],
        "gaps": [
            {"category": "statistics", "description": "No standard errors reported anywhere."},
            {"category": "methodology", "description": "Weak sampling."},
        ],
    }
    keywords = tx.diagnosis_keywords(diagnosis, limit=8)
    assert keywords[:2] == ["econometrics", "identification"]
    assert "statistics" in keywords and "methodology" in keywords
    assert "standard" in keywords  # long gap word kept
    assert "no" not in keywords  # short words dropped
    assert len(tx.diagnosis_keywords(diagnosis, limit=3)) == 3
    assert tx.diagnosis_keywords({}) == []


def test_parse_turns_shapes() -> None:
    """Documented ms shape plus snake_case and seconds fallbacks parse."""
    turns = tx.parse_turns(
        {
            "turns": [
                {"speaker": "SPEAKER_0", "startMs": 0, "endMs": 1500,
                 "transcript": "Hello."},
                {"speakerLabel": "SPEAKER_1", "start_ms": 1500,
                 "end_ms": 3000, "text": "Hi."},
                {"speaker": "SPEAKER_0", "start": 3.0, "end": 4.5,
                 "transcript": "Again."},
            ]
        }
    )
    assert [(t.speaker, t.start_ms, t.end_ms, t.text) for t in turns] == [
        ("SPEAKER_0", 0, 1500, "Hello."),
        ("SPEAKER_1", 1500, 3000, "Hi."),
        ("SPEAKER_0", 3000, 4500, "Again."),
    ]
    with pytest.raises(tx.TranscriptionError, match="no turns"):
        tx.parse_turns({"turns": []})
    with pytest.raises(tx.TranscriptionError, match="missing fields"):
        tx.parse_turns({"turns": [{"speaker": "S", "startMs": 0}]})


class FakeHttp:
    """Scripted HTTP responses recording calls and sleep delays."""

    def __init__(self, responses: list[Any]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []
        self.sleeps: list[float] = []

    def post(self, url: str, **kwargs: Any) -> Any:
        """Serve the next scripted response, recording the call."""
        self.calls.append({"url": url, **kwargs})
        return self.responses.pop(0)

    def sleep(self, delay: float) -> None:
        """Record backoff delays instead of waiting."""
        self.sleeps.append(delay)


def ok_response() -> SimpleNamespace:
    """Successful diarization payload with two turns."""
    return SimpleNamespace(
        status_code=200,
        json=lambda: {
            "turns": [
                {"speaker": "SPEAKER_0", "startMs": 0, "endMs": 1200,
                 "transcript": "Welcome back."},
                {"speaker": "SPEAKER_1", "startMs": 1200, "endMs": 2500,
                 "transcript": "Thanks, let's review."},
            ]
        },
    )


def test_transcribe_success_shape(tmp_path: Path) -> None:
    """Success posts multipart with auth and returns turns plus text."""
    audio = write_wav(tmp_path / "clip.wav")
    http = FakeHttp([ok_response()])
    result = tx.transcribe_wav(
        audio, model="muse-voice-transcribe-1.0", api_key="k",
        base_url="https://api.meta.ai/v1", language_bias=["English"],
        keywords=["econometrics"], http_post=http.post, sleep=http.sleep,
    )
    assert [turn.speaker for turn in result.turns] == ["SPEAKER_0", "SPEAKER_1"]
    assert result.full_text == "Welcome back. Thanks, let's review."
    assert len(http.calls) == 1
    call = http.calls[0]
    assert call["url"] == "https://api.meta.ai/v1/asr/transcribe"
    assert call["headers"] == {"Authorization": "Bearer k"}
    assert set(call["files"]) == {"request", "audio"}
    request_json = json.loads(call["files"]["request"][1])
    assert request_json["keywords"] == ["econometrics"]
    assert request_json["languageBias"] == ["English"]
    assert http.sleeps == []


def test_transcribe_retries_429_with_backoff(tmp_path: Path) -> None:
    """429s back off exponentially, then the success is returned."""
    audio = write_wav(tmp_path / "clip.wav")
    denied = SimpleNamespace(status_code=429)
    http = FakeHttp([denied, denied, ok_response()])
    result = tx.transcribe_wav(
        audio, model="m", api_key="k", base_url="https://x",
        http_post=http.post, sleep=http.sleep,
    )
    assert len(result.turns) == 2
    assert http.sleeps == [2.0, 4.0]
    assert len(http.calls) == 3


def test_transcribe_gives_up_after_429s(tmp_path: Path) -> None:
    """Three 429 retries exhausted surfaces HTTP 429."""
    audio = write_wav(tmp_path / "clip.wav")
    http = FakeHttp([SimpleNamespace(status_code=429)] * 5)
    with pytest.raises(tx.TranscriptionError, match="HTTP 429"):
        tx.transcribe_wav(
            audio, model="m", api_key="k", base_url="https://x",
            http_post=http.post, sleep=http.sleep,
        )
    assert len(http.calls) == 4  # initial + 3 retries


def test_transcribe_retries_500_once(tmp_path: Path) -> None:
    """A 500 gets exactly one retry; a second 500 raises."""
    audio = write_wav(tmp_path / "clip.wav")
    http = FakeHttp([SimpleNamespace(status_code=500), ok_response()])
    assert len(
        tx.transcribe_wav(
            audio, model="m", api_key="k", base_url="https://x",
            http_post=http.post, sleep=http.sleep,
        ).turns
    ) == 2
    assert http.sleeps == [2.0]
    http2 = FakeHttp(
        [SimpleNamespace(status_code=500), SimpleNamespace(status_code=500)]
    )
    with pytest.raises(tx.TranscriptionError, match="HTTP 500"):
        tx.transcribe_wav(
            audio, model="m", api_key="k", base_url="https://x",
            http_post=http2.post, sleep=http2.sleep,
        )
    assert len(http2.calls) == 2


def test_transcribe_bad_payloads_raise(tmp_path: Path) -> None:
    """Invalid JSON, non-objects and turn-less responses raise."""
    audio = write_wav(tmp_path / "clip.wav")

    def _bad_json() -> Any:
        raise ValueError("nope")

    for response in (
        SimpleNamespace(status_code=200, json=_bad_json),
        SimpleNamespace(status_code=200, json=lambda: [1, 2]),
        SimpleNamespace(status_code=200, json=lambda: {"turns": []}),
    ):
        http = FakeHttp([response])
        with pytest.raises(tx.TranscriptionError):
            tx.transcribe_wav(
                audio, model="m", api_key="k", base_url="https://x",
                http_post=http.post, sleep=http.sleep,
            )


def test_transcribe_validates_before_http(tmp_path: Path) -> None:
    """Bad audio, missing model and missing key never reach the network."""
    stereo = write_wav(tmp_path / "stereo.wav", channels=2)
    http = FakeHttp([ok_response()])
    with pytest.raises(tx.AudioRejected):
        tx.transcribe_wav(
            stereo, model="m", api_key="k", base_url="https://x",
            http_post=http.post, sleep=http.sleep,
        )
    good = write_wav(tmp_path / "good.wav")
    with pytest.raises(tx.TranscriptionError, match="model"):
        tx.transcribe_wav(
            good, model="", api_key="k", base_url="https://x",
            http_post=http.post, sleep=http.sleep,
        )
    with pytest.raises(tx.TranscriptionError, match="API key"):
        tx.transcribe_wav(
            good, model="m", api_key="", base_url="https://x",
            http_post=http.post, sleep=http.sleep,
        )
    assert http.calls == []


def test_audio_deletion_default_and_keep(
    tmp_path: Path, monkeypatch  # type: ignore[no-untyped-def]
) -> None:
    """Audio is deleted after transcription unless KEEP_AUDIO=true."""
    first = write_wav(tmp_path / "first.wav")
    monkeypatch.delenv("KEEP_AUDIO", raising=False)
    assert tx.keep_audio() is False
    assert tx.maybe_delete_audio(first) is True
    assert not first.exists()
    assert tx.maybe_delete_audio(first) is True  # missing file is fine
    second = write_wav(tmp_path / "second.wav")
    monkeypatch.setenv("KEEP_AUDIO", "true")
    assert tx.keep_audio() is True
    assert tx.maybe_delete_audio(second) is False
    assert second.exists()
