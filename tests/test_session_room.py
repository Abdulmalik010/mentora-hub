"""Session room tests: access, consent, gating, worker, mapping. No network."""
from __future__ import annotations

import io
import itertools
import wave
from datetime import datetime, timedelta, timezone
from pathlib import Path

from flask import Flask

from app.extensions import db
from app.models import Booking, RunEvent, SessionRecord, User
from app.services.booking import create_booking
from app.services.booking_workflow import apply_transition
from app.services.sessions import (
    default_speaker_map,
    mapped_turns,
    recording_allowed,
    run_session_pipeline,
    swap_speaker_map,
)
from app.services.transcription import Transcript, Turn
from tests.test_booking import login_sample_student, seed_booking_case
from tests.test_professor import login_professor

_key_counter = itertools.count(1)


def wav_bytes(
    *, channels: int = 1, width: int = 2, rate: int = 16000,
    seconds: float = 1.0,
) -> bytes:
    """Small in-memory WAV for upload tests."""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(channels)
        handle.setsampwidth(width)
        handle.setframerate(rate)
        frames = int(rate * seconds)
        handle.writeframes(b"\0" * frames * channels * width)
    return buffer.getvalue()


def accepted_booking(start: datetime | None = None) -> Booking:
    """Accepted booking for professor 12 (starts `start` or soon)."""
    case, prof_id = seed_booking_case()
    booking = create_booking(
        student_id=case.student_id, professor_id=prof_id, case_id=case.id,
        start_naive_utc=start or naive_utc_plus(minutes=10),
        consent_share_diagnosis=True,
        idempotency_key=f"tok-room-{next(_key_counter)}",
    )
    professor = db.session.get(User, prof_id)
    assert professor is not None
    return apply_transition(booking.id, "accept", actor_user=professor)


def naive_utc_plus(**delta: int) -> datetime:
    """Naive UTC now shifted (mirrors the stored datetime form)."""
    return datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(**delta)


def fake_transcript(path: Path, keywords: list[str] | None = None) -> Transcript:
    """Two turns, deliberately out of chronological order."""
    assert keywords is not None  # worker always passes keyword hints
    return Transcript(
        turns=(
            Turn("SPEAKER_1", 5000, 8000, "Second voice."),
            Turn("SPEAKER_0", 0, 4000, "First voice."),
        ),
        full_text="Second voice. First voice.",
    )


def upload(
    client, booking_id: int, payload: bytes,  # type: ignore[no-untyped-def]
    filename: str = "clip.wav", consent: bool = True,
):
    """POST an audio upload to the room."""
    data: dict[str, object] = {}
    if consent:
        data["consent"] = "yes"
    data["audio"] = (io.BytesIO(payload), filename)
    return client.post(
        f"/sessions/{booking_id}/room/audio", data=data,
        content_type="multipart/form-data",
    )


def test_room_access_control(app: Flask) -> None:
    """Anonymous bounces; parties enter; strangers 404."""
    booking = accepted_booking()
    client = app.test_client()
    assert client.get(f"/sessions/{booking.id}/room").status_code == 302
    login_sample_student(client)
    assert client.get(f"/sessions/{booking.id}/room").status_code == 200
    login_professor(client, 12)
    assert client.get(f"/sessions/{booking.id}/room").status_code == 200
    login_professor(client, 2)
    assert client.get(f"/sessions/{booking.id}/room").status_code == 404
    assert client.get("/sessions/9999/room").status_code == 404


def test_room_meeting_link_follows_reveal_rule(app: Flask) -> None:
    """Accepted rooms link out; requested rooms explain the wait."""
    booking = accepted_booking()
    client = app.test_client()
    login_sample_student(client)
    html = client.get(f"/sessions/{booking.id}/room").get_data(as_text=True)
    assert (booking.meeting_url or "") in html
    assert "Transcribed" in html and "Email sent" in html  # 6 steps render
    case, prof_id = seed_booking_case()
    requested = create_booking(
        student_id=case.student_id, professor_id=prof_id, case_id=case.id,
        start_naive_utc=naive_utc_plus(hours=2),
        consent_share_diagnosis=True, idempotency_key="tok-room-req-1",
    )
    pending = client.get(f"/sessions/{requested.id}/room").get_data(as_text=True)
    assert "appears once the professor accepts" in pending


