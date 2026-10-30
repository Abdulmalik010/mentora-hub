"""Wallet tests: ledger invariants, holds, captures, insufficient funds."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from flask import Flask

from app.extensions import db
from app.models import Booking, LedgerEntry, ProfessorProfile, User
from app.services.booking import InsufficientFundsError, create_booking
from app.services.booking_workflow import (
    apply_transition,
    expire_stale_bookings,
    utcnow_naive,
)
from app.services.wallet import (
    OPENING_STUDENT_CREDITS,
    capture_entries,
    demo_balance,
    hold_amount,
    place_hold,
    platform_fee_for,
    release_entries,
)
from tests.test_booking import login_sample_student, seed_booking_case
from tests.test_workflow import force_status, fresh_key

RATE_12 = 22000  # seeded rate of professor 12


def seed_held() -> Booking:
    """Requested booking for professor 12 (places a 22,000 hold)."""
    case, prof_id = seed_booking_case()
    return create_booking(
        student_id=case.student_id, professor_id=prof_id, case_id=case.id,
        start_naive_utc=datetime(2026, 11, 4, 9, 0),
        consent_share_diagnosis=True, idempotency_key=fresh_key(),
    )


def parties(booking: Booking) -> tuple[User, User]:
    """Student and professor users for one booking."""
    student = db.session.get(User, booking.student_id)
    professor = db.session.get(User, booking.professor_id)
    assert student is not None and professor is not None
    return student, professor


def test_opening_balances(app: Flask) -> None:
    """Students start with 100,000 demo credits; professors with zero."""
    case, prof_id = seed_booking_case()
    student = db.session.get(User, case.student_id)
    professor = db.session.get(User, prof_id)
    assert student is not None and professor is not None
    assert demo_balance(student) == OPENING_STUDENT_CREDITS == 100_000
    assert demo_balance(professor) == 0


def test_request_places_hold(app: Flask) -> None:
    """Checkout writes one hold row and reduces the available balance."""
    booking = seed_held()
    student, _professor = parties(booking)
    assert hold_amount(booking.id) == RATE_12
    assert demo_balance(student) == 100_000 - RATE_12
    holds = LedgerEntry.query.filter_by(
        booking_id=booking.id, type="hold"
    ).all()
    assert len(holds) == 1


def test_insufficient_funds_fails_cleanly(app: Flask) -> None:
    """An uncovered request raises with no booking and no hold row."""
    case, prof_id = seed_booking_case()
    profile = ProfessorProfile.query.filter_by(user_id=prof_id).one()
    profile.rate = 200_000.0
    db.session.commit()
    with pytest.raises(InsufficientFundsError, match="Insufficient demo"):
        create_booking(
            student_id=case.student_id, professor_id=prof_id,
            case_id=case.id, start_naive_utc=datetime(2026, 11, 4, 9, 0),
            consent_share_diagnosis=True, idempotency_key=fresh_key(),
        )
    assert Booking.query.count() == 0
    assert LedgerEntry.query.count() == 0


def test_insufficient_funds_view(app: Flask) -> None:
    """Checkout with an empty wallet answers 400, booking nothing."""
    from app.services.slots import generate_slots

    case, prof_id = seed_booking_case()
    profile = ProfessorProfile.query.filter_by(user_id=prof_id).one()
    slot = generate_slots(profile.availability or {})[0]
    profile.rate = 200_000.0
    db.session.commit()
    client = app.test_client()
    login_sample_student(client)
    response = client.post(
        f"/cases/{case.id}/book/{prof_id}",
        data={
            "slot": slot.key, "consent": "yes",
            "idempotency_token": "tok-broke-1",
        },
    )
    assert response.status_code == 400
    assert "Insufficient demo credits" in response.get_data(as_text=True)
    assert Booking.query.count() == 0


def test_accept_captures_with_platform_fee(app: Flask) -> None:
    """Accept charges the student and credits the professor minus 10%."""
    booking = seed_held()
    student, professor = parties(booking)
    apply_transition(booking.id, "accept", actor_user=professor)
    assert demo_balance(student) == 100_000 - RATE_12
    assert demo_balance(professor) == RATE_12 - platform_fee_for(RATE_12)
    assert demo_balance(professor) == 19_800
    fee = LedgerEntry.query.filter_by(
        booking_id=booking.id, type="platform_fee"
    ).one()
    assert fee.amount == 2_200
    assert fee.user_id is None


def test_releases_restore_availability(app: Flask) -> None:
    """Decline, cancel and expiry each free the held amount."""
    first = seed_held()
    student, professor = parties(first)
    apply_transition(
        first.id, "decline", actor_user=professor, reason="Busy."
    )
    assert demo_balance(student) == 100_000

    _second_case, second_prof = seed_booking_case()
    second_student = db.session.get(User, first.student_id)
    assert second_student is not None
    second = create_booking(
        student_id=first.student_id, professor_id=second_prof,
        case_id=first.case_id, start_naive_utc=datetime(2026, 11, 11, 9, 0),
        consent_share_diagnosis=True, idempotency_key=fresh_key(),
    )
    apply_transition(second.id, "cancel", actor_user=second_student)
    assert demo_balance(second_student) == 100_000

    third = create_booking(
        student_id=first.student_id, professor_id=second_prof,
        case_id=first.case_id, start_naive_utc=datetime(2026, 11, 18, 9, 0),
        consent_share_diagnosis=True, idempotency_key=fresh_key(),
    )
    force_status(
        third, "requested",
        expires_at=utcnow_naive() - timedelta(hours=1),
    )
    assert expire_stale_bookings() == [third.id]
    assert demo_balance(second_student) == 100_000


def test_capture_uses_request_time_amount(app: Flask) -> None:
    """A rate change after the request does not change the capture."""
    booking = seed_held()
    _student, professor = parties(booking)
    profile = ProfessorProfile.query.filter_by(user_id=professor.id).one()
    profile.rate = 50_000.0
    db.session.commit()
    apply_transition(booking.id, "accept", actor_user=professor)
    assert demo_balance(professor) == RATE_12 - platform_fee_for(RATE_12)


def test_free_session_skips_ledger(app: Flask) -> None:
    """Zero-rate professors book and decide with no ledger rows."""
    case, prof_id = seed_booking_case()
    profile = ProfessorProfile.query.filter_by(user_id=prof_id).one()
    profile.rate = None
    db.session.commit()
    booking = create_booking(
        student_id=case.student_id, professor_id=prof_id, case_id=case.id,
        start_naive_utc=datetime(2026, 11, 4, 9, 0),
        consent_share_diagnosis=True, idempotency_key=fresh_key(),
    )
    assert LedgerEntry.query.count() == 0
    professor = db.session.get(User, prof_id)
    assert professor is not None
    apply_transition(booking.id, "accept", actor_user=professor)
    assert LedgerEntry.query.count() == 0
    assert demo_balance(professor) == 0


def test_settlement_builders_are_idempotent(app: Flask) -> None:
    """Second capture/release builds for a booking come back empty."""
    booking = seed_held()
    _student, professor = parties(booking)
    assert len(capture_entries(booking)) == 3
    apply_transition(booking.id, "accept", actor_user=professor)
    assert capture_entries(booking) == []
    assert release_entries(booking) == []


def test_place_hold_rejects_short_and_zero(app: Flask) -> None:
    """Direct holds enforce funds and positive amounts."""
    booking = seed_held()
    student, _professor = parties(booking)
    with pytest.raises(InsufficientFundsError):
        place_hold(student, booking.id, 100_000)
    with pytest.raises(ValueError, match="positive"):
        place_hold(student, booking.id, 0)


def test_dashboard_shows_demo_wallet_card(app: Flask) -> None:
    """The student dashboard carries a demo-labeled balance card."""
    booking = seed_held()
    student, _professor = parties(booking)
    client = app.test_client()
    login_sample_student(client)
    html = client.get("/dashboard").get_data(as_text=True)
    assert "Demo balance" in html
    assert "₦78,000 demo" in html
    assert demo_balance(student) == 78_000
