"""Session room backend: audio intake, slot gating, pipeline worker.

One SessionRecord per booking tracks the 6-step pipeline (audio received,
transcribed, notes drafted, notes reviewed, PDF built, email sent); later
steps land in Part C. Recording is allowed inside the slot window (30 min
early to 120 min after the start) unless DEMO_ALLOW_ANYTIME skips the
check. Speaker labels default the first voice to Professor with a swap.
"""
from __future__ import annotations

import uuid
from collections.abc import Callable, Mapping
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from flask import Flask

from ..extensions import db
from ..models import Booking, CaseFile, SessionRecord
from .diagnosis import log_event
from .extraction import save_upload
from .meta_client import MetaSettings
from .transcription import (
    AudioRejected,
    TranscriptionError,
    Transcript,
    Turn,
    diagnosis_keywords,
    maybe_delete_audio,
    transcribe_wav,
    validate_wav,
)

STEP_EVENTS: tuple[str, ...] = (
    "audio_received",
    "transcribed",
    "notes_drafted",
    "notes_reviewed",
    "pdf_built",
    "email_sent",
)

RECORD_EARLY_MINUTES = 30
RECORD_LATE_MINUTES = 120
SESSION_MINUTES = 60

RECORD_STATUS_PENDING = "pending"
RECORD_STATUS_RECEIVED = "received"
RECORD_STATUS_TRANSCRIBED = "transcribed"
RECORD_STATUS_ERROR = "error"

ROLE_PROFESSOR = "Professor"
ROLE_STUDENT = "Student"


def recording_allowed(
    booking: Booking,
    now: datetime | None = None,
    demo_anytime: bool = False,
) -> tuple[bool, str]:
    """Whether recording may start; False carries a human reason.

    The window opens 30 minutes before the slot and closes 120 minutes
    after the start (the 60-minute session plus slack). Naive datetimes
    are read as UTC, matching the stored form.
    """
    if demo_anytime:
        return True, ""
    current = now or datetime.now(timezone.utc).replace(tzinfo=None)
    if current.tzinfo is not None:
        current = current.astimezone(timezone.utc).replace(tzinfo=None)
    start = booking.scheduled_at
    opens = start - timedelta(minutes=RECORD_EARLY_MINUTES)
    closes = start + timedelta(minutes=RECORD_LATE_MINUTES)
    if current < opens:
        return False, "Recording opens 30 minutes before the slot."
    if current > closes:
        return False, "The recording window for this slot has closed."
    return True, ""


def validate_session_audio(filename: str, data: bytes) -> None:
    """Reject non-WAV uploads; deep format checks run after saving."""
    if "." not in filename:
        raise AudioRejected("session audio must be a .wav file")
    if filename.rsplit(".", 1)[1].lower() != "wav":
        raise AudioRejected("session audio must be a .wav file")
    if not data:
        raise AudioRejected("session audio is empty")
    if not data.startswith(b"RIFF"):
        raise AudioRejected("file is not a real WAV (bad signature)")


def save_session_audio(
    filename: str, data: bytes, upload_dir: str | Path
) -> Path:
    """Validate and store session audio; return the absolute path."""
    validate_session_audio(filename, data)
    path = save_upload(data, "wav", Path(upload_dir) / "session_audio")
    try:
        validate_wav(path)
    except AudioRejected:
        path.unlink(missing_ok=True)
        raise
    return path


def get_session_record(booking_id: int) -> SessionRecord | None:
    """The booking's session record, if one exists."""
    return SessionRecord.query.filter_by(booking_id=booking_id).first()


def default_speaker_map(turns: list[Turn] | tuple[Turn, ...]) -> dict[str, str]:
    """First voice to speak is Professor; every other is Student."""
    mapping: dict[str, str] = {}
    for turn in sorted(turns, key=lambda item: (item.start_ms, item.end_ms)):
        if turn.speaker not in mapping:
            mapping[turn.speaker] = (
                ROLE_PROFESSOR if not mapping else ROLE_STUDENT
            )
    return mapping


def swap_speaker_map(mapping: Mapping[str, str]) -> dict[str, str]:
    """Flip Professor and Student roles for every mapped speaker."""
    flipped = {ROLE_PROFESSOR: ROLE_STUDENT, ROLE_STUDENT: ROLE_PROFESSOR}
    return {
        speaker: flipped.get(role, role) for speaker, role in mapping.items()
    }


