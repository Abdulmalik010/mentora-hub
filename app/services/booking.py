"""Race-safe booking creation with Jitsi links and demo payment refs."""
from __future__ import annotations

import secrets
import time
from datetime import datetime

from sqlalchemy.exc import IntegrityError, OperationalError

from ..extensions import db
from ..models import Booking

MEETING_ROOM_PREFIX = "mentora-"
COMMIT_RETRIES = 3


class SlotTakenError(ValueError):
    """The requested slot was booked first by someone else."""


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
) -> Booking:
    """Persist one booking; raise SlotTakenError when the slot is gone.

    Consent is mandatory. A pre-check gives the friendly path; the
    (professor, start) unique constraint is the race-safe backstop, with a
    short retry on transient SQLite lock errors.
    """
    if not consent_share_diagnosis:
        raise ValueError("consent to share the diagnosis is required")
    taken = Booking.query.filter_by(
        professor_id=professor_id, scheduled_at=start_naive_utc
    ).first()
    if taken is not None:
        raise SlotTakenError("that slot was just booked; pick another")
    booking = Booking(
        student_id=student_id,
        professor_id=professor_id,
        case_id=case_id,
        status="confirmed",
        scheduled_at=start_naive_utc,
        meeting_url=meeting_url(),
        consent_share_diagnosis=True,
        mock_payment_ref=f"DEMO-{secrets.token_hex(4).upper()}",
    )
    for attempt in range(COMMIT_RETRIES):
        try:
            db.session.add(booking)
            db.session.commit()
            return booking
        except IntegrityError:
            db.session.rollback()
            raise SlotTakenError(
                "that slot was just booked; pick another"
            ) from None
        except OperationalError:
            db.session.rollback()
            if attempt == COMMIT_RETRIES - 1:
                raise
            time.sleep(0.05 * (attempt + 1))
    raise SlotTakenError("could not book; please retry")  # unreachable
