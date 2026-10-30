"""Session notes tests: reviewer, PDF, email, worker steps 3-6. No network."""
from __future__ import annotations

import io
import json
from email import policy
from email.parser import BytesParser
from pathlib import Path
from typing import Any

from flask import Flask
from pypdf import PdfReader

from app.extensions import db
from app.models import EmailLog, MemoryNote, RunEvent, SessionRecord
from app.services import pdf_service
from app.services.email_service import (
    KIND_SESSION_NOTES_BASE,
    build_session_notes_email,
    send_session_notes_email,
)
from app.services.meta_client import ChatResult, complete_json
from app.services.notes import apply_review, draft_notes, review_notes
from app.services.pdf_service import build_session_notes_pdf
from app.services.sessions import run_session_pipeline
from tests.test_booking import login_sample_student
from tests.test_professor import login_professor
from tests.test_session_room import (
    CANNED_DRAFT,
    CANNED_VERDICTS,
    accepted_booking,
    canned_draft,
    canned_review,
    fake_transcript,
    naive_utc_plus,
    upload,
    wav_bytes,
)


class NotesFake:
    """Canned structured payload recording model and schema name."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.calls: list[dict[str, Any]] = []

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: Any = None,
        *,
        model: str,
        response_format: dict[str, Any] | None = None,
        effort: str | None = None,
    ) -> ChatResult:
        """Serve the payload, recording routing details."""
        self.calls.append(
            {"model": model, "effort": effort, "format": response_format}
        )
        return ChatResult(text=json.dumps(self.payload))


def run_full_pipeline(
    app: Flask, tmp_path: Path, booking_id: int | None = None,
    run_id: str = "run-notes-1",
) -> SessionRecord:
    """Transcribed record run through all six steps with canned fakes."""
    booking = accepted_booking(naive_utc_plus(minutes=10)) if booking_id is None else None
    target = booking.id if booking is not None else booking_id
    assert target is not None
    audio = tmp_path / "clip.wav"
    audio.write_bytes(wav_bytes())
    db.session.add(
        SessionRecord(
            booking_id=target, consent=True, status="received",
            run_id=run_id, audio_path=str(audio),
        )
    )
    db.session.commit()
    run_session_pipeline(
        app, target, run_id, fake_transcript, canned_draft, canned_review
    )
    record = SessionRecord.query.filter_by(booking_id=target).one()
    db.session.refresh(record)
    return record


def test_apply_review_filters_and_scores() -> None:
    """Supported kept, partial flagged, unsupported and bad refs dropped."""
    draft = {
        "summary": "s",
        "key_points": [
            {"text": "kept", "turns": [0]},
            {"text": "hedged", "turns": [1]},
            {"text": "invented", "turns": [0]},
        ],
        "action_items": [
            {"owner": "student", "task": "bad ref", "turns": [9]},
            {"owner": "student", "task": "no refs", "turns": []},
            {"owner": "student", "task": "unlabeled", "turns": [1]},
        ],
    }
    verdicts = {
        "verdicts": [
            {"section": "key_points", "index": 0, "label": "supported"},
            {"section": "key_points", "index": 1, "label": "partial",
             "note": "turn 1 only implies it"},
            {"section": "key_points", "index": 2, "label": "unsupported"},
            {"section": "action_items", "index": 0, "label": "supported"},
            {"section": "action_items", "index": 1, "label": "weird"},
        ]
    }
    final, fidelity = apply_review(draft, verdicts, turn_count=2)
    assert [item["text"] for item in final["key_points"]] == ["kept", "hedged"]
    assert "partial" not in final["key_points"][0]
    assert final["key_points"][1]["partial"] is True
    assert "implies it" in final["key_points"][1]["partial_note"]
    assert [item["task"] for item in final["action_items"]] == ["unlabeled"]
    assert final["action_items"][0]["partial"] is True  # fail-safe flag
    assert fidelity == round((1 + 0.5 + 0 + 0 + 0 + 0.5) / 6, 3)


def test_apply_review_empty_and_suggestion() -> None:
    """Empty drafts score 1.0; a bad suggestion is dropped, not kept."""
    final, fidelity = apply_review({"summary": "s"}, {"verdicts": []}, 2)
    assert fidelity == 1.0
    assert final["key_points"] == []
    draft = {
        "summary": "s",
        "next_session_suggestion": {"text": "Meet again.", "turns": [0]},
    }
    dropped, fidelity = apply_review(
        draft,
        {"verdicts": [
            {"section": "next_session_suggestion", "index": 0,
             "label": "unsupported"}
        ]},
        2,
    )
    assert "next_session_suggestion" not in dropped
    assert fidelity == 0.0


def test_draft_and_review_call_shapes() -> None:
    """Draft and review use structured calls with distinct schemas."""
    turns = [{"name": "Professor", "text": "Do X."}]
    draft_fake = NotesFake(CANNED_DRAFT)
    draft = draft_notes(draft_fake, turns, "wonder-x", None)
    assert draft["summary"].startswith("Reviewed OLS")
    assert draft_fake.calls[0]["model"] == "wonder-x"
    assert draft_fake.calls[0]["format"]["json_schema"]["name"] == "SessionNotes"
    review_fake = NotesFake(CANNED_VERDICTS)
    verdicts = review_notes(review_fake, draft, turns, "spark-x", "low")
    assert len(verdicts["verdicts"]) == 4
    assert review_fake.calls[0]["model"] == "spark-x"
    assert review_fake.calls[0]["effort"] == "low"
    assert review_fake.calls[0]["format"]["json_schema"]["name"] == "NotesReview"


def test_pdf_builds_and_parses_back() -> None:
    """PDF bytes carry every section; pypdf reads the text back."""
    final, _ = apply_review(CANNED_DRAFT, CANNED_VERDICTS, turn_count=2)
    pdf_bytes = build_session_notes_pdf(
        student_name="Ada Student", professor_name="Dr. Lars Johansson",
        slot_text="Mon, Nov 3 · 10:00 WAT", final_notes=final,
        fidelity_rate=1.0,
    )
    assert pdf_bytes.startswith(b"%PDF")
    text = PdfReader(io.BytesIO(pdf_bytes)).pages[0].extract_text()
    for snippet in (
        "Mentora Academic Hub", "Ada Student", "Dr. Lars Johansson",
        "robust standard errors", "Rerun regressions", "Friday",
        "Heteroskedasticity", "Review chapter 4", "Fidelity: 100%",
    ):
        assert snippet in text


def test_pdf_flags_partial_and_missing_font(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Partial items show their flag; missing fonts fail fast and loud."""
    final = {
        "summary": "s",
        "key_points": [
            {"text": "Hedged claim.", "turns": [0], "partial": True,
             "partial_note": "turn 0 only implies it"}
        ],
    }
    pdf_bytes = build_session_notes_pdf(
        student_name="s", professor_name="p", slot_text="t",
        final_notes=final, fidelity_rate=0.5,
    )
    text = PdfReader(io.BytesIO(pdf_bytes)).pages[0].extract_text()
    assert "partly verified" in text
    assert "Fidelity: 50%" in text
    monkeypatch.setattr(
        pdf_service, "FONT_REGULAR", Path("/nonexistent/Inter-Regular.ttf")
    )
    import pytest

    with pytest.raises(FileNotFoundError, match="PDF font missing"):
        build_session_notes_pdf(
            student_name="s", professor_name="p", slot_text="t",
            final_notes=final, fidelity_rate=0.5,
        )


