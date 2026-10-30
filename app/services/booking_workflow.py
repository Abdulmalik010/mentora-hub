"""Booking request state machine: explicit transitions, atomic, authorized.

Students request sessions; professors accept, decline or propose an
alternative; students may cancel or answer a proposal. Requests expire after
48 hours. Every transition flips status with a conditional UPDATE (the
loser of a race sees rowcount 0), and the partial unique index keeps two
active bookings off the same slot. ``completed`` is terminal vocabulary for
the later session-notes step; nothing transitions into it yet.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import Booking, User
from .booking import (
    ACTIVE_STATUSES,
    STATUS_ACCEPTED,
    STATUS_CANCELLED,
    STATUS_DECLINED,
    STATUS_EXPIRED,
    STATUS_PROPOSED,
    STATUS_REQUESTED,
    SlotTakenError,
)
from .notifications import notify_transition
from .wallet import capture_entries, release_entries

Actor = Literal["professor", "student", "system"]


class BookingAuthError(PermissionError):
    """The actor may not apply this transition to this booking."""


class InvalidTransitionError(ValueError):
    """The action is not legal from the booking's current status."""


@dataclass(frozen=True)
class Transition:
    """One legal edge: action, origin, destination, permitted actor."""

    action: str
    frm: str
    to: str
    actor: Actor


TRANSITIONS: dict[tuple[str, str], Transition] = {
    (STATUS_REQUESTED, "accept"): Transition(
        "accept", STATUS_REQUESTED, STATUS_ACCEPTED, "professor"
    ),
    (STATUS_REQUESTED, "decline"): Transition(
        "decline", STATUS_REQUESTED, STATUS_DECLINED, "professor"
    ),
    (STATUS_REQUESTED, "propose"): Transition(
        "propose", STATUS_REQUESTED, STATUS_PROPOSED, "professor"
    ),
    (STATUS_REQUESTED, "cancel"): Transition(
        "cancel", STATUS_REQUESTED, STATUS_CANCELLED, "student"
    ),
    (STATUS_REQUESTED, "expire"): Transition(
        "expire", STATUS_REQUESTED, STATUS_EXPIRED, "system"
    ),
    (STATUS_PROPOSED, "accept_proposal"): Transition(
        "accept_proposal", STATUS_PROPOSED, STATUS_ACCEPTED, "student"
    ),
    (STATUS_PROPOSED, "decline_proposal"): Transition(
        "decline_proposal", STATUS_PROPOSED, STATUS_CANCELLED, "student"
    ),
    (STATUS_PROPOSED, "expire"): Transition(
        "expire", STATUS_PROPOSED, STATUS_EXPIRED, "system"
    ),
}


