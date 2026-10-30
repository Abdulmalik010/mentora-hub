"""Demo wallet: ledger-based balances, holds, captures, releases.

Students start with 100,000 demo credits (a constant, not stored). A request
places a hold; accept captures it (professor credited minus a 10% platform
fee); decline, cancel and expiry release it. Balances derive from the ledger
plus the opening grant — no stored balances anywhere. Every amount the UI
shows is labeled demo. Free sessions (zero rate) skip the ledger entirely.
"""
from __future__ import annotations

from ..extensions import db
from ..models import Booking, LedgerEntry, User

OPENING_STUDENT_CREDITS = 100_000
PLATFORM_FEE_PCT = 10

TYPE_HOLD = "hold"
TYPE_CAPTURE = "capture"
TYPE_RELEASE = "release"
TYPE_PLATFORM_FEE = "platform_fee"


class InsufficientFundsError(ValueError):
    """The student's available demo credits do not cover the hold."""


def _hold_rows(user_id: int) -> dict[int, int]:
    """Booking id to held amount for one user's hold entries."""
    return {
        row.booking_id: row.amount
        for row in LedgerEntry.query.filter_by(
            user_id=user_id, type=TYPE_HOLD
        ).all()
    }


def _terminal_bookings(user_id: int) -> set[int]:
    """Bookings whose hold already resolved (release or student capture)."""
    return {
        row.booking_id
        for row in LedgerEntry.query.filter(
            LedgerEntry.user_id == user_id,
            LedgerEntry.type.in_([TYPE_RELEASE, TYPE_CAPTURE]),
        ).all()
    }


def active_holds_total(user_id: int) -> int:
    """Sum of holds with no terminal entry yet."""
    holds = _hold_rows(user_id)
    terminal = _terminal_bookings(user_id)
    return sum(
        amount for booking_id, amount in holds.items()
        if booking_id not in terminal
    )


def demo_balance(user: User) -> int:
    """Spendable demo credits (students) or earnings (professors).

    Captures classify by booking side: a capture on the student side is a
    charge, on the professor side an earning. Holds count until released
    or captured.
    """
    opening = OPENING_STUDENT_CREDITS if user.role == "student" else 0
    captures = (
        db.session.query(LedgerEntry.amount, Booking.student_id)
        .join(Booking, LedgerEntry.booking_id == Booking.id)
        .filter(
            LedgerEntry.user_id == user.id,
            LedgerEntry.type == TYPE_CAPTURE,
        )
        .all()
    )
    charges = sum(
        amount for amount, student_id in captures if student_id == user.id
    )
    earnings = sum(
        amount for amount, student_id in captures if student_id != user.id
    )
    return opening + earnings - charges - active_holds_total(user.id)


def hold_amount(booking_id: int) -> int:
    """The request-time hold amount (0 when the session is free)."""
    row = LedgerEntry.query.filter_by(
        booking_id=booking_id, type=TYPE_HOLD
    ).first()
    return row.amount if row else 0


def platform_fee_for(amount: int) -> int:
    """Whole-naira 10% platform cut (rounds down, professor keeps rest)."""
    return amount * PLATFORM_FEE_PCT // 100


def place_hold(student: User, booking_id: int, amount: int) -> LedgerEntry:
    """Reserve funds; raises InsufficientFundsError when not covered.

    Adds the row without committing (the caller owns the transaction).
    Zero-amount sessions skip the ledger, so callers must not place
    zero holds.
    """
    if amount <= 0:
        raise ValueError("place_hold needs a positive amount")
    if demo_balance(student) < amount:
        raise InsufficientFundsError(
            f"Insufficient demo credits: need ₦{amount:,}, "
            f"have ₦{demo_balance(student):,}."
        )
    entry = LedgerEntry(
        user_id=student.id, booking_id=booking_id, type=TYPE_HOLD,
        amount=amount,
    )
    db.session.add(entry)
    return entry


def _already_settled(booking_id: int, student_id: int) -> bool:
    """True when the booking's hold already captured or released."""
    return (
        LedgerEntry.query.filter(
            LedgerEntry.booking_id == booking_id,
            LedgerEntry.user_id == student_id,
            LedgerEntry.type.in_([TYPE_CAPTURE, TYPE_RELEASE]),
        ).first()
        is not None
    )


def capture_entries(booking: Booking) -> list[LedgerEntry]:
    """Transient capture rows (student charge, professor credit, fee).

    Empty for free sessions or already-settled holds (idempotent).
    """
    amount = hold_amount(booking.id)
    if amount <= 0 or _already_settled(booking.id, booking.student_id):
        return []
    fee = platform_fee_for(amount)
    return [
        LedgerEntry(
            user_id=booking.student_id, booking_id=booking.id,
            type=TYPE_CAPTURE, amount=amount,
        ),
        LedgerEntry(
            user_id=booking.professor_id, booking_id=booking.id,
            type=TYPE_CAPTURE, amount=amount - fee,
        ),
        LedgerEntry(
            user_id=None, booking_id=booking.id, type=TYPE_PLATFORM_FEE,
            amount=fee,
        ),
    ]


def release_entries(booking: Booking) -> list[LedgerEntry]:
    """Transient release row freeing the hold (idempotent, [] when free)."""
    amount = hold_amount(booking.id)
    if amount <= 0 or _already_settled(booking.id, booking.student_id):
        return []
    return [
        LedgerEntry(
            user_id=booking.student_id, booking_id=booking.id,
            type=TYPE_RELEASE, amount=amount,
        )
    ]
