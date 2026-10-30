"""Request-workflow tests: state machine, race, expiry, actions. No network."""
from __future__ import annotations

import threading
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from flask import Flask

from app.extensions import db
from app.models import Booking, ProfessorProfile, User
from app.services.booking import (
    ACTIVE_STATUSES,
    STATUS_ACCEPTED,
    STATUS_CANCELLED,
    STATUS_COMPLETED,
    STATUS_DECLINED,
    STATUS_EXPIRED,
    STATUS_PROPOSED,
    STATUS_REQUESTED,
    SlotTakenError,
    create_booking,
)
from app.services.booking_workflow import (
    TRANSITIONS,
    BookingAuthError,
    InvalidTransitionError,
    apply_transition,
    expire_stale_bookings,
    utcnow_naive,
)
from app.services.slots import generate_slots
from tests.test_booking import login_sample_student, seed_booking_case
from tests.test_professor import future_start, login_professor


def fresh_key() -> str:
    """Unique idempotency key per booking."""
    return f"tok-wf-{uuid.uuid4().hex[:12]}"


def seed_request(start: datetime | None = None) -> Booking:
    """Requested booking for professor 12 with a fresh token."""
    case, prof_id = seed_booking_case()
    return create_booking(
        student_id=case.student_id, professor_id=prof_id, case_id=case.id,
        start_naive_utc=start or datetime(2026, 11, 4, 9, 0),
        consent_share_diagnosis=True, idempotency_key=fresh_key(),
    )


def force_status(booking: Booking, status: str, **fields) -> Booking:  # type: ignore[no-untyped-def]
    """Set status directly for table setup; returns the refreshed row."""
    booking.status = status
    for key, value in fields.items():
        setattr(booking, key, value)
    db.session.commit()
    db.session.refresh(booking)
    return booking


def parties(booking: Booking) -> tuple[User, User, User, User]:
    """Student, professor, other student, other professor."""
    student = db.session.get(User, booking.student_id)
    professor = db.session.get(User, booking.professor_id)
    other_student = User(
        display_name="Other", email="other-wf@example.com", role="student"
    )
    other_student.set_password("password123")
    other_prof = User(
        display_name="Other Prof", email="other-prof-wf@example.com",
        role="professor",
    )
    other_prof.set_password("password123")
    db.session.add_all([other_student, other_prof])
    db.session.commit()
    assert student is not None and professor is not None
    return student, professor, other_student, other_prof


def test_transition_table_covers_eight_edges() -> None:
    """The table is the spec: eight legal (status, action) edges."""
    assert set(TRANSITIONS) == {
        (STATUS_REQUESTED, "accept"),
        (STATUS_REQUESTED, "decline"),
        (STATUS_REQUESTED, "propose"),
        (STATUS_REQUESTED, "cancel"),
        (STATUS_REQUESTED, "expire"),
        (STATUS_PROPOSED, "accept_proposal"),
        (STATUS_PROPOSED, "decline_proposal"),
        (STATUS_PROPOSED, "expire"),
    }
    assert all(t.actor in ("professor", "student", "system") for t in TRANSITIONS.values())


def test_accept_captures_and_decides(app: Flask) -> None:
    """Accept flips to accepted, captures the hold, stamps decided_at."""
    booking = seed_request()
    professor = db.session.get(User, booking.professor_id)
    assert professor is not None
    done = apply_transition(booking.id, "accept", actor_user=professor)
    assert done.status == STATUS_ACCEPTED
    assert done.payment_status == "captured"
    assert done.decided_at is not None


def test_decline_needs_reason_and_releases(app: Flask) -> None:
    """Decline stores the reason and releases the hold; reason mandatory."""
    booking = seed_request()
    professor = db.session.get(User, booking.professor_id)
    assert professor is not None
    with pytest.raises(InvalidTransitionError, match="reason"):
        apply_transition(booking.id, "decline", actor_user=professor, reason="  ")
    done = apply_transition(
        booking.id, "decline", actor_user=professor, reason="On leave."
    )
    assert done.status == STATUS_DECLINED
    assert done.decline_reason == "On leave."
    assert done.payment_status == "released"


def test_propose_holds_alternative(app: Flask) -> None:
    """Propose parks a future open slot; hold stays until the student answers."""
    booking = seed_request()
    professor = db.session.get(User, booking.professor_id)
    assert professor is not None
    target = datetime(2026, 11, 11, 9, 0)
    done = apply_transition(
        booking.id, "propose", actor_user=professor, new_start=target
    )
    assert done.status == STATUS_PROPOSED
    assert done.proposed_start == target
    assert done.payment_status == "held"
    with pytest.raises(InvalidTransitionError, match="future"):
        apply_transition(
            seed_request(datetime(2026, 11, 18, 9, 0)).id, "propose",
            actor_user=professor, new_start=datetime(2020, 1, 1, 9, 0),
        )