def test_recording_window_gating(app: Flask) -> None:
    """Panel shows inside the window; outside shows the reason instead."""
    inside = accepted_booking(naive_utc_plus(minutes=10))
    far_seed = accepted_booking(naive_utc_plus(hours=3))
    assert far_seed.id != inside.id
    client = app.test_client()
    login_sample_student(client)
    assert "consent" in client.get(
        f"/sessions/{inside.id}/room"
    ).get_data(as_text=True).lower()
    far = far_seed
    html = client.get(f"/sessions/{far.id}/room").get_data(as_text=True)
    assert "Recording opens 30 minutes before the slot." in html
    assert 'name="consent"' not in html
    app.config["DEMO_ALLOW_ANYTIME"] = True
    flagged = client.get(f"/sessions/{far.id}/room").get_data(as_text=True)
    assert 'name="consent"' in flagged


def test_recording_allowed_boundaries(app: Flask) -> None:
    """Window edges are inclusive; the flag bypasses everything."""
    booking = accepted_booking(naive_utc_plus(hours=1))
    start = booking.scheduled_at
    assert recording_allowed(
        booking, start - timedelta(minutes=30)
    )[0] is True
    assert recording_allowed(
        booking, start + timedelta(minutes=120)
    )[0] is True
    assert recording_allowed(
        booking, start - timedelta(minutes=31)
    )[0] is False
    assert recording_allowed(
        booking, start + timedelta(minutes=121)
    )[0] is False
    assert recording_allowed(
        booking, start + timedelta(days=9), demo_anytime=True
    ) == (True, "")


