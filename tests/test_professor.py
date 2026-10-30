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
        idempotency_key="tok-prof-dash-1",
    )
    client = app.test_client()
    login_professor(client, 12)
    page = client.get("/dashboard")
    assert page.status_code == 200
    html = page.get_data(as_text=True)
    assert "Upcoming sessions" in html
    assert "Sample Student 01" in html
    assert "Full case file" in html


def test_professor_dashboard_lists_own_upcoming_only(app: Flask) -> None:
    """Other professors' and past bookings stay invisible."""
    case, prof_id = seed_booking_case()
    mine = create_booking(
        student_id=case.student_id, professor_id=prof_id, case_id=case.id,
        start_naive_utc=future_start(3), consent_share_diagnosis=True,
        idempotency_key="tok-prof-own-1",
    )
    create_booking(
        student_id=case.student_id, professor_id=2, case_id=case.id,
        start_naive_utc=future_start(4), consent_share_diagnosis=True,
        idempotency_key="tok-prof-own-2",
    )
    create_booking(
        student_id=case.student_id, professor_id=prof_id, case_id=case.id,
        start_naive_utc=future_start(-3), consent_share_diagnosis=True,
        idempotency_key="tok-prof-own-3",
    )
    client = app.test_client()
    login_professor(client, 12)
    html = client.get("/dashboard").get_data(as_text=True)
    assert html.count("Full case file") == 1
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
        idempotency_key="tok-prof-file-1",
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
    assert "Respond to this request" in html  # actions while requested
    assert (booking.meeting_url or "") not in html  # link hidden until accept
    from app.services.booking_workflow import apply_transition

    apply_transition(booking.id, "accept", actor_user=professor)
    decided = client.get(f"/dashboard/bookings/{booking.id}")
    decided_html = decided.get_data(as_text=True)
    assert (booking.meeting_url or "") in decided_html
    main = decided_html.split("<main", 1)[1]  # decided: no forms past the nav
    assert "<form" not in main


def test_case_file_access_control(app: Flask) -> None:
    """Anonymous bounces; students 403; others and unconsented 404."""
    case, prof_id = seed_booking_case()
    booking = create_booking(
        student_id=case.student_id, professor_id=prof_id, case_id=case.id,
        start_naive_utc=future_start(), consent_share_diagnosis=True,
        idempotency_key="tok-prof-access-1",
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


def test_workspace_stats_and_tabs(app: Flask) -> None:
    """Stats are real counts; all four tabs render with badges."""
    from app.services.booking_workflow import apply_transition

    case, prof_id = seed_booking_case()
    pending = create_booking(
        student_id=case.student_id, professor_id=prof_id, case_id=case.id,
        start_naive_utc=future_start(3), consent_share_diagnosis=True,
        idempotency_key="tok-ws-stats-1",
    )
    accepted = create_booking(
        student_id=case.student_id, professor_id=prof_id, case_id=case.id,
        start_naive_utc=future_start(4), consent_share_diagnosis=True,
        idempotency_key="tok-ws-stats-2",
    )
    professor = db.session.get(User, prof_id)
    assert professor is not None
    apply_transition(accepted.id, "accept", actor_user=professor)
    client = app.test_client()
    login_professor(client, 12)
    html = client.get("/dashboard").get_data(as_text=True)
    assert "Demo balance" in html and "₦19,800 demo" in html
    assert "Pending requests" in html
    assert "Upcoming sessions" in html
    assert "Unread messages" in html
    for tab in ("Requests", "Upcoming", "Inbox", "Profile"):
        assert f">{tab}" in html or f'id="tab-{tab.lower()}"' in html
    assert "Weak identification strategy." in html  # case preview
    assert "methodology" in html
    assert f"/dashboard/bookings/{pending.id}/accept" in html
    assert f"/dashboard/bookings/{pending.id}/decline" in html
    assert f"/dashboard/bookings/{pending.id}/propose" in html
    assert "Join video" in html  # accepted session in Upcoming


def test_workspace_request_actions_inline(app: Flask) -> None:
    """Dashboard forms drive the same endpoints as the case-file page."""
    from app.models import ProfessorProfile

    from app.services.slots import generate_slots

    case, prof_id = seed_booking_case()
    first = create_booking(
        student_id=case.student_id, professor_id=prof_id, case_id=case.id,
        start_naive_utc=future_start(3), consent_share_diagnosis=True,
        idempotency_key="tok-ws-act-1",
    )
    second = create_booking(
        student_id=case.student_id, professor_id=prof_id, case_id=case.id,
        start_naive_utc=future_start(5), consent_share_diagnosis=True,
        idempotency_key="tok-ws-act-2",
    )
    client = app.test_client()
    login_professor(client, 12)
    assert client.post(
        f"/dashboard/bookings/{first.id}/accept"
    ).status_code == 303
    profile = ProfessorProfile.query.filter_by(user_id=prof_id).one()
    slot = [
        s for s in generate_slots(profile.availability or {})
        if s.start_naive_utc != second.scheduled_at
    ][0]
    assert client.post(
        f"/dashboard/bookings/{second.id}/propose",
        data={"new_slot": slot.key},
    ).status_code == 303
    html = client.get("/dashboard").get_data(as_text=True)
    assert "Waiting on the student" in html


def test_workspace_empty_states_and_profile(app: Flask) -> None:
    """Each tab has a designed empty state; the profile tab summarizes."""
    seed_booking_case()
    client = app.test_client()
    login_professor(client, 3)
    for tab, heading in (
        ("requests", "No pending requests"),
        ("upcoming", "No upcoming sessions"),
        ("inbox", "No messages yet"),
    ):
        html = client.get(f"/dashboard?tab={tab}").get_data(as_text=True)
        assert heading in html
    profile_html = client.get("/dashboard?tab=profile").get_data(as_text=True)
    assert "Dr. Yuki Tanaka" in profile_html
    assert "Statistics" in profile_html
    assert "Time series" in profile_html
    assert "₦13,000" in profile_html
    assert "View public profile" in profile_html
    assert client.get("/dashboard?tab=bogus").status_code == 200


def test_professor_blocked_from_student_routes(app: Flask) -> None:
    """Professors stay out of intake, booking and student sessions."""
    from tests.test_matching import seed_match_case

    seed_match_case()
    client = app.test_client()
    login_professor(client, 12)
    assert client.get("/cases/new").status_code == 403
    assert client.get("/sessions").status_code == 403
