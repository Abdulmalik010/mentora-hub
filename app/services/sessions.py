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

import json

from ..extensions import db
from ..models import Booking, CaseFile, MemoryNote, SessionRecord, User
from .diagnosis import log_event
from .email_service import STATUS_SENT, send_session_notes_email
from .extraction import save_upload
from .meta_client import MetaSettings, OpenAICompatChatClient
from .notes import (
    apply_review,
    draft_notes,
    memory_note_content,
    review_notes,
)
from .pdf_service import build_session_notes_pdf
from .slots import format_wat
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
RECORD_STATUS_NOTES_DRAFTED = "notes_drafted"
RECORD_STATUS_REVIEWED = "reviewed"
RECORD_STATUS_PDF_BUILT = "pdf_built"
RECORD_STATUS_EMAILED = "emailed"
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
    draft_fn: Callable[[list[dict[str, Any]]], dict[str, Any]] | None = None,
    review_fn: (
        Callable[[dict[str, Any], list[dict[str, Any]]], dict[str, Any]] | None
    ) = None,
) -> None:
    """Run the 6-step session pipeline: audio, transcript, notes, PDF, email.

    Designed for a background thread; opens its own app context. Audio is
    deleted after transcription unless KEEP_AUDIO=true. A failed email
    leaves the status at ``pdf_built`` with an ``email_failed`` event;
    anything else marks ``error``.
    """
    with app.app_context():
        record = get_session_record(booking_id)
        if record is None or record.run_id != run_id:
            return  # superseded by a newer upload, or record removed
        try:
            _run_transcription_step(booking_id, run_id, record, transcribe_fn)
            _run_notes_steps(app, booking_id, run_id, record, draft_fn, review_fn)
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


def _run_transcription_step(
    booking_id: int,
    run_id: str,
    record: SessionRecord,
    transcribe_fn: Callable[..., Transcript] | None,
) -> None:
    """Steps 1-2: receive audio, transcribe with speaker labels."""
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


def _run_notes_steps(
    app: Flask,
    booking_id: int,
    run_id: str,
    record: SessionRecord,
    draft_fn: Callable[[list[dict[str, Any]]], dict[str, Any]] | None,
    review_fn: (
        Callable[[dict[str, Any], list[dict[str, Any]]], dict[str, Any]] | None
    ),
) -> None:
    """Steps 3-6: draft, review, PDF, email, memory note."""
    booking = db.session.get(Booking, booking_id)
    if booking is None:
        raise TranscriptionError("booking is gone; cannot build notes")
    turns_named = mapped_turns(record)
    if draft_fn is None or review_fn is None:
        settings = MetaSettings.from_env()
        client = OpenAICompatChatClient(settings)
        if not settings.model_agent or not settings.model_fast:
            raise TranscriptionError(
                "META_MODEL_AGENT and META_MODEL_FAST are required for notes"
            )
        draft = (draft_fn or (lambda turns: draft_notes(
            client, turns, settings.model_agent, settings.effort_agent
        )))(turns_named)
        verdicts = (review_fn or (lambda draft_, turns: review_notes(
            client, draft_, turns, settings.model_fast, settings.effort_fast
        )))(draft, turns_named)
    else:
        draft = draft_fn(turns_named)
        verdicts = review_fn(draft, turns_named)
    record.status = RECORD_STATUS_NOTES_DRAFTED
    db.session.commit()
    log_event(run_id, "notes_drafted", "Notes drafted; reviewer checking citations")
    final_notes, fidelity = apply_review(draft, verdicts, len(turns_named))
    record.notes = json.dumps(final_notes, ensure_ascii=False)
    record.fidelity_rate = fidelity
    record.status = RECORD_STATUS_REVIEWED
    db.session.commit()
    log_event(
        run_id, "notes_reviewed",
        f"Notes reviewed: fidelity {fidelity:.0%}",
        payload={"fidelity_rate": fidelity},
    )
    student = db.session.get(User, booking.student_id)
    professor = db.session.get(User, booking.professor_id)
    slot = format_wat(booking.scheduled_at) if booking.scheduled_at else "—"
    pdf_bytes = build_session_notes_pdf(
        student_name=student.display_name if student else "?",
        professor_name=professor.display_name if professor else "?",
        slot_text=slot,
        final_notes=final_notes,
        fidelity_rate=fidelity,
    )
    record.status = RECORD_STATUS_PDF_BUILT
    db.session.commit()
    log_event(run_id, "pdf_built", "Notes PDF built from the database")
    db.session.add(
        MemoryNote(
            student_id=booking.student_id,
            session_record_id=record.id,
            content=memory_note_content(final_notes, slot),
        )
    )
    db.session.commit()
    email_log = send_session_notes_email(
        booking.id, run_id, pdf_bytes,
        summary=str(final_notes.get("summary", ""))[:500],
        fidelity_rate=fidelity,
    )
    if email_log is None or email_log.status != STATUS_SENT:
        detail = email_log.error if email_log and email_log.error else "unknown"
        log_event(
            run_id, "email_failed", f"Notes email failed: {detail}",
            status="error",
        )
        return  # notes complete; email can be retried from the room later
    record.status = RECORD_STATUS_EMAILED
    db.session.commit()
    log_event(run_id, "email_sent", "Notes PDF emailed to the student")


def new_run_id() -> str:
    """Unique run id for one upload's pipeline run."""
    return f"session-{uuid.uuid4().hex[:12]}"