def test_audio_requires_consent(app: Flask, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """No checkbox, no record, no pipeline launch."""
    launched: list[tuple[int, str]] = []
    monkeypatch.setattr(
        "app.blueprints.cases._launch_session_pipeline",
        lambda a, b, r: launched.append((b, r)),
    )
    app.config["DEMO_ALLOW_ANYTIME"] = True
    booking = accepted_booking()
    client = app.test_client()
    login_sample_student(client)
    response = upload(client, booking.id, wav_bytes(), consent=False)
    assert response.status_code == 303
    assert SessionRecord.query.filter_by(booking_id=booking.id).count() == 0
    assert launched == []


def test_audio_upload_validation(app: Flask, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Non-WAV, stereo and missing files are refused with a flash."""
    launched: list[tuple[int, str]] = []
    monkeypatch.setattr(
        "app.blueprints.cases._launch_session_pipeline",
        lambda a, b, r: launched.append((b, r)),
    )
    app.config["DEMO_ALLOW_ANYTIME"] = True
    booking = accepted_booking()
    client = app.test_client()
    login_sample_student(client)
    for payload, filename in (
        (b"ID3 junk", "clip.mp3"),
        (wav_bytes(channels=2), "stereo.wav"),
        (b"not a wav at all", "clip.wav"),
    ):
        response = upload(client, booking.id, payload, filename)
        assert response.status_code == 303
    assert SessionRecord.query.filter_by(booking_id=booking.id).count() == 0
    assert launched == []
    missing = client.post(
        f"/sessions/{booking.id}/room/audio", data={"consent": "yes"}
    )
    assert missing.status_code == 303
    assert launched == []


def test_audio_upload_launches_pipeline(app: Flask, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Valid upload stores audio, resets the record, launches the worker."""
    launched: list[tuple[int, str]] = []
    monkeypatch.setattr(
        "app.blueprints.cases._launch_session_pipeline",
        lambda a, b, r: launched.append((b, r)),
    )
    app.config["DEMO_ALLOW_ANYTIME"] = True
    booking = accepted_booking()
    client = app.test_client()
    login_sample_student(client)
    response = upload(client, booking.id, wav_bytes())
    assert response.status_code == 303
    record = SessionRecord.query.filter_by(booking_id=booking.id).one()
    assert record.consent is True
    assert record.status == "received"
    assert record.run_id and launched == [(booking.id, record.run_id)]
    assert record.audio_path is not None and Path(record.audio_path).is_file()
    assert "session_audio" in record.audio_path


def test_upload_outside_window_blocked(app: Flask) -> None:
    """The slot check also guards the upload endpoint, not just the panel."""
    booking = accepted_booking(naive_utc_plus(hours=3))
    client = app.test_client()
    login_sample_student(client)
    response = upload(client, booking.id, wav_bytes())
    assert response.status_code == 303
    assert SessionRecord.query.filter_by(booking_id=booking.id).count() == 0


def test_pipeline_transcribes_and_cleans_up(app: Flask, tmp_path: Path) -> None:
    """Worker persists turns + mapping, deletes audio, logs both steps."""
    booking = accepted_booking()
    tmp = tmp_path / "audio"
    tmp.mkdir()
    audio = tmp / "clip.wav"
    audio.write_bytes(wav_bytes())
    record = SessionRecord(
        booking_id=booking.id, consent=True, status="received",
        run_id="run-room-1", audio_path=str(audio),
    )
    db.session.add(record)
    db.session.commit()
    run_session_pipeline(app, booking.id, "run-room-1", fake_transcript)
    db.session.refresh(record)
    assert record.status == "transcribed"
    assert record.transcript == "Second voice. First voice."
    assert len(record.turns or []) == 2
    assert record.speaker_map == {"SPEAKER_0": "Professor", "SPEAKER_1": "Student"}
    assert not audio.exists()  # deleted unless KEEP_AUDIO
    assert record.audio_path is None
    types = [
        event.type
        for event in RunEvent.query.filter_by(run_id="run-room-1")
        .order_by(RunEvent.seq).all()
    ]
    assert types == ["audio_received", "transcribed"]


def test_pipeline_keep_audio_and_failure(
    app: Flask, tmp_path: Path, monkeypatch  # type: ignore[no-untyped-def]
) -> None:
    """KEEP_AUDIO preserves the file; missing audio marks error."""
    booking = accepted_booking()
    tmp = tmp_path / "audio"
    tmp.mkdir()
    audio = tmp / "clip.wav"
    audio.write_bytes(wav_bytes())
    record = SessionRecord(
        booking_id=booking.id, consent=True, status="received",
        run_id="run-room-1", audio_path=str(audio),
    )
    db.session.add(record)
    db.session.commit()
    monkeypatch.setenv("KEEP_AUDIO", "true")
    run_session_pipeline(app, booking.id, "run-room-1", fake_transcript)
    db.session.refresh(record)
    assert record.status == "transcribed"
    assert audio.exists()
    monkeypatch.delenv("KEEP_AUDIO", raising=False)

    record.run_id = "run-room-2"
    record.audio_path = str(tmp / "gone.wav")
    record.status = "received"
    db.session.commit()
    run_session_pipeline(app, booking.id, "run-room-2", fake_transcript)
    db.session.refresh(record)
    assert record.status == "error"
    failed = RunEvent.query.filter_by(
        run_id="run-room-2", type="run_failed"
    ).one()
    assert failed.status == "error"


def test_pipeline_superseded_run_is_noop(app: Flask) -> None:
    """A stale worker run touches nothing when a new upload won."""
    booking = accepted_booking()
    record = SessionRecord(
        booking_id=booking.id, consent=True, status="received",
        run_id="run-room-2", audio_path=None,
    )
    db.session.add(record)
    db.session.commit()
    run_session_pipeline(app, booking.id, "run-room-1", fake_transcript)
    db.session.refresh(record)
    assert record.status == "received"
    assert RunEvent.query.filter_by(run_id="run-room-1").count() == 0


def test_speaker_mapping_default_and_swap() -> None:
    """First voice is Professor; swap flips every role."""
    turns = (
        Turn("SPEAKER_1", 5000, 8000, "b"),
        Turn("SPEAKER_0", 0, 4000, "a"),
        Turn("SPEAKER_2", 9000, 10000, "c"),
    )
    mapping = default_speaker_map(turns)
    assert mapping == {
        "SPEAKER_0": "Professor",
        "SPEAKER_1": "Student",
        "SPEAKER_2": "Student",
    }
    assert swap_speaker_map(mapping) == {
        "SPEAKER_0": "Student",
        "SPEAKER_1": "Professor",
        "SPEAKER_2": "Professor",
    }
    assert swap_speaker_map(swap_speaker_map(mapping)) == mapping


def test_swap_view_flips_mapping(app: Flask) -> None:
    """One click swaps roles; strangers 404; empty rooms flash."""
    booking = accepted_booking()
    client = app.test_client()
    login_sample_student(client)
    assert client.post(
        f"/sessions/{booking.id}/room/speakers/swap"
    ).status_code == 303
    record = SessionRecord(
        booking_id=booking.id, consent=True, status="transcribed",
        run_id="run-room-1",
        turns=[{"speaker": "SPEAKER_0", "start_ms": 0, "end_ms": 1, "text": "a"}],
        speaker_map={"SPEAKER_0": "Professor", "SPEAKER_1": "Student"},
    )
    db.session.add(record)
    db.session.commit()
    assert client.post(
        f"/sessions/{booking.id}/room/speakers/swap"
    ).status_code == 303
    db.session.refresh(record)
    assert record.speaker_map == {"SPEAKER_0": "Student", "SPEAKER_1": "Professor"}
    assert [turn["name"] for turn in mapped_turns(record)] == ["Student"]
    login_professor(client, 2)
    assert client.post(
        f"/sessions/{booking.id}/room/speakers/swap"
    ).status_code == 404


def test_room_events_poll(app: Flask) -> None:
    """The poll endpoint streams status plus new events only."""
    booking = accepted_booking()
    record = SessionRecord(
        booking_id=booking.id, consent=True, status="received",
        run_id="run-room-1", audio_path=None,
    )
    db.session.add(record)
    db.session.commit()
    called: list[str] = []
    run_session_pipeline(
        app, booking.id, "run-room-1",
        lambda path, keywords: called.append("transcribe"),  # type: ignore[return-value]
    )
    assert called == []  # missing audio fails before transcribing
    client = app.test_client()
    login_sample_student(client)
    first = client.get(f"/sessions/{booking.id}/room/events?after=0").get_json()
    assert first is not None and first["status"] == "error"
    assert [event["type"] for event in first["events"]] == ["run_failed"]
    second = client.get(f"/sessions/{booking.id}/room/events?after=1").get_json()
    assert second is not None and second["events"] == []


def test_reupload_resets_record(app: Flask, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """A second upload supersedes the first run's output entirely."""
    monkeypatch.setattr(
        "app.blueprints.cases._launch_session_pipeline",
        lambda a, b, r: run_session_pipeline(a, b, r, fake_transcript),
    )
    app.config["DEMO_ALLOW_ANYTIME"] = True
    booking = accepted_booking()
    client = app.test_client()
    login_sample_student(client)
    upload(client, booking.id, wav_bytes())
    record = SessionRecord.query.filter_by(booking_id=booking.id).one()
    assert record.status == "transcribed"
    first_run = record.run_id
    upload(client, booking.id, wav_bytes())
    db.session.refresh(record)
    assert record.run_id != first_run
    assert record.status == "transcribed"  # sync fake re-ran
    assert record.transcript == "Second voice. First voice."


def test_config_upload_cap_raised(app: Flask) -> None:
    """Flask cap fits a 9:30 WAV; document cap stays 10 MB in code."""
    from app.services.extraction import MAX_UPLOAD_BYTES

    assert app.config["MAX_CONTENT_LENGTH"] == 20 * 1024 * 1024
    assert MAX_UPLOAD_BYTES == 10 * 1024 * 1024
