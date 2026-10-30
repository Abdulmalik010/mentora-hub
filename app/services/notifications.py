"""Inbox notifications: create rows, count unread, mark read."""
from __future__ import annotations

from datetime import datetime, timezone

from ..extensions import db
from ..models import Booking, Notification, User
from .slots import format_wat

KIND_REQUEST_CREATED = "request_created"
KIND_ACCEPTED = "accepted"
KIND_DECLINED = "declined"
KIND_PROPOSAL = "proposal"
KIND_EXPIRED = "expired"


def notify(
    user_id: int, kind: str, title: str, body: str = "", url: str = ""
) -> Notification:
    """Persist one unread notification and return it."""
    note = Notification(
        user_id=user_id, kind=kind, title=title, body=body[:500],
        url=url[:500],
    )
    db.session.add(note)
    db.session.commit()
    return note


def unread_count(user_id: int) -> int:
    """Number of unread notifications for one user."""
    return Notification.query.filter_by(
        user_id=user_id, read_at=None
    ).count()


def mark_all_read(user_id: int) -> int:
    """Mark every notification read; return how many flipped."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    flipped = (
        Notification.query.filter_by(user_id=user_id, read_at=None)
        .update({"read_at": now}, synchronize_session=False)
    )
    db.session.commit()
    return flipped


def notify_transition(booking_id: int, event: str) -> Notification | None:
    """Emit the inbox notification for one booking event (spec: 5 events).

    Request creation notifies the professor; accept/decline/proposal/expiry
    notify the student. Cancels and proposal answers stay silent. Returns
    None when the booking or its parties are gone.
    """
    booking = db.session.get(Booking, booking_id)
    if booking is None:
        return None
    student = db.session.get(User, booking.student_id)
    professor = db.session.get(User, booking.professor_id)
    if student is None or professor is None:
        return None
    slot = format_wat(booking.scheduled_at) if booking.scheduled_at else "—"
    session_url = f"/sessions/{booking.id}"
    if event == "request_created":
        return notify(
            professor.id, KIND_REQUEST_CREATED,
            f"New session request from {student.display_name}",
            f"{slot} · respond within 48 hours",
            f"/dashboard/bookings/{booking.id}",
        )
    if event == "accepted":
        return notify(
            student.id, KIND_ACCEPTED,
            f"{professor.display_name} accepted your request",
            f"{slot} · meeting link revealed", session_url,
        )
    if event == "declined":
        return notify(
            student.id, KIND_DECLINED,
            f"{professor.display_name} declined your request",
            booking.decline_reason or "", session_url,
        )
    if event == "proposal":
        new = (
            format_wat(booking.proposed_start)
            if booking.proposed_start
            else "—"
        )
        return notify(
            student.id, KIND_PROPOSAL,
            f"{professor.display_name} proposed a new time",
            new, session_url,
        )
    if event == "expired":
        return notify(
            student.id, KIND_EXPIRED, "Your request expired",
            f"{slot} · the demo hold was released", session_url,
        )
    raise ValueError(f"unknown booking event: {event}")
