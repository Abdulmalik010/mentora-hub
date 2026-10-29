"""Booking tests: slot grid, timezones, race-safe create, consent, routes."""
from __future__ import annotations

import os
import threading
from datetime import datetime, timedelta, timezone

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app.extensions import db
from app.models import Booking, CaseFile, MatchResult, User
from app.services.booking import SlotTakenError, create_booking
from app.services.slots import (
    SLOT_DAYS_AHEAD,
    format_wat,
    generate_slots,
    slot_from_key,
)
from scripts.seed import seed_database
from tests.test_intake import login, make_student
from tests.test_matching import seed_match_case

MONDAY_NOON_UTC = datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)


def seed_booking_case() -> tuple[CaseFile, int]:
    """Seeded case plus a match row for professor 12; returns (case, prof_id)."""
    case = seed_match_case()
    match = MatchResult(
        case_id=case.id, professor_id=12, rank=1, score=90,
        reasons=[
            {
                "gap_id": "g1", "page": 1,
                "quote": "results were significant",
                "explanation": "Teaches inference.",
            }
        ],
        caveats=[], next_slot="2026-11-02 10:00 WAT",
    )
    db.session.add(match)
    db.session.commit()
    return case, 12


def login_sample_student(client: FlaskClient) -> None:
    """Log in as the seeded student owning seed_match_case rows."""
    client.post(
        "/auth/login",
        data={
            "email": "sample-student-01@example.com",
            "password": os.environ["SEED_DEMO_PASSWORD"],
        },
    )


def test_slot_grid_from_weekly_pattern() -> None:
    """Whole hours inside the window land on listed weekdays, future only."""
    assert MONDAY_NOON_UTC.strftime("%A") == "Monday"
    slots = generate_slots(
        {"days": ["Wednesday"], "hours": "10:00-12:00 WAT"},
        now=MONDAY_NOON_UTC,
    )
    assert len(slots) == 4  # two Wednesdays x 10:00/11:00 WAT
    first = slots[0]
    assert first.start_naive_utc == datetime(2026, 11, 4, 9, 0)
    assert first.start_wat.strftime("%H:%M") == "10:00"
    assert slots[1].start_naive_utc == datetime(2026, 11, 4, 10, 0)
    assert slots[2].start_naive_utc == datetime(2026, 11, 11, 9, 0)
    assert all(slot.start_utc > MONDAY_NOON_UTC for slot in slots)


def test_slots_skip_past_and_reject_malformed() -> None:
    """Past slots drop out; bad availability yields nothing, never crashes."""
    wednesday_past = datetime(2026, 11, 4, 13, 0, tzinfo=timezone.utc)
    slots = generate_slots(
        {"days": ["Wednesday"], "hours": "10:00-11:00 WAT"},
        now=wednesday_past,
    )
    assert [slot.start_naive_utc for slot in slots] == [
        datetime(2026, 11, 11, 9, 0), datetime(2026, 11, 18, 9, 0)
    ]
    assert generate_slots(None) == []
    assert generate_slots({}) == []
    assert generate_slots({"days": ["Monday"], "hours": "blah"}) == []
    assert generate_slots({"days": ["Monday"], "hours": "14:00-10:00 WAT"}) == []
    assert generate_slots({"days": [], "hours": "10:00-12:00 WAT"}) == []


def test_slot_key_roundtrip() -> None:
    """Keys survive the form round-trip; garbage and naive input degrade."""
    slots = generate_slots(
        {"days": ["Wednesday"], "hours": "10:00-11:00 WAT"},
        now=MONDAY_NOON_UTC,
    )
    assert slot_from_key(slots[0].key) == slots[0]
    assert slot_from_key("not-a-slot") is None
    assert slot_from_key("") is None
    naive = slot_from_key("2026-11-04T09:00:00")
    assert naive is not None and naive.start_naive_utc == datetime(2026, 11, 4, 9, 0)


def test_format_wat() -> None:
    """Naive UTC renders as a WAT day string (UTC+1, no DST)."""
    assert format_wat(datetime(2026, 11, 4, 9, 0)) == "Wed, Nov 4 · 10:00 WAT"