def mapped_turns(record: SessionRecord) -> list[dict[str, Any]]:
    """Stored turns with display names resolved through the speaker map."""
    mapping = record.speaker_map or {}
    return [
        {
            "speaker": turn.get("speaker", "?"),
            "name": mapping.get(turn.get("speaker", ""), turn.get("speaker", "?")),
            "start_ms": turn.get("start_ms", 0),
            "end_ms": turn.get("end_ms", 0),
            "text": turn.get("text", ""),
        }
        for turn in record.turns or []
        if isinstance(turn, dict)
    ]


def _transcribe_fn_from_env() -> Callable[[Path], Transcript]:
    """Real transcribe call: settings, diagnosis-agnostic keywords hook."""

    def _transcribe(path: Path, keywords: list[str] | None = None) -> Transcript:
        settings = MetaSettings.from_env()
        if not settings.model_transcribe:
            raise TranscriptionError("META_MODEL_TRANSCRIBE is not set")
        return transcribe_wav(
            path,
            model=settings.model_transcribe,
            api_key=settings.api_key,
            base_url=settings.base_url,
            language_bias=["English"],
            keywords=keywords or [],
        )

    return _transcribe


def reset_record_for_upload(
    record: SessionRecord, audio_path: Path, run_id: str
) -> None:
    """Point the record at a new run, clearing prior run output."""
    record.consent = True
    record.status = RECORD_STATUS_RECEIVED
    record.run_id = run_id
    record.audio_path = str(audio_path)
    record.transcript = None
    record.turns = None
    record.speaker_map = None
    record.notes = None
    record.pdf_path = None


def run_session_pipeline(
    app: Flask,
    booking_id: int,
    run_id: str,
    transcribe_fn: Callable[..., Transcript] | None = None,
) -> None:
    """Transcribe the booking's audio: steps 1-2 of the 6-step pipeline.

    Designed for a background thread; opens its own app context. Later
    steps (notes onward) extend this worker in Part C. Audio is deleted
    after transcription unless KEEP_AUDIO=true. Failures mark ``error``.
    """
    with app.app_context():
        record = get_session_record(booking_id)
        if record is None or record.run_id != run_id:
            return  # superseded by a newer upload, or record removed
        try:
            if record.audio_path is None or not Path(record.audio_path).is_file():
                raise TranscriptionError("session audio file is missing")
            log_event(
                run_id, "audio_received",
                "Audio received; transcription started",
                payload={"booking_id": booking_id},
            )
            booking = db.session.get(Booking, booking_id)
            keywords: list[str] = []
            if booking is not None and booking.case_id:
                case = db.session.get(CaseFile, booking.case_id)
                if case is not None:
                    keywords = diagnosis_keywords(case.diagnosis or {})
            transcribe = transcribe_fn or _transcribe_fn_from_env()
            transcript = transcribe(Path(record.audio_path), keywords)
            record.transcript = transcript.full_text
            record.turns = [
                {
                    "speaker": turn.speaker,
                    "start_ms": turn.start_ms,
                    "end_ms": turn.end_ms,
                    "text": turn.text,
                }
                for turn in transcript.turns
            ]
            record.speaker_map = default_speaker_map(transcript.turns)
            record.status = RECORD_STATUS_TRANSCRIBED
            db.session.commit()
            log_event(
                run_id, "transcribed",
                f"Transcribed {len(transcript.turns)} turns "
                f"({len(record.speaker_map)} speakers)",
                payload={
                    "turns": len(transcript.turns),
                    "speakers": sorted(record.speaker_map),
                },
            )
        except Exception as exc:
            db.session.rollback()
            record = get_session_record(booking_id)
            if record is not None and record.run_id == run_id:
                record.status = RECORD_STATUS_ERROR
                db.session.commit()
                log_event(
                    run_id, "run_failed", f"Session pipeline failed: {exc}",
                    status="error",
                )
        finally:
            record = get_session_record(booking_id)
            if (
                record is not None
                and record.run_id == run_id
                and record.audio_path
            ):
                if maybe_delete_audio(record.audio_path):
                    record.audio_path = None
                    db.session.commit()


def new_run_id() -> str:
    """Unique run id for one upload's pipeline run."""
    return f"session-{uuid.uuid4().hex[:12]}"