def test_propose_rejects_occupied_slot(app: Flask) -> None:
    """A proposal onto a held slot fails without changing anything."""
    first = seed_request(datetime(2026, 11, 4, 9, 0))
    second = seed_request(datetime(2026, 11, 11, 9, 0))
    professor = db.session.get(User, first.professor_id)
    assert professor is not None
    with pytest.raises(SlotTakenError):
        apply_transition(
            second.id, "propose", actor_user=professor,
            new_start=datetime(2026, 11, 4, 9, 0),
        )
    db.session.refresh(second)
    assert second.status == STATUS_REQUESTED
    assert second.proposed_start is None


def test_answer_proposal_moves_and_captures(app: Flask) -> None:
    """Accepting a proposal moves the slot and captures; declining cancels."""
    booking = seed_request()
    professor = db.session.get(User, booking.professor_id)
    student = db.session.get(User, booking.student_id)
    assert professor is not None and student is not None
    target = datetime(2026, 11, 11, 9, 0)
    apply_transition(
        booking.id, "propose", actor_user=professor, new_start=target
    )
    done = apply_transition(booking.id, "accept_proposal", actor_user=student)
    assert done.status == STATUS_ACCEPTED
    assert done.scheduled_at == target
    assert done.proposed_start is None
    assert done.payment_status == "captured"

    other = seed_request(datetime(2026, 11, 18, 9, 0))
    apply_transition(
        other.id, "propose", actor_user=professor,
        new_start=datetime(2026, 11, 25, 9, 0),
    )
    refused = apply_transition(
        other.id, "decline_proposal", actor_user=student
    )
    assert refused.status == STATUS_CANCELLED
    assert refused.payment_status == "released"


def test_cancel_releases_while_requested(app: Flask) -> None:
    """Students can withdraw a pending request; the hold is released."""
    booking = seed_request()
    student = db.session.get(User, booking.student_id)
    assert student is not None
    done = apply_transition(booking.id, "cancel", actor_user=student)
    assert done.status == STATUS_CANCELLED
    assert done.payment_status == "released"


@pytest.mark.parametrize(
    "status,action",
    [
        (STATUS_ACCEPTED, "accept"),
        (STATUS_ACCEPTED, "decline"),
        (STATUS_ACCEPTED, "propose"),
        (STATUS_ACCEPTED, "cancel"),
        (STATUS_ACCEPTED, "accept_proposal"),
        (STATUS_DECLINED, "accept"),
        (STATUS_DECLINED, "cancel"),
        (STATUS_CANCELLED, "accept"),
        (STATUS_EXPIRED, "accept"),
        (STATUS_COMPLETED, "accept"),
        (STATUS_REQUESTED, "accept_proposal"),
        (STATUS_REQUESTED, "decline_proposal"),
        (STATUS_PROPOSED, "accept"),
        (STATUS_PROPOSED, "decline"),
        (STATUS_PROPOSED, "propose"),
        (STATUS_PROPOSED, "cancel"),
        (STATUS_REQUESTED, "nope"),
    ],
)
def test_illegal_edges_rejected(app: Flask, status: str, action: str) -> None:
    """Anything off the transition table raises, changing nothing."""
    booking = seed_request()
    force_status(booking, status)
    professor = db.session.get(User, booking.professor_id)
    student = db.session.get(User, booking.student_id)
    actor = professor if action in (
        "accept", "decline", "propose", "nope",
    ) else student
    with pytest.raises(InvalidTransitionError):
        apply_transition(
            booking.id, action, actor_user=actor, reason="x",
            new_start=datetime(2026, 11, 11, 9, 0),
        )
    db.session.refresh(booking)
    assert booking.status == status


@pytest.mark.parametrize(
    "action,actor_kind",
    [
        ("accept", "student"),
        ("accept", "other_professor"),
        ("decline", "student"),
        ("propose", "student"),
        ("cancel", "professor"),
        ("cancel", "other_student"),
        ("accept_proposal", "professor"),
        ("decline_proposal", "other_student"),
    ],
)
def test_wrong_actor_rejected(app: Flask, action: str, actor_kind: str) -> None:
    """Only the booking's own professor/student may move it."""
    booking = seed_request()
    student, professor, other_student, other_prof = parties(booking)
    if action in ("accept_proposal", "decline_proposal"):
        force_status(
            booking, STATUS_PROPOSED,
            proposed_start=datetime(2026, 11, 11, 9, 0),
        )
    actor = {
        "student": student, "professor": professor,
        "other_student": other_student, "other_professor": other_prof,
    }[actor_kind]
    with pytest.raises(BookingAuthError):
        apply_transition(
            booking.id, action, actor_user=actor, reason="x",
            new_start=datetime(2026, 11, 11, 9, 0),
        )


