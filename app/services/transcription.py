"""Session transcription via Muse Voice Transcribe (docs-verified shape).

Contract (Meta docs, ``/docs/speech-to-text``, as probed by
``scripts/check_meta.py``): multipart ``POST {base}/asr/transcribe`` with a
``request`` JSON part (``mode: DIARIZATION``, ``model``,
``audioEncoding: WAV``, plus ``languageBias`` and ``keywords``) and an
``audio`` part, Bearer auth. Responses carry ``turns`` with per-turn
speaker labels and timestamps; speaker labels are scoped to one
transcription only.

Hard limits enforced in code before any call: WAV/RIFF, mono, 16-bit
PCM, 16 or 24 kHz, at most 10 minutes and 32 MB per request. Retries:
429 with backoff, 500 once. Audio is deleted after transcription
unless ``KEEP_AUDIO=true``.
"""
from __future__ import annotations

import json
import os
import time
import wave
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

TRANSCRIBE_PATH = "/asr/transcribe"
TRANSCRIBE_MODE = "DIARIZATION"
TRANSCRIBE_ENCODING = "WAV"
ALLOWED_SAMPLE_RATES = (16000, 24000)
MAX_AUDIO_BYTES = 32 * 1024 * 1024
MAX_DURATION_S = 600.0
MAX_RECORD_S = 570.0  # 9:30 browser cap: 570s x 32KB/s ~= 18MB < 32MB
MAX_429_ATTEMPTS = 3
MAX_500_ATTEMPTS = 2
RETRY_BACKOFF_S = 2.0
TRANSCRIBE_TIMEOUT_S = 180.0


class TranscriptionError(RuntimeError):
    """The transcribe call failed or returned an unusable response."""


class AudioRejected(ValueError):
    """The audio file violates a hard API constraint (checked pre-call)."""


@dataclass(frozen=True)
class WavInfo:
    """Validated WAV parameters (RIFF, mono, 16-bit PCM)."""

    sample_rate: int
    duration_s: float
    size_bytes: int


@dataclass(frozen=True)
class Turn:
    """One diarized turn: speaker label plus millisecond span."""

    speaker: str
    start_ms: int
    end_ms: int
    text: str


@dataclass(frozen=True)
class Transcript:
    """Full transcription result: turns plus joined text."""

    turns: tuple[Turn, ...]
    full_text: str


def inspect_wav(path: str | Path) -> WavInfo:
    """Read WAV parameters; raise AudioRejected unless RIFF/mono/16-bit."""
    resolved = Path(path)
    try:
        size = resolved.stat().st_size
    except OSError as exc:
        raise AudioRejected(f"cannot read audio file: {exc}") from exc
    try:
        with wave.open(str(resolved), "rb") as handle:
            channels = handle.getnchannels()
            width = handle.getsampwidth()
            rate = handle.getframerate()
            frames = handle.getnframes()
    except (wave.Error, EOFError, OSError) as exc:
        raise AudioRejected(f"not a readable WAV file: {exc}") from exc
    if channels != 1:
        raise AudioRejected(f"WAV must be mono, got {channels} channels")
    if width != 2:
        raise AudioRejected(f"WAV must be 16-bit PCM, got {width * 8}-bit")
    if rate <= 0:
        raise AudioRejected("WAV sample rate is invalid")
    return WavInfo(
        sample_rate=rate, duration_s=frames / rate, size_bytes=size
    )


def validate_wav(path: str | Path) -> WavInfo:
    """Enforce every hard API constraint; return the inspected info."""
    info = inspect_wav(path)
    if info.sample_rate not in ALLOWED_SAMPLE_RATES:
        raise AudioRejected(
            f"WAV sample rate must be 16 or 24 kHz, got {info.sample_rate} Hz"
        )
    if info.duration_s > MAX_DURATION_S:
        raise AudioRejected(
            f"audio is {info.duration_s:.0f}s; the limit is 600s per request"
        )
    if info.size_bytes > MAX_AUDIO_BYTES:
        raise AudioRejected(
            f"audio is {info.size_bytes / 1024 / 1024:.1f} MB; "
            "the limit is 32 MB per request"
        )
    return info


def build_request_part(
    model: str,
    language_bias: list[str] | None = None,
    keywords: list[str] | None = None,
) -> str:
    """Request JSON part: mode, model, encoding, bias, keywords."""
    payload: dict[str, Any] = {
        "mode": TRANSCRIBE_MODE,
        "model": model,
        "audioEncoding": TRANSCRIBE_ENCODING,
    }
    if language_bias:
        payload["languageBias"] = list(language_bias)
    if keywords:
        payload["keywords"] = list(keywords)
    return json.dumps(payload)