def test_session_notes_email_carries_pdf(app: Flask, tmp_path: Path) -> None:
    """Notes email has the PDF attached and parses from the outbox .eml."""
    booking = accepted_booking(naive_utc_plus(minutes=10))
    log = send_session_notes_email(
        booking.id, "run-notes-1", b"%PDF-fake-bytes",
        summary="Reviewed OLS.", fidelity_rate=0.9,
    )
    assert log is not None and log.status == "sent"
    assert log.kind == f"{KIND_SESSION_NOTES_BASE}:run-notes-1"
    outbox = tmp_path / "outbox"
    files = sorted(outbox.iterdir())
    assert len(files) == 1
    message = BytesParser(policy=policy.default).parsebytes(files[0].read_bytes())
    attachments = list(message.iter_attachments())
    assert len(attachments) == 1
    assert attachments[0].get_filename() == f"mentora-session-notes-{booking.id}.pdf"
    assert attachments[0].get_content() == b"%PDF-fake-bytes"
    assert "90%" in message.get_body(preferencelist=("plain",)).get_content()


def test_session_notes_email_idempotent_per_run(app: Flask, tmp_path: Path) -> None:
    """Same run re-sent returns the row; a new run sends a new email."""
    booking = accepted_booking(naive_utc_plus(minutes=10))
    first = send_session_notes_email(
        booking.id, "run-notes-1", b"pdf-1", summary="s", fidelity_rate=1.0
    )
    second = send_session_notes_email(
        booking.id, "run-notes-1", b"pdf-1", summary="s", fidelity_rate=1.0
    )
    assert first is not None and second is not None
    assert first.id == second.id
    third = send_session_notes_email(
        booking.id, "run-notes-2", b"pdf-2", summary="s", fidelity_rate=1.0
    )
    assert third is not None and third.id != first.id
    outbox = tmp_path / "outbox"
    assert len(list(outbox.iterdir())) == 2


