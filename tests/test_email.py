"""Email tests: providers, override, idempotency, content. No network."""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from flask import Flask

from app.extensions import db
from app.models import Booking, EmailLog, User
from app.services import email_service
from app.services.booking import create_booking
from app.services.email_service import (
    KIND_CASE_FILE,
    KIND_CONFIRMATION,
    OutgoingEmail,
    build_case_file_email,
    build_confirmation_email,
    send_booking_emails,
    send_logged_email,
)
from tests.test_booking import login_sample_student, seed_booking_case

EMAIL = OutgoingEmail(
    to="prof@example.com", subject="Hello", text="Hi.", html_body="<p>Hi.</p>"
)


def seed_booking(key: str = "tok-email-1") -> Booking:
    """Seeded booking with consent for professor 12."""
    case, prof_id = seed_booking_case()
    return create_booking(
        student_id=case.student_id, professor_id=prof_id, case_id=case.id,
        start_naive_utc=datetime(2026, 11, 4, 9, 0),
        consent_share_diagnosis=True, idempotency_key=key,
    )


def outbox_files(tmp_path) -> list[str]:  # type: ignore[no-untyped-def]
    """Sorted .eml filenames in the test outbox dir."""
    outbox = tmp_path / "outbox"
    if not outbox.exists():
        return []
    return sorted(os.listdir(outbox))


def test_outbox_writes_eml_and_logs_sent(app: Flask, tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Outbox provider writes one .eml and logs it as sent."""
    booking = seed_booking()
    log = send_logged_email(
        booking_id=booking.id, kind=KIND_CONFIRMATION, email=EMAIL
    )
    assert log.status == "sent"
    assert log.provider == "outbox"
    assert log.recipient == "prof@example.com"
    assert log.provider_id is not None and log.provider_id.endswith(".eml")
    files = outbox_files(tmp_path)
    assert files == [log.provider_id]
    raw = (tmp_path / "outbox" / files[0]).read_bytes().decode()
    assert "To: prof@example.com" in raw
    assert "Subject: Hello" in raw
    assert "Hi." in raw


def test_override_redirects_with_banner(app: Flask, tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Override reroutes to one inbox, bannered in text and HTML."""
    monkeypatch.setenv("DEMO_RECIPIENT_OVERRIDE", "demo-owner@example.org")
    booking = seed_booking()
    log = send_logged_email(
        booking_id=booking.id, kind=KIND_CONFIRMATION, email=EMAIL
    )
    assert log.status == "sent"
    assert log.recipient == "prof@example.com"  # original kept in the log
    raw = (tmp_path / "outbox" / outbox_files(tmp_path)[0]).read_bytes().decode()
    assert "To: demo-owner@example.org" in raw
    assert "[Demo] Hello" in raw
    assert "Demo: intended for prof@example.com" in raw


def test_send_is_idempotent_per_booking_and_kind(app: Flask, tmp_path) -> None:  # type: ignore[no-untyped-def]
    """A repeat send returns the existing row and writes nothing new."""
    booking = seed_booking()
    first = send_logged_email(
        booking_id=booking.id, kind=KIND_CONFIRMATION, email=EMAIL
    )
    second = send_logged_email(
        booking_id=booking.id, kind=KIND_CONFIRMATION, email=EMAIL
    )
    assert first.id == second.id
    assert outbox_files(tmp_path) != []
    assert len(outbox_files(tmp_path)) == 1
    assert EmailLog.query.filter_by(
        booking_id=booking.id, kind=KIND_CONFIRMATION
    ).count() == 1


class FakeResponse:
    """Minimal httpx response double."""

    def __init__(self, status_code: int, payload: dict[str, Any]) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self) -> dict[str, Any]:
        """Return the canned JSON body."""
        return self._payload