def test_create_booking_and_double_booking(app: Flask) -> None:
    """Create confirms with link and ref; the same slot cannot book twice."""
    case, prof_id = seed_booking_case()
    start = datetime(2026, 11, 4, 9, 0)
    booking = create_booking(
        student_id=case.student_id, professor_id=prof_id, case_id=case.id,
        start_naive_utc=start, consent_share_diagnosis=True,
    )
    assert booking.status == "confirmed"
    assert booking.meeting_url.startswith("https://meet.jit.si/mentora-")
    assert booking.mock_payment_ref.startswith("DEMO-")
    assert booking.consent_share_diagnosis is True
    with pytest.raises(SlotTakenError):
        create_booking(
            student_id=case.student_id, professor_id=prof_id,
            case_id=case.id, start_naive_utc=start,
            consent_share_diagnosis=True,
        )
    other_prof = create_booking(
        student_id=case.student_id, professor_id=2, case_id=case.id,
        start_naive_utc=start, consent_share_diagnosis=True,
    )
    assert other_prof.meeting_url != booking.meeting_url
    assert Booking.query.count() == 2


def test_create_booking_requires_consent(app: Flask) -> None:
    """No consent, no booking."""
    case, prof_id = seed_booking_case()
    with pytest.raises(ValueError, match="consent"):
        create_booking(
            student_id=case.student_id, professor_id=prof_id,
            case_id=case.id, start_naive_utc=datetime(2026, 11, 4, 9, 0),
            consent_share_diagnosis=False,
        )
    assert Booking.query.count() == 0


