"""Professor tests: dashboard, case-file page, access control."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from flask import Flask
from flask.testing import FlaskClient

from app.extensions import db
from app.models import User
from app.services.booking import create_booking
from app.services.email_service import build_case_file_email
from tests.test_booking import login_sample_student, seed_booking_case


def login_professor(client: FlaskClient, number: int = 12) -> None:
    """Log in as a seeded professor with the sample password."""
    client.post(
        "/auth/login",
        data={
            "email": f"sample-professor-{number:02d}@example.com",
            "password": os.environ["SEED_DEMO_PASSWORD"],
        },
    )


def future_start(days: int = 3) -> datetime:
    """Naive-UTC start `days` ahead, truncated to the hour."""
    return (
        datetime.now(timezone.utc) + timedelta(days=days)
    ).replace(tzinfo=None, minute=0, second=0, microsecond=0)


def test_seeded_professor_login_and_dashboard(app: Flask) -> None:
    """Seeded professors log in with the demo password and see bookings."""
    case, prof_id = seed_booking_case()
    create_booking(
        student_id=case.student_id, professor_id=prof_id, case_id=case.id,
        start_naive_utc=future_start(), consent_share_diagnosis=True,
    )
    client = app.test_client()
    login_professor(client, 12)
    page = client.get("/dashboard")
    assert page.status_code == 200
    html = page.get_data(as_text=True)
    assert "Upcoming sessions" in html
    assert "Sample Student 01" in html
    assert "Open case file" in html


def test_professor_dashboard_lists_own_upcoming_only(app: Flask) -> None:
    """Other professors' and past bookings stay invisible."""
    case, prof_id = seed_booking_case()
    mine = create_booking(
        student_id=case.student_id, professor_id=prof_id, case_id=case.id,
        start_naive_utc=future_start(3), consent_share_diagnosis=True,
    )
    create_booking(
        student_id=case.student_id, professor_id=2, case_id=case.id,
        start_naive_utc=future_start(4), consent_share_diagnosis=True,
    )
    create_booking(
        student_id=case.student_id, professor_id=prof_id, case_id=case.id,
        start_naive_utc=future_start(-3), consent_share_diagnosis=True,
    )
    client = app.test_client()
    login_professor(client, 12)
    html = client.get("/dashboard").get_data(as_text=True)
    assert html.count("Open case file") == 1
    from app.services.slots import format_wat

    assert format_wat(mine.scheduled_at) in html


def test_case_file_page_matches_email(app: Flask) -> None:
    """The page shows the same content the case-file email carried."""
    case, prof_id = seed_booking_case()
    diagnosis = dict(case.diagnosis or {})
    diagnosis["questions_for_professor"] = ["Is my instrument valid?"]
    diagnosis["what_student_already_tried"] = ["A placebo regression."]
    case.diagnosis = diagnosis
    db.session.commit()
    booking = create_booking(
        student_id=case.student_id, professor_id=prof_id, case_id=case.id,
        start_naive_utc=future_start(), consent_share_diagnosis=True,
    )
    professor = db.session.get(User, prof_id)
    student = db.session.get(User, case.student_id)
    assert professor is not None and student is not None
    email = build_case_file_email(
        booking=booking, case=case, professor=professor, student=student
    )
    client = app.test_client()
    login_professor(client, 12)
    page = client.get(f"/dashboard/bookings/{booking.id}")
    assert page.status_code == 200
    html = page.get_data(as_text=True)
    for snippet in (
        "Weak identification strategy.",
        "No standard errors reported.",
        "results were significant",
        "(p. 1)",
        "Is my instrument valid?",
        "A placebo regression.",
        "45-minute agenda",
    ):
        assert snippet in email.text
        assert snippet in html
    assert (booking.meeting_url or "") in html
    main = html.split("<main", 1)[1]  # read-only: no forms past the nav
    assert "<form" not in main


def test_case_file_access_control(app: Flask) -> None:
    """Anonymous bounces; students 403; others and unconsented 404."""
    case, prof_id = seed_booking_case()
    booking = create_booking(
        student_id=case.student_id, professor_id=prof_id, case_id=case.id,
        start_naive_utc=future_start(), consent_share_diagnosis=True,
    )
    url = f"/dashboard/bookings/{booking.id}"
    client = app.test_client()
    assert client.get(url).status_code == 302
    login_sample_student(client)  # the owning student: still professor-only
    assert client.get(url).status_code == 403
    login_professor(client, 2)  # a different professor
    assert client.get(url).status_code == 404
    assert client.get("/dashboard/bookings/9999").status_code == 404
    booking.consent_share_diagnosis = False
    db.session.commit()
    login_professor(client, 12)  # the booked professor, consent withdrawn
    assert client.get(url).status_code == 404


def test_professor_blocked_from_student_routes(app: Flask) -> None:
    """Professors stay out of intake, booking and student sessions."""
    from tests.test_matching import seed_match_case

    seed_match_case()
    client = app.test_client()
    login_professor(client, 12)
    assert client.get("/cases/new").status_code == 403
    assert client.get("/sessions").status_code == 403