def diagnosis_keywords(diagnosis: Mapping[str, Any], limit: int = 20) -> list[str]:
    """Keyword hints: expertise keywords plus salient gap terms.

    Deterministic: expertise keywords first, then gap categories, then
    distinctive words (>= 6 chars, alpha) from gap descriptions.
    """
    seen: list[str] = []

    def _add(term: object) -> None:
        text = str(term).strip().lower()
        if text and text not in seen and len(seen) < limit:
            seen.append(text)

    for keyword in diagnosis.get("expertise_keywords", []) or []:
        _add(keyword)
    for gap in diagnosis.get("gaps", []) or []:
        if not isinstance(gap, dict):
            continue
        _add(gap.get("category", ""))
        for word in str(gap.get("description", "")).split():
            cleaned = "".join(char for char in word if char.isalpha())
            if len(cleaned) >= 6:
                _add(cleaned)
    return seen


def _turn_millis(value: object, *, seconds: bool) -> int | None:
    """Millisecond timestamp from ms- or s-denominated numbers."""
    if isinstance(value, bool):
        return None
    if not isinstance(value, (int, float)):
        return None
    millis = value * 1000.0 if seconds else float(value)
    return int(millis) if millis >= 0 else None


def parse_turns(data: Mapping[str, Any]) -> tuple[Turn, ...]:
    """Turns from the documented shape, with unit-tolerant fallbacks.

    Documented: ``turns: [{speaker, startMs, endMs, transcript}]``.
    Also accepts ``start_ms``/``end_ms`` and second-denominated
    ``start``/``end``. Anything else raises TranscriptionError.
    """
    raw_turns = data.get("turns", [])
    if not isinstance(raw_turns, list) or not raw_turns:
        raise TranscriptionError("transcribe response has no turns")
    turns: list[Turn] = []
    for index, item in enumerate(raw_turns):
        if not isinstance(item, dict):
            raise TranscriptionError(f"turn {index} is not an object")
        speaker = item.get("speaker", item.get("speakerLabel", ""))
        start = _turn_millis(item.get("startMs", item.get("start_ms")), seconds=False)
        end = _turn_millis(item.get("endMs", item.get("end_ms")), seconds=False)
        if start is None:
            start = _turn_millis(item.get("start"), seconds=True)
        if end is None:
            end = _turn_millis(item.get("end"), seconds=True)
        text = str(item.get("transcript", item.get("text", ""))).strip()
        if not str(speaker).strip() or start is None or end is None or not text:
            raise TranscriptionError(f"turn {index} is missing fields")
        turns.append(
            Turn(speaker=str(speaker), start_ms=start, end_ms=end, text=text)
        )
    return tuple(turns)


def transcribe_wav(
    path: str | Path,
    *,
    model: str,
    api_key: str,
    base_url: str,
    language_bias: list[str] | None = None,
    keywords: list[str] | None = None,
    timeout_s: float = TRANSCRIBE_TIMEOUT_S,
    http_post: Callable[..., Any] | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> Transcript:
    """Validate, transcribe (429 backoff, 500 once), return turns + text.

    ``http_post`` defaults to ``httpx.post``; tests inject a fake and a
    recording sleeper. Audio bytes are never logged.
    """
    import httpx  # local import: only this call needs it at runtime

    post = http_post or httpx.post
    info = validate_wav(path)
    if not model:
        raise TranscriptionError("a transcribe model id is required")
    if not api_key:
        raise TranscriptionError("an API key is required")
    url = base_url.rstrip("/") + TRANSCRIBE_PATH
    request_part = build_request_part(model, language_bias, keywords)
    audio_bytes = Path(path).read_bytes()
    attempts_429 = attempts_500 = 0
    delay = RETRY_BACKOFF_S
    while True:
        response = post(
            url,
            files={
                "request": ("request", request_part, "application/json"),
                "audio": (Path(path).name, audio_bytes, "audio/wav"),
            },
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout_s,
        )
        status = response.status_code
        if status == 429 and attempts_429 < MAX_429_ATTEMPTS:
            attempts_429 += 1
            sleep(delay)
            delay *= 2
            continue
        if status >= 500 and attempts_500 < MAX_500_ATTEMPTS - 1:
            attempts_500 += 1
            sleep(RETRY_BACKOFF_S)
            continue
        if status != 200:
            raise TranscriptionError(f"transcribe failed: HTTP {status}")
        try:
            data = response.json()
        except ValueError as exc:
            raise TranscriptionError(
                f"transcribe returned invalid JSON: {exc}"
            ) from exc
        if not isinstance(data, dict):
            raise TranscriptionError("transcribe response is not an object")
        turns = parse_turns(data)
        full_text = " ".join(turn.text for turn in turns)
        return Transcript(turns=turns, full_text=full_text)


def keep_audio() -> bool:
    """True only when KEEP_AUDIO=true (default: delete after transcribing)."""
    return os.environ.get("KEEP_AUDIO", "").strip().lower() == "true"


def maybe_delete_audio(path: str | Path) -> bool:
    """Delete the audio file unless KEEP_AUDIO=true; True when deleted."""
    if keep_audio():
        return False
    try:
        Path(path).unlink()
    except FileNotFoundError:
        pass
    return True