def test_booking_race_one_winner(app: Flask) -> None:
    """Two threads racing one slot: exactly one booking survives."""
    case, prof_id = seed_booking_case()
    start = datetime(2026, 11, 4, 9, 0)
    student_id = case.student_id  # plain ints: ORM objects stay thread-local
    case_id = case.id
    outcomes: list[str] = []
    lock = threading.Lock()

    def attempt() -> None:
        with app.app_context():
            try:
                create_booking(
                    student_id=student_id, professor_id=prof_id,
                    case_id=case_id, start_naive_utc=start,
                    consent_share_diagnosis=True,
                )
                result = "booked"
            except SlotTakenError:
                result = "taken"
            with lock:
                outcomes.append(result)

    threads = [threading.Thread(target=attempt) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    assert sorted(outcomes) == ["booked", "taken"]
    assert Booking.query.filter_by(
        professor_id=prof_id, scheduled_at=start
    ).count() == 1


def test_book_page_requires_match(app: Flask) -> None:
    """Book page 404s for unmatched professors; matched shows the full form."""
    case, prof_id = seed_booking_case()
    client = app.test_client()
    login_sample_student(client)
    assert client.get(f"/cases/{case.id}/book/3").status_code == 404
    page = client.get(f"/cases/{case.id}/book/{prof_id}")
    assert page.status_code == 200
    html = page.get_data(as_text=True)
    assert "Share my diagnosis with this professor" in html
    assert "DEMO" in html and "charges nothing" in html
    assert 'name="slot"' in html and "WAT" in html
    assert "your local time" in html or "your time" in html
    assert 'name="csrf_token"' in html


def test_book_post_full_flow(app: Flask) -> None:
    """Pick slot, consent, submit: redirect to a session with link and ref."""
    from app.models import ProfessorProfile

    case, prof_id = seed_booking_case()
    profile = ProfessorProfile.query.filter_by(user_id=prof_id).one()
    slot = generate_slots(profile.availability or {})[0]
    client = app.test_client()
    login_sample_student(client)
    response = client.post(
        f"/cases/{case.id}/book/{prof_id}",
        data={"slot": slot.key, "consent": "yes"},
    )
    assert response.status_code == 302
    booking = Booking.query.one()
    assert response.location.endswith(f"/sessions/{booking.id}")
    assert booking.consent_share_diagnosis is True
    detail = client.get(f"/sessions/{booking.id}")
    assert detail.status_code == 200
    html = detail.get_data(as_text=True)
    assert "meet.jit.si/mentora-" in html
    assert "WAT" in html and "Shared with professor" in html
    assert "DEMO-" in html and "nothing charged" in html
    listing = client.get("/sessions")
    assert listing.status_code == 200
    assert "Dr. Chiamaka Obi" in listing.get_data(as_text=True)


def test_book_post_requires_consent_and_valid_slot(app: Flask) -> None:
    """Missing consent or a forged slot key books nothing (400)."""
    from app.models import ProfessorProfile

    case, prof_id = seed_booking_case()
    profile = ProfessorProfile.query.filter_by(user_id=prof_id).one()
    slot = generate_slots(profile.availability or {})[0]
    client = app.test_client()
    login_sample_student(client)
    no_consent = client.post(
        f"/cases/{case.id}/book/{prof_id}", data={"slot": slot.key}
    )
    assert no_consent.status_code == 400
    forged = client.post(
        f"/cases/{case.id}/book/{prof_id}",
        data={"slot": "2030-01-01T00:00:00+00:00", "consent": "yes"},
    )
    assert forged.status_code == 400
    assert Booking.query.count() == 0


def test_book_post_taken_slot_returns_409(app: Flask, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """A lost race surfaces as 409 with the picker intact."""
    from app.models import ProfessorProfile

    case, prof_id = seed_booking_case()
    profile = ProfessorProfile.query.filter_by(user_id=prof_id).one()
    slot = generate_slots(profile.availability or {})[0]

    def _always_taken(**kwargs):  # type: ignore[no-untyped-def]
        raise SlotTakenError("that slot was just booked; pick another")

    monkeypatch.setattr("app.blueprints.cases.create_booking", _always_taken)
    client = app.test_client()
    login_sample_student(client)
    response = client.post(
        f"/cases/{case.id}/book/{prof_id}",
        data={"slot": slot.key, "consent": "yes"},
    )
    assert response.status_code == 409
    assert "just booked" in response.get_data(as_text=True)


def test_sessions_access_control(app: Flask) -> None:
    """Anonymous bounces; other students 404; professors 403."""
    case, prof_id = seed_booking_case()
    booking = create_booking(
        student_id=case.student_id, professor_id=prof_id, case_id=case.id,
        start_naive_utc=datetime(2026, 11, 4, 9, 0),
        consent_share_diagnosis=True,
    )
    client = app.test_client()
    assert client.get("/sessions").status_code == 302
    assert client.get(f"/sessions/{booking.id}").status_code == 302
    assert client.get(f"/cases/{case.id}/book/{prof_id}").status_code == 302
    make_student()
    login(client, "intake@example.com")
    assert client.get("/sessions").status_code == 200  # own (empty) list
    assert client.get(f"/sessions/{booking.id}").status_code == 404
    assert client.get(f"/cases/{case.id}/book/{prof_id}").status_code == 404
    professor = User(
        display_name="Prof", email="prof-book@example.com", role="professor"
    )
    professor.set_password("password123")
    db.session.add(professor)
    db.session.commit()
    login(client, "prof-book@example.com")
    assert client.get("/sessions").status_code == 403
    assert client.get(f"/sessions/{booking.id}").status_code == 403
    assert client.get(f"/cases/{case.id}/book/{prof_id}").status_code == 403


def test_slot_window_spans_fourteen_days() -> None:
    """The picker window covers offsets 1..14 (no same-day rush)."""
    slots = generate_slots(
        {
            "days": [
                "Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
                "Saturday", "Sunday",
            ],
            "hours": "10:00-11:00 WAT",
        },
        now=MONDAY_NOON_UTC,
    )
    assert len(slots) == SLOT_DAYS_AHEAD
    assert slots[0].start_wat.date() == (
        MONDAY_NOON_UTC + timedelta(days=1)
    ).date()
    assert slots[-1].start_wat.date() == (
        MONDAY_NOON_UTC + timedelta(days=14)
    ).date()
