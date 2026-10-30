"""Per-booking messaging: threads, posting, read state, rate limits.

One thread per booking from the moment the request is placed. Both parties
may post while the booking is requested, accepted or reschedule_proposed;
terminal bookings are read-only. Bodies cap at 2000 chars, HTML is escaped
at render (templates) and at DOM insert (poll script uses textContent).
Posting is rate-limited to 20 messages per minute per user (DB-backed, so
it holds across processes).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from ..extensions import db
from ..models import Booking, Message, User

POSTABLE_STATUSES = frozenset(
    {"requested", "accepted", "reschedule_proposed"}
)
MAX_BODY_CHARS = 2000
RATE_LIMIT_PER_MINUTE = 20
RATE_WINDOW = timedelta(minutes=1)


class ThreadLockedError(PermissionError):
    """The booking is decided; its thread is read-only."""


class RateLimitedError(ValueError):
    """Too many messages too fast; slow down."""


def _is_party(booking: Booking, user_id: int) -> bool:
    """True when the user is the booking's student or professor."""
    return user_id in (booking.student_id, booking.professor_id)


def post_message(booking_id: int, sender: User, body: str) -> Message:
    """Validate and persist one message; raises on any rule breach.

    Raises LookupError (unknown booking or non-party sender),
    ThreadLockedError (terminal booking), ValueError (empty/oversize
    body) and RateLimitedError (over 20/minute).
    """
    booking = db.session.get(Booking, booking_id)
    if booking is None or not _is_party(booking, sender.id):
        raise LookupError("unknown booking")
    if booking.status not in POSTABLE_STATUSES:
        raise ThreadLockedError("this thread is read-only")
    text = (body or "").strip()
    if not text:
        raise ValueError("message body is required")
    if len(text) > MAX_BODY_CHARS:
        raise ValueError("message body must be 2000 characters or fewer")
    since = datetime.now(timezone.utc).replace(tzinfo=None) - RATE_WINDOW
    recent = Message.query.filter(
        Message.sender_id == sender.id, Message.created_at > since
    ).count()
    if recent >= RATE_LIMIT_PER_MINUTE:
        raise RateLimitedError("too many messages; wait a minute")
    message = Message(booking_id=booking.id, sender_id=sender.id, body=text)
    db.session.add(message)
    db.session.commit()
    return message


def mark_thread_read(booking_id: int, user_id: int) -> int:
    """Mark the other party's messages read; return how many flipped."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    flipped = (
        Message.query.filter(
            Message.booking_id == booking_id,
            Message.sender_id != user_id,
            Message.read_at.is_(None),
        ).update({"read_at": now}, synchronize_session=False)
    )
    db.session.commit()
    return flipped


def unread_message_count(user_id: int) -> int:
    """Unread messages across all threads the user participates in."""
    booking_ids = [
        row[0]
        for row in db.session.query(Booking.id)
        .filter(
            (Booking.student_id == user_id)
            | (Booking.professor_id == user_id)
        )
        .all()
    ]
    if not booking_ids:
        return 0
    return Message.query.filter(
        Message.booking_id.in_(booking_ids),
        Message.sender_id != user_id,
        Message.read_at.is_(None),
    ).count()


def get_threads(user_id: int) -> list[dict[str, object]]:
    """Thread summaries for one user, most recently active first."""
    bookings = (
        Booking.query.filter(
            (Booking.student_id == user_id)
            | (Booking.professor_id == user_id)
        ).all()
    )
    threads = []
    for booking in bookings:
        last = (
            Message.query.filter_by(booking_id=booking.id)
            .order_by(Message.id.desc())
            .first()
        )
        other_id = (
            booking.professor_id
            if booking.student_id == user_id
            else booking.student_id
        )
        threads.append(
            {
                "booking": booking,
                "other": db.session.get(User, other_id),
                "last_message": last,
                "unread": Message.query.filter(
                    Message.booking_id == booking.id,
                    Message.sender_id != user_id,
                    Message.read_at.is_(None),
                ).count(),
                "activity": (
                    last.created_at if last else booking.created_at
                ),
            }
        )
    threads.sort(key=lambda row: row["activity"] or datetime.min, reverse=True)
    return threads