def test_resend_success_logs_provider_id(app: Flask, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Resend 200 persists the provider id; payload carries all fields."""
    monkeypatch.setenv("EMAIL_PROVIDER", "resend")
    monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
    seen: dict[str, Any] = {}

    def fake_post(url: str, **kwargs: Any) -> FakeResponse:
        seen["url"] = url
        seen.update(kwargs)
        return FakeResponse(200, {"id": "re_123"})

    monkeypatch.setattr("httpx.post", fake_post)
    booking = seed_booking()
    log = send_logged_email(
        booking_id=booking.id,
        kind=KIND_CONFIRMATION,
        email=OutgoingEmail(
            to="real@example.org", subject="Hi", text="T", html_body="<p>T</p>"
        ),
    )
    assert log.status == "sent"
    assert log.provider_id == "re_123"
    assert seen["url"] == "https://api.resend.com/emails"
    assert seen["json"]["to"] == ["real@example.org"]
    assert seen["json"]["subject"] == "Hi"
    assert seen["headers"]["Authorization"] == "Bearer re_test_key"


def test_resend_retries_once_then_fails(app: Flask, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """5xx retries once; double failure becomes a failed row, not a raise."""
    monkeypatch.setenv("EMAIL_PROVIDER", "resend")
    monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
    calls: list[str] = []

    def fake_post(url: str, **kwargs: Any) -> FakeResponse:
        calls.append(url)
        return FakeResponse(500, {"error": "boom"})

    monkeypatch.setattr("httpx.post", fake_post)
    booking = seed_booking()
    log = send_logged_email(
        booking_id=booking.id,
        kind=KIND_CONFIRMATION,
        email=OutgoingEmail(
            to="real@example.org", subject="Hi", text="T", html_body="<p>T</p>"
        ),
    )
    assert calls and all(call.endswith("/emails") for call in calls)
    assert len(calls) == 2
    assert log.status == "failed"
    assert "500" in (log.error or "")


def test_resend_client_error_fails_fast(app: Flask, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """4xx does not retry: the request itself is wrong."""
    monkeypatch.setenv("EMAIL_PROVIDER", "resend")
    monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
    calls: list[str] = []

    def fake_post(url: str, **kwargs: Any) -> FakeResponse:
        calls.append(url)
        return FakeResponse(401, {"error": "bad key"})

    monkeypatch.setattr("httpx.post", fake_post)
    booking = seed_booking()
    log = send_logged_email(
        booking_id=booking.id,
        kind=KIND_CONFIRMATION,
        email=OutgoingEmail(
            to="real@example.org", subject="Hi", text="T", html_body="<p>T</p>"
        ),
    )
    assert len(calls) == 1
    assert log.status == "failed"


def test_resend_refuses_sample_addresses(app: Flask, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """@example.com never reaches Resend unless the override reroutes it."""
    monkeypatch.setenv("EMAIL_PROVIDER", "resend")
    monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
    calls: list[str] = []
    monkeypatch.setattr(
        "httpx.post", lambda url, **kwargs: calls.append(url) or FakeResponse(200, {"id": "re_x"})
    )
    booking = seed_booking()
    refused = send_logged_email(
        booking_id=booking.id, kind=KIND_CONFIRMATION, email=EMAIL
    )
    assert refused.status == "refused"
    assert calls == []
    monkeypatch.setenv("DEMO_RECIPIENT_OVERRIDE", "demo-owner@example.org")
    allowed = send_logged_email(
        booking_id=booking.id, kind=KIND_CASE_FILE, email=EMAIL
    )
    assert allowed.status == "sent"
    assert len(calls) == 1


def test_unknown_provider_is_refused(app: Flask, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """A typo'd provider logs refused instead of raising."""
    monkeypatch.setenv("EMAIL_PROVIDER", "pigeon")
    booking = seed_booking()
    log = send_logged_email(
        booking_id=booking.id, kind=KIND_CONFIRMATION, email=EMAIL
    )
    assert log.status == "refused"
    assert "pigeon" in (log.error or "")


def rich_case_booking(app: Flask) -> Booking:  # type: ignore[no-untyped-def]
    """Booking whose case carries questions, tried items and an XSS probe."""
    case, prof_id = seed_booking_case()
    diagnosis = dict(case.diagnosis or {})
    diagnosis["questions_for_professor"] = ["Is my instrument valid?"]
    diagnosis["what_student_already_tried"] = ["A placebo regression."]
    diagnosis["gaps"][0]["description"] = 'Bad <script>alert("x")</script> errors.'
    case.diagnosis = diagnosis
    db.session.commit()
    return create_booking(
        student_id=case.student_id, professor_id=prof_id, case_id=case.id,
        start_naive_utc=datetime(2026, 11, 4, 9, 0),
        consent_share_diagnosis=True, idempotency_key="tok-email-rich-1",
    )


def test_case_file_content(app: Flask) -> None:
    """Case file carries problem, gaps, questions, agenda, slot and link."""
    booking = rich_case_booking(app)
    case = booking.case
    assert case is not None
    professor = db.session.get(User, booking.professor_id)
    student = db.session.get(User, booking.student_id)
    assert professor is not None and student is not None
    email = build_case_file_email(
        booking=booking, case=case, professor=professor, student=student
    )
    assert email.to == professor.email
    assert "Weak identification strategy." in email.text
    assert "results were significant" in email.text
    assert "(p. 1)" in email.text
    assert "Is my instrument valid?" in email.text
    assert "A placebo regression." in email.text
    assert "45-minute agenda" in email.text
    assert "Wed, Nov 4 · 10:00 WAT" in email.text
    assert (booking.meeting_url or "") in email.text
    assert "<script>" not in email.html_body
    assert "&lt;script&gt;" in email.html_body
    assert "[SAMPLE DATA]" in email.text


def test_confirmation_content(app: Flask) -> None:
    """Confirmation names the professor, slot, link and demo receipt."""
    booking = rich_case_booking(app)
    professor = db.session.get(User, booking.professor_id)
    student = db.session.get(User, booking.student_id)
    assert professor is not None and student is not None
    email = build_confirmation_email(
        booking=booking, professor=professor, student=student
    )
    assert email.to == student.email
    assert "Dr. Chiamaka Obi" in email.text
    assert "Wed, Nov 4 · 10:00 WAT" in email.text
    assert (booking.meeting_url or "") in email.text
    assert (booking.mock_payment_ref or "") in email.text


def test_case_file_gated_on_consent(app: Flask) -> None:
    """Without consent the case file stays home; confirmation still sends."""
    booking = seed_booking()
    booking.consent_share_diagnosis = False
    db.session.commit()
    logs = send_booking_emails(booking.id)
    assert [log.kind for log in logs] == [KIND_CONFIRMATION]
    assert EmailLog.query.filter_by(
        booking_id=booking.id, kind=KIND_CASE_FILE
    ).count() == 0


def test_booking_post_sends_both_emails(app: Flask, tmp_path) -> None:  # type: ignore[no-untyped-def]
    """End of checkout: two sent logs and two .eml files."""
    from app.models import ProfessorProfile

    from app.services.slots import generate_slots

    case, prof_id = seed_booking_case()
    profile = ProfessorProfile.query.filter_by(user_id=prof_id).one()
    slot = generate_slots(profile.availability or {})[0]
    client = app.test_client()
    login_sample_student(client)
    response = client.post(
        f"/cases/{case.id}/book/{prof_id}",
        data={
            "slot": slot.key, "consent": "yes",
            "idempotency_token": "tok-email-flow-1",
        },
    )
    assert response.status_code == 303
    booking = Booking.query.one()
    kinds = {
        row.kind: row.status
        for row in EmailLog.query.filter_by(booking_id=booking.id).all()
    }
    assert kinds == {KIND_CASE_FILE: "sent", KIND_CONFIRMATION: "sent"}
    assert len(outbox_files(tmp_path)) == 2


def test_email_failure_never_breaks_booking(app: Flask, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Even a crashing mailer leaves a confirmed booking behind."""
    from app.models import ProfessorProfile

    from app.services.slots import generate_slots

    def _boom(booking_id: int) -> None:
        raise RuntimeError("smtp is lava")

    monkeypatch.setattr("app.blueprints.cases.send_booking_emails", _boom)
    case, prof_id = seed_booking_case()
    profile = ProfessorProfile.query.filter_by(user_id=prof_id).one()
    slot = generate_slots(profile.availability or {})[0]
    client = app.test_client()
    login_sample_student(client)
    response = client.post(
        f"/cases/{case.id}/book/{prof_id}",
        data={
            "slot": slot.key, "consent": "yes",
            "idempotency_token": "tok-email-boom-1",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert Booking.query.count() == 1
    assert "could not be sent" in response.get_data(as_text=True)