def test_worker_runs_all_six_steps(app: Flask, tmp_path: Path) -> None:
    """Full fake run: notes, fidelity, memory, email, ordered events."""
    record = run_full_pipeline(app, tmp_path)
    assert record.status == "emailed"
    notes = json.loads(record.notes or "{}")
    assert notes["summary"].startswith("Reviewed OLS")
    assert len(notes["action_items"]) == 1
    assert record.fidelity_rate == 1.0
    memory = MemoryNote.query.filter_by(session_record_id=record.id).one()
    assert memory.student_id == record.booking.student_id
    assert "Reviewed OLS" in memory.content
    log = EmailLog.query.filter_by(booking_id=record.booking_id).one()
    assert log.kind == f"{KIND_SESSION_NOTES_BASE}:{record.run_id}"
    assert log.status == "sent"
    types = [
        event.type
        for event in RunEvent.query.filter_by(run_id=record.run_id)
        .order_by(RunEvent.seq).all()
    ]
    assert types == [
        "audio_received", "transcribed", "notes_drafted", "notes_reviewed",
        "pdf_built", "email_sent",
    ]


def test_worker_email_failure_keeps_notes(app: Flask, tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """A dead provider parks at pdf_built with notes intact, not error."""
    monkeypatch.setenv("EMAIL_PROVIDER", "bogus")
    record = run_full_pipeline(app, tmp_path)
    assert record.status == "pdf_built"
    assert (record.notes or "") != ""
    assert record.fidelity_rate == 1.0
    assert RunEvent.query.filter_by(
        run_id=record.run_id, type="email_failed"
    ).count() == 1
    assert RunEvent.query.filter_by(
        run_id=record.run_id, type="email_sent"
    ).count() == 0


def test_transcript_view_access(app: Flask) -> None:
    """Parties read the mapped transcript; strangers and empty rooms 404."""
    booking = accepted_booking(naive_utc_plus(minutes=10))
    client = app.test_client()
    login_sample_student(client)
    assert client.get(f"/sessions/{booking.id}/room/transcript").status_code == 404
    record = SessionRecord(
        booking_id=booking.id, consent=True, status="transcribed",
        run_id="run-notes-1",
        turns=[
            {"speaker": "SPEAKER_0", "start_ms": 0, "end_ms": 4000,
             "text": "First voice."}
        ],
        speaker_map={"SPEAKER_0": "Professor"},
    )
    db.session.add(record)
    db.session.commit()
    html = client.get(
        f"/sessions/{booking.id}/room/transcript"
    ).get_data(as_text=True)
    assert "First voice." in html and "Professor" in html
    assert "Swap speakers" in html
    login_professor(client, 12)
    assert client.get(
        f"/sessions/{booking.id}/room/transcript"
    ).status_code == 200
    login_professor(client, 2)
    assert client.get(
        f"/sessions/{booking.id}/room/transcript"
    ).status_code == 404


def test_pdf_download_access(app: Flask, tmp_path: Path) -> None:
    """PDF downloads for parties once notes exist; 404 before that."""
    booking = accepted_booking(naive_utc_plus(minutes=10))
    client = app.test_client()
    login_sample_student(client)
    assert client.get(f"/sessions/{booking.id}/room/notes.pdf").status_code == 404
    record = run_full_pipeline(app, tmp_path, booking_id=booking.id)
    assert record.status == "emailed"
    response = client.get(f"/sessions/{booking.id}/room/notes.pdf")
    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    assert "attachment" in response.headers.get("Content-Disposition", "")
    text = PdfReader(io.BytesIO(response.data)).pages[0].extract_text()
    assert "robust standard errors" in text
    login_professor(client, 2)
    assert client.get(f"/sessions/{booking.id}/room/notes.pdf").status_code == 404


def test_swap_from_transcript_redirects_back(app: Flask) -> None:
    """Swap with next=transcript returns to the transcript view."""
    booking = accepted_booking(naive_utc_plus(minutes=10))
    db.session.add(
        SessionRecord(
            booking_id=booking.id, consent=True, status="transcribed",
            run_id="run-notes-1",
            turns=[{"speaker": "SPEAKER_0", "start_ms": 0, "end_ms": 1,
                    "text": "a"}],
            speaker_map={"SPEAKER_0": "Professor"},
        )
    )
    db.session.commit()
    client = app.test_client()
    login_sample_student(client)
    response = client.post(
        f"/sessions/{booking.id}/room/speakers/swap", data={"next": "transcript"}
    )
    assert response.status_code == 303
    assert response.headers["Location"].endswith(
        f"/sessions/{booking.id}/room/transcript"
    )


def test_session_page_links_pdf_after_notes(app: Flask, tmp_path: Path) -> None:
    """The session page gains a PDF download link once notes land."""
    booking = accepted_booking(naive_utc_plus(minutes=10))
    client = app.test_client()
    login_sample_student(client)
    before = client.get(f"/sessions/{booking.id}").get_data(as_text=True)
    assert "notes.pdf" not in before
    run_full_pipeline(app, tmp_path, booking_id=booking.id)
    after = client.get(f"/sessions/{booking.id}").get_data(as_text=True)
    assert "notes.pdf" in after


def test_reupload_sends_fresh_email(app: Flask, tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """A second upload runs the full pipeline and emails new notes."""
    monkeypatch.setattr(
        "app.blueprints.cases._launch_session_pipeline",
        lambda a, b, r: run_session_pipeline(
            a, b, r, fake_transcript, canned_draft, canned_review
        ),
    )
    app.config["DEMO_ALLOW_ANYTIME"] = True
    booking = accepted_booking(naive_utc_plus(minutes=10))
    client = app.test_client()
    login_sample_student(client)
    upload(client, booking.id, wav_bytes())
    upload(client, booking.id, wav_bytes())
    kinds = sorted(
        row.kind
        for row in EmailLog.query.filter_by(booking_id=booking.id).all()
    )
    assert len(kinds) == 2
    assert len({kind.split(":")[1] for kind in kinds}) == 2
