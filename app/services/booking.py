"""Race-safe booking creation with Jitsi links and demo payment refs."""
from __future__ import annotations

import secrets
import threading
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError, OperationalError

from ..extensions import db
from ..models import Booking, ProfessorProfile, User
from .wallet import InsufficientFundsError, demo_balance, place_hold

STATUS_REQUESTED = "requested"
STATUS_ACCEPTED = "accepted"
STATUS_DECLINED = "declined"
STATUS_PROPOSED = "reschedule_proposed"
STATUS_CANCELLED = "cancelled"
STATUS_EXPIRED = "expired"
STATUS_COMPLETED = "completed"

ACTIVE_STATUSES = frozenset(
    {STATUS_REQUESTED, STATUS_ACCEPTED, STATUS_PROPOSED}
)
EXPIRY_HOURS = 48

MEETING_ROOM_PREFIX = "mentora-"
COMMIT_RETRIES = 3

_CREATE_LOCK = threading.Lock()


class SlotTakenError(ValueError):
    """The requested slot was booked first by someone else."""


class DuplicateCheckoutError(ValueError):
    """This checkout token already produced a booking (retry, not new)."""

    def __init__(self, booking: Booking) -> None:
        super().__init__("this checkout was already completed")
        self.booking = booking


def meeting_url() -> str:
    """Fresh Jitsi room URL with an unguessable random token."""
    return f"https://meet.jit.si/{MEETING_ROOM_PREFIX}{secrets.token_urlsafe(6)}"


def create_booking(
    *,
    student_id: int,
    professor_id: int,
    case_id: int,
    start_naive_utc: datetime,
    consent_share_diagnosis: bool,
    idempotency_key: str,
) -> Booking:
    """Persist one booking as requested; SlotTakenError when occupied.

    Consent is mandatory. Only active statuses occupy a slot (pre-check
    plus the partial unique backstop), with a short retry on transient
    SQLite lock errors. A token that already produced a booking raises
    DuplicateCheckoutError with that booking. Payment is held (demo,
    InsufficientFundsError when the wallet cannot cover it) and the
    request expires after 48 hours. The whole check-then-insert runs
    under a process lock; a multi-process deploy would need row locking.
    """
    with _CREATE_LOCK:
        return _create_booking_inner(
            student_id=student_id,
            professor_id=professor_id,
            case_id=case_id,
            start_naive_utc=start_naive_utc,
            consent_share_diagnosis=consent_share_diagnosis,
            idempotency_key=idempotency_key,
        )


def _create_booking_inner(
    *,
    student_id: int,
    professor_id: int,
    case_id: int,
    start_naive_utc: datetime,
    consent_share_diagnosis: bool,
    idempotency_key: str,
) -> Booking:
    """Creation body; always runs under ``_CREATE_LOCK``."""
    if not consent_share_diagnosis:
        raise ValueError("consent to share the diagnosis is required")
    if not idempotency_key:
        raise ValueError("idempotency_key is required")
    student = db.session.get(User, student_id)
    if student is None:
        raise ValueError("unknown student")
    duplicate = Booking.query.filter_by(idempotency_key=idempotency_key).first()
    if duplicate is not None:
        raise DuplicateCheckoutError(duplicate)
    taken = (
        Booking.query.filter_by(
            professor_id=professor_id, scheduled_at=start_naive_utc
        )
        .filter(Booking.status.in_(ACTIVE_STATUSES))
        .first()
    )
    if taken is not None:
        raise SlotTakenError("that slot was just booked; pick another")
    profile = ProfessorProfile.query.filter_by(user_id=professor_id).first()
    amount = max(0, int(profile.rate or 0)) if profile else 0
    if amount > 0 and demo_balance(student) < amount:
        raise InsufficientFundsError(
            f"Insufficient demo credits: need ₦{amount:,}, "
            f"have ₦{demo_balance(student):,}."
        )
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    booking = Booking(
        student_id=student_id,
        professor_id=professor_id,
        case_id=case_id,
        idempotency_key=idempotency_key,
        status="requested",
        scheduled_at=start_naive_utc,
        expires_at=now + timedelta(hours=EXPIRY_HOURS),
        payment_status="held",
        meeting_url=meeting_url(),
        consent_share_diagnosis=True,
        mock_payment_ref=f"DEMO-{secrets.token_hex(4).upper()}",
    )
    for attempt in range(COMMIT_RETRIES):
        try:
            db.session.add(booking)
            db.session.flush()  # assigns the id; may surface the slot race
            if amount > 0:
                place_hold(student, booking.id, amount)
            db.session.commit()
            return booking
        except IntegrityError:
            db.session.rollback()
            raced = Booking.query.filter_by(
                idempotency_key=idempotency_key
            ).first()
            if raced is not None:
                raise DuplicateCheckoutError(raced) from None
            raise SlotTakenError(
                "that slot was just booked; pick another"
            ) from None
        except InsufficientFundsError:
            db.session.rollback()
            raise
        except OperationalError:
            db.session.rollback()
            if attempt == COMMIT_RETRIES - 1:
                raise
            time.sleep(0.05 * (attempt + 1))
    raise SlotTakenError("could not book; please retry")  # unreachable
