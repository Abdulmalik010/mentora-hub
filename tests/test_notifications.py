"""Notification tests: inbox, bell, per-transition fan-out. No network."""
from __future__ import annotations

from datetime import datetime, timedelta

from flask import Flask

from app.extensions import db
from app.models import Booking, EmailLog, Notification, User
from app.services.booking_workflow import expire_stale_bookings, utcnow_naive
from app.services.email_service import (
    KIND_CONFIRMED_PROFESSOR,
    KIND_CONFIRMED_STUDENT,
    KIND_DECLINED_STUDENT,
    KIND_REQUEST_PROFESSOR,
    KIND_REQUEST_STUDENT,
)
from app.services.notifications import (
    KIND_ACCEPTED,
    KIND_DECLINED,
    KIND_EXPIRED,
    KIND_PROPOSAL,
    KIND_REQUEST_CREATED,
    mark_all_read,
    notify,
    unread_count,
)
from tests.test_booking import login_sample_student, seed_booking_case
from tests.test_professor import login_professor
from tests.test_workflow import force_status, open_proposal_slot, seed_request


def test_notify_count_and_mark_read(app: Flask) -> None:
    """Rows start unread; mark-all-read flips exactly the user's own."""
    student_id = seed_booking_case()[0].student_id
    assert unread_count(student_id) == 0
    notify(student_id, KIND_ACCEPTED, "Accepted", "slot", "/sessions/1")
    notify(student_id, KIND_DECLINED, "Declined")
    assert unread_count(student_id) == 2
    assert mark_all_read(student_id) == 2
    assert unread_count(student_id) == 0
    other = User.query.filter_by(email="sample-student-02@example.com").one()
    assert unread_count(other.id) == 0


def test_inbox_bell_and_count_endpoint(app: Flask) -> None:
    """Inbox lists newest first; bell badge and count follow unread state."""
    case, _prof_id = seed_booking_case()
    client = app.test_client()
    assert client.get("/notifications").status_code == 302
    assert client.get("/notifications/unread-count").status_code == 302
    login_sample_student(client)
    notify(case.student_id, KIND_ACCEPTED, "Accepted!")
    notify(case.student_id, KIND_DECLINED, "Declined.")
    inbox = client.get("/notifications")
    assert inbox.status_code == 200
    html = inbox.get_data(as_text=True)
    assert html.index("Declined.") < html.index("Accepted!")  # newest first
    assert html.count(">new<") == 2
    assert 'data-unread-count' in html
    count = client.get("/notifications/unread-count")
    assert count.get_json() == {"count": 2}
    read = client.post("/notifications/read-all")
    assert read.status_code == 303
    assert client.get("/notifications/unread-count").get_json() == {"count": 0}
    assert ">new<" not in client.get("/notifications").get_data(as_text=True)


def test_checkout_notifies_professor_and_mails_both(app: Flask) -> None:
    """A posted request notifies the professor and sends the request emails."""
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
            "idempotency_token": "tok-notify-1",
        },
    )
    assert response.status_code == 303
    from app.models import Booking

    booking = Booking.query.one()
    prof_notes = Notification.query.filter_by(user_id=prof_id).all()
    assert [(note.kind, note.url) for note in prof_notes] == [
        (KIND_REQUEST_CREATED, f"/dashboard/bookings/{booking.id}")
    ]
    assert "Sample Student 01" in prof_notes[0].title
    assert Notification.query.filter_by(user_id=case.student_id).count() == 0
    kinds = {
        row.kind
        for row in EmailLog.query.filter_by(booking_id=booking.id).all()
    }
    assert kinds == {KIND_REQUEST_PROFESSOR, KIND_REQUEST_STUDENT}


def test_accept_notifies_and_mails_both(app: Flask) -> None:
    """Accept notifies the student and sends both confirmed emails."""
    booking = seed_request()
    client = app.test_client()
    login_professor(client, 12)
    response = client.post(f"/dashboard/bookings/{booking.id}/accept")
    assert response.status_code == 303
    notes = Notification.query.filter_by(user_id=booking.student_id).all()
    assert [(note.kind, note.url) for note in notes] == [
        (KIND_ACCEPTED, f"/sessions/{booking.id}")
    ]
    assert "Dr. Chiamaka Obi" in notes[0].title
    kinds = {
        row.kind
        for row in EmailLog.query.filter_by(booking_id=booking.id).all()
    }
    assert kinds == {KIND_CONFIRMED_PROFESSOR, KIND_CONFIRMED_STUDENT}


def test_decline_and_propose_notify_student(app: Flask) -> None:
    """Decline carries the reason; proposal carries the new slot."""
    first = seed_request(datetime(2026, 11, 4, 9, 0))
    second = seed_request(datetime(2026, 11, 18, 9, 0))
    client = app.test_client()
    login_professor(client, 12)
    client.post(
        f"/dashboard/bookings/{first.id}/decline",
        data={"reason": "Conference week."},
    )
    new_slot = open_proposal_slot(second)
    client.post(
        f"/dashboard/bookings/{second.id}/propose",
        data={"new_slot": new_slot.key},
    )
    notes = Notification.query.filter_by(user_id=first.student_id).order_by(
        Notification.id
    ).all()
    assert [note.kind for note in notes] == [KIND_DECLINED, KIND_PROPOSAL]
    assert notes[0].body == "Conference week."
    assert "WAT" in notes[1].body
    declined = EmailLog.query.filter_by(
        booking_id=first.id, kind=KIND_DECLINED_STUDENT
    ).one()
    assert declined.status == "sent"
    assert EmailLog.query.filter_by(booking_id=second.id).count() == 0


def test_expiry_notifies_student(app: Flask) -> None:
    """The sweep notifies each expired request's student exactly once."""
    booking = seed_request()
    force_status(
        booking, "requested",
        expires_at=utcnow_naive() - timedelta(hours=1),
    )
    assert expire_stale_bookings() == [booking.id]
    notes = Notification.query.filter_by(user_id=booking.student_id).all()
    assert [note.kind for note in notes] == [KIND_EXPIRED]
    assert expire_stale_bookings() == []  # second sweep is silent
    assert Notification.query.filter_by(user_id=booking.student_id).count() == 1


def test_cancel_and_answers_stay_silent(app: Flask) -> None:
    """Cancels and proposal answers send no notifications (spec: 5 events)."""
    booking = seed_request(datetime(2026, 11, 4, 9, 0))
    client = app.test_client()
    login_sample_student(client)
    client.post(f"/sessions/{booking.id}/cancel")
    assert Notification.query.count() == 0

    other = seed_request(datetime(2026, 11, 18, 9, 0))
    login_professor(client, 12)
    new_slot = open_proposal_slot(other)
    client.post(
        f"/dashboard/bookings/{other.id}/propose",
        data={"new_slot": new_slot.key},
    )
    assert Notification.query.count() == 1  # the proposal itself
    login_sample_student(client)
    client.post(f"/sessions/{other.id}/proposal/accept")
    assert Notification.query.count() == 1  # the answer is silent
    assert db.session.get(Booking, other.id).status == "accepted"