def utcnow_naive() -> datetime:
    """Current UTC in the naive persistence form."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _authorize(
    booking: Booking, actor: Actor, actor_user: User | None
) -> None:
    """Raise BookingAuthError unless the actor owns this side."""
    if actor == "system":
        if actor_user is not None:
            raise BookingAuthError("system transitions take no user")
        return
    if actor_user is None or actor_user.role != actor:
        raise BookingAuthError(f"only the {actor} may do this")
    owner_id = (
        booking.professor_id if actor == "professor" else booking.student_id
    )
    if actor_user.id != owner_id:
        raise BookingAuthError("not your booking")


def _slot_occupied(
    professor_id: int, start: datetime, *, exclude_booking_id: int
) -> bool:
    """True when another active booking already holds the slot."""
    return (
        db.session.query(Booking.id)
        .filter(
            Booking.professor_id == professor_id,
            Booking.scheduled_at == start,
            Booking.status.in_(ACTIVE_STATUSES),
            Booking.id != exclude_booking_id,
        )
        .first()
        is not None
    )


def apply_transition(
    booking_id: int,
    action: str,
    *,
    actor_user: User | None,
    reason: str = "",
    new_start: datetime | None = None,
    now: datetime | None = None,
) -> Booking:
    """Apply one transition atomically; return the refreshed booking.

    Raises BookingAuthError (wrong actor), InvalidTransitionError (illegal
    action, missing reason/slot, or a lost race) and SlotTakenError (the
    proposal target was taken first).
    """
    current = now or utcnow_naive()
    booking = db.session.get(Booking, booking_id)
    if booking is None:
        raise InvalidTransitionError("unknown booking")
    if (
        booking.status in (STATUS_REQUESTED, STATUS_PROPOSED)
        and booking.expires_at is not None
        and booking.expires_at <= current
        and action != "expire"
    ):
        expire_booking(booking.id, now=current)
        raise InvalidTransitionError("request expired")
    edge = TRANSITIONS.get((booking.status, action))
    if edge is None:
        raise InvalidTransitionError(
            f"cannot {action} a {booking.status} booking"
        )
    _authorize(booking, edge.actor, actor_user)
    values: dict[str, Any] = {"status": edge.to}
    if action == "accept":
        values.update(decided_at=current, payment_status="captured")
    elif action == "decline":
        if not reason.strip():
            raise InvalidTransitionError("a decline reason is required")
        values.update(
            decided_at=current,
            decline_reason=reason.strip()[:500],
            payment_status="released",
        )
    elif action == "propose":
        if new_start is None:
            raise InvalidTransitionError("a proposed slot is required")
        if new_start <= current:
            raise InvalidTransitionError("proposed slot must be in the future")
        if _slot_occupied(
            booking.professor_id, new_start, exclude_booking_id=booking.id
        ):
            raise SlotTakenError("proposed slot is already taken")
        values.update(
            decided_at=current,
            proposed_start=new_start,
            decline_reason=None,
        )
    elif action == "cancel":
        values.update(decided_at=current, payment_status="released")
    elif action == "accept_proposal":
        if booking.proposed_start is None:
            raise InvalidTransitionError("no proposal to accept")
        if _slot_occupied(
            booking.professor_id,
            booking.proposed_start,
            exclude_booking_id=booking.id,
        ):
            raise SlotTakenError("proposed slot was just taken")
        values.update(
            scheduled_at=booking.proposed_start,
            proposed_start=None,
            decided_at=current,
            payment_status="captured",
        )
    elif action == "decline_proposal":
        values.update(
            proposed_start=None, decided_at=current,
            payment_status="released",
        )
    elif action == "expire":
        values.update(decided_at=current, payment_status="released")
    if action in ("accept", "accept_proposal"):
        ledger = capture_entries(booking)
    elif action in ("decline", "cancel", "decline_proposal", "expire"):
        ledger = release_entries(booking)
    else:  # propose: the original hold stays put
        ledger = []
    db.session.add_all(ledger)
    try:
        rowcount = (
            db.session.query(Booking)
            .filter_by(id=booking.id, status=edge.frm)
            .update(values, synchronize_session=False)
        )
        if rowcount == 0:
            db.session.rollback()
            raise InvalidTransitionError("booking changed; please retry")
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise SlotTakenError("slot was just taken") from None
    refreshed = db.session.get(Booking, booking.id)
    assert refreshed is not None  # just updated it
    return refreshed


def expire_booking(booking_id: int, now: datetime | None = None) -> bool:
    """Expire one request if still pending; True when it flipped."""
    current = now or utcnow_naive()
    booking = db.session.get(Booking, booking_id)
    if booking is None:
        return False
    db.session.add_all(release_entries(booking))
    rowcount = (
        db.session.query(Booking)
        .filter(
            Booking.id == booking_id,
            Booking.status.in_((STATUS_REQUESTED, STATUS_PROPOSED)),
            Booking.expires_at.is_not(None),
            Booking.expires_at <= current,
        )
        .update(
            {
                "status": STATUS_EXPIRED,
                "decided_at": current,
                "payment_status": "released",
            },
            synchronize_session=False,
        )
    )
    if not rowcount:
        db.session.rollback()
        return False
    db.session.commit()
    notify_transition(booking_id, "expired")
    return True


def expire_stale_bookings(now: datetime | None = None) -> list[int]:
    """Expire every stale request; return the flipped booking ids."""
    current = now or utcnow_naive()
    ids = [
        row[0]
        for row in db.session.query(Booking.id)
        .filter(
            Booking.status.in_((STATUS_REQUESTED, STATUS_PROPOSED)),
            Booking.expires_at.is_not(None),
            Booking.expires_at <= current,
        )
        .all()
    ]
    return [bid for bid in ids if expire_booking(bid, now=current)]