def test_double_accept_race_one_winner(app: Flask) -> None:
    """Two concurrent accepts: one wins, the other sees InvalidTransition."""
    booking = seed_request()
    booking_id = booking.id
    professor_id = booking.professor_id
    outcomes: list[str] = []
    lock = threading.Lock()

    def attempt() -> None:
        with app.app_context():
            try:
                professor = db.session.get(User, professor_id)
                apply_transition(booking_id, "accept", actor_user=professor)
                result = "accepted"
            except InvalidTransitionError:
                result = "stale"
            with lock:
                outcomes.append(result)

    threads = [threading.Thread(target=attempt) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    assert sorted(outcomes) == ["accepted", "stale"]
    db.session.refresh(booking)
    assert booking.status == STATUS_ACCEPTED
    assert booking.payment_status == "captured"


def test_expired_request_flips_on_touch(app: Flask) -> None:
    """Acting on a stale request expires it first, then refuses the action."""
    booking = seed_request()
    past = utcnow_naive() - timedelta(hours=1)
    force_status(booking, STATUS_REQUESTED, expires_at=past)
    professor = db.session.get(User, booking.professor_id)
    assert professor is not None
    with pytest.raises(InvalidTransitionError, match="expired"):
        apply_transition(booking.id, "accept", actor_user=professor)
    db.session.refresh(booking)
    assert booking.status == STATUS_EXPIRED
    assert booking.payment_status == "released"


def test_expire_sweep_only_touches_stale(app: Flask) -> None:
    """The sweep flips stale requests, leaving fresh and decided rows alone."""
    stale = seed_request(datetime(2026, 11, 4, 9, 0))
    force_status(
        stale, STATUS_REQUESTED,
        expires_at=utcnow_naive() - timedelta(hours=1),
    )
    proposed = seed_request(datetime(2026, 11, 11, 9, 0))
    force_status(
        proposed, STATUS_PROPOSED,
        expires_at=utcnow_naive() - timedelta(hours=1),
        proposed_start=datetime(2026, 11, 18, 9, 0),
    )
    fresh = seed_request(datetime(2026, 11, 18, 9, 0))
    decided = seed_request(datetime(2026, 11, 25, 9, 0))
    force_status(
        decided, STATUS_DECLINED,
        expires_at=utcnow_naive() - timedelta(hours=1),
    )
    flipped = expire_stale_bookings()
    assert sorted(flipped) == sorted([stale.id, proposed.id])
    for bid, expected in (
        (stale.id, STATUS_EXPIRED), (proposed.id, STATUS_EXPIRED),
        (fresh.id, STATUS_REQUESTED), (decided.id, STATUS_DECLINED),
    ):
        assert db.session.get(Booking, bid).status == expected


def test_expire_requests_cli(app: Flask) -> None:
    """The flask CLI command expires stale requests and reports the count."""
    stale = seed_request()
    force_status(
        stale, STATUS_REQUESTED,
        expires_at=utcnow_naive() - timedelta(hours=1),
    )
    result = app.test_cli_runner().invoke(args=["expire-requests"])
    assert result.exit_code == 0
    assert "Expired 1 booking request(s)." in result.output
    assert db.session.get(Booking, stale.id).status == STATUS_EXPIRED


def test_declined_slot_can_be_rebooked(app: Flask) -> None:
    """Terminal bookings vacate the slot: decline, then request it again."""
    booking = seed_request(datetime(2026, 11, 4, 9, 0))
    professor = db.session.get(User, booking.professor_id)
    assert professor is not None
    apply_transition(booking.id, "decline", actor_user=professor, reason="Busy.")
    case_id = booking.case_id
    student_id = booking.student_id
    assert case_id is not None
    retry = create_booking(
        student_id=student_id, professor_id=booking.professor_id,
        case_id=case_id, start_naive_utc=datetime(2026, 11, 4, 9, 0),
        consent_share_diagnosis=True, idempotency_key=fresh_key(),
    )
    assert retry.status == STATUS_REQUESTED


def test_partial_index_blocks_two_active_same_slot(app: Flask) -> None:
    """Below the service guard, the DB itself rejects double-active slots."""
    import sqlalchemy.exc

    booking = seed_request(datetime(2026, 11, 4, 9, 0))
    clash = Booking(
        student_id=booking.student_id, professor_id=booking.professor_id,
        case_id=booking.case_id, status=STATUS_ACCEPTED,
        scheduled_at=datetime(2026, 11, 4, 9, 0),
        payment_status="captured",
    )
    db.session.add(clash)
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        db.session.commit()
    db.session.rollback()
    assert booking.status in ACTIVE_STATUSES


def open_proposal_slot(booking: Booking):  # type: ignore[no-untyped-def]
    """A genuinely open slot for the booking's professor."""
    profile = ProfessorProfile.query.filter_by(
        user_id=booking.professor_id
    ).one()
    slots = [
        slot
        for slot in generate_slots(profile.availability or {})
        if slot.start_naive_utc != booking.scheduled_at
    ]
    assert slots, "seeded availability must offer alternatives"
    return slots[0]


def test_professor_action_views(app: Flask) -> None:
    """Accept/decline/propose move the request with flashes and 303s."""
    booking = seed_request()
    client = app.test_client()
    login_professor(client, 12)
    base = f"/dashboard/bookings/{booking.id}"
    page = client.get(base)
    assert page.status_code == 200
    assert "Propose time" in page.get_data(as_text=True)

    refused = client.post(f"{base}/decline", data={"reason": "  "})
    assert refused.status_code == 303
    db.session.refresh(booking)
    assert booking.status == STATUS_REQUESTED  # reason required

    new_slot = open_proposal_slot(booking)
    proposed = client.post(f"{base}/propose", data={"new_slot": new_slot.key})
    assert proposed.status_code == 303
    db.session.refresh(booking)
    assert booking.status == STATUS_PROPOSED
    assert booking.proposed_start == new_slot.start_naive_utc

    forged = client.post(
        f"{base}/propose", data={"new_slot": "2030-01-01T00:00:00+00:00"}
    )
    assert forged.status_code == 303  # invalid key, state unchanged
    db.session.refresh(booking)
    assert booking.status == STATUS_PROPOSED


def test_professor_accept_and_decline_views(app: Flask) -> None:
    """Accept captures and reveals; decline releases with the reason shown."""
    first = seed_request(datetime(2026, 11, 4, 9, 0))
    second = seed_request(datetime(2026, 11, 11, 9, 0))
    client = app.test_client()
    login_professor(client, 12)
    accept = client.post(
        f"/dashboard/bookings/{first.id}/accept", follow_redirects=True
    )
    assert accept.status_code == 200
    assert "Session accepted" in accept.get_data(as_text=True)
    assert (first.meeting_url or "") in accept.get_data(as_text=True)
    decline = client.post(
        f"/dashboard/bookings/{second.id}/decline",
        data={"reason": "Conference week."}, follow_redirects=True,
    )
    assert decline.status_code == 200
    assert "Request declined" in decline.get_data(as_text=True)
    db.session.refresh(second)
    assert second.status == STATUS_DECLINED
    assert second.payment_status == "released"


def test_student_cancel_and_proposal_views(app: Flask) -> None:
    """Cancel withdraws; proposal answers resolve; chips follow the state."""
    booking = seed_request()
    professor = db.session.get(User, booking.professor_id)
    assert professor is not None
    target = datetime(2026, 11, 11, 9, 0)
    apply_transition(
        booking.id, "propose", actor_user=professor, new_start=target
    )
    client = app.test_client()
    login_sample_student(client)
    listing = client.get("/sessions")
    assert "reschedule proposed" in listing.get_data(as_text=True)
    answer = client.post(
        f"/sessions/{booking.id}/proposal/accept", follow_redirects=True
    )
    assert answer.status_code == 200
    html = answer.get_data(as_text=True)
    assert "New time accepted" in html
    assert (booking.meeting_url or "") in html  # link revealed on accept
    db.session.refresh(booking)
    assert booking.status == STATUS_ACCEPTED
    assert booking.scheduled_at == target

    other = seed_request(datetime(2026, 11, 18, 9, 0))
    cancelled = client.post(
        f"/sessions/{other.id}/cancel", follow_redirects=True
    )
    assert cancelled.status_code == 200
    assert "Request cancelled" in cancelled.get_data(as_text=True)
    db.session.refresh(other)
    assert other.status == STATUS_CANCELLED


def test_workflow_action_auth(app: Flask) -> None:
    """Anonymous bounces; wrong roles 403; wrong owners 404."""
    booking = seed_request()
    prof_url = f"/dashboard/bookings/{booking.id}/accept"
    student_url = f"/sessions/{booking.id}/cancel"
    client = app.test_client()
    assert client.post(prof_url).status_code == 302
    assert client.post(student_url).status_code == 302
    login_sample_student(client)
    assert client.post(prof_url).status_code == 403
    login_professor(client, 2)
    assert client.post(prof_url).status_code == 404
    assert client.post(student_url).status_code == 403


def test_lazy_expiry_on_read(app: Flask) -> None:
    """Opening /sessions flips stale requests to expired automatically."""
    booking = seed_request()
    force_status(
        booking, STATUS_REQUESTED,
        expires_at=utcnow_naive() - timedelta(hours=1),
    )
    client = app.test_client()
    login_sample_student(client)
    page = client.get("/sessions")
    assert page.status_code == 200
    assert "expired" in page.get_data(as_text=True)
    db.session.refresh(booking)
    assert booking.status == STATUS_EXPIRED
    assert booking.payment_status == "released"
