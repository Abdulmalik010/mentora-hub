"""Per-booking message threads for both parties (both roles)."""
from __future__ import annotations

from flask import (
    Blueprint, Response, abort, current_app, flash, jsonify, redirect,
    render_template, request, url_for,
)

from ..extensions import db
from ..models import Booking, Message, User
from ..security import current_user, login_required
from ..services.email_service import send_message_email
from ..services.messaging import (
    POSTABLE_STATUSES,
    RateLimitedError,
    ThreadLockedError,
    get_threads,
    mark_thread_read,
    post_message,
)
from ..services.notifications import notify_new_message

bp = Blueprint("inbox", __name__)


def _party_booking_or_404(booking_id: int) -> tuple[Booking, User]:
    """Booking plus current user; 404 unless they are a party to it."""
    booking = db.session.get(Booking, booking_id)
    user = current_user()
    if (
        booking is None
        or user is None
        or user.id not in (booking.student_id, booking.professor_id)
    ):
        abort(404)
    return booking, user


@bp.get("/inbox")
@login_required
def thread_list() -> str:
    """Thread summaries, most recently active first."""
    user = current_user()
    assert user is not None  # guaranteed by login_required
    return render_template("inbox/list.html", threads=get_threads(user.id))


def _render_thread(
    booking: Booking, user: User, status: int = 200
) -> tuple[str, int]:
    """Thread page with messages oldest-first."""
    other_id = (
        booking.professor_id
        if user.id == booking.student_id
        else booking.student_id
    )
    messages = (
        Message.query.filter_by(booking_id=booking.id)
        .order_by(Message.id.asc())
        .all()
    )
    return (
        render_template(
            "inbox/thread.html",
            booking=booking,
            other=db.session.get(User, other_id),
            messages=messages,
            locked=booking.status not in POSTABLE_STATUSES,
        ),
        status,
    )


@bp.get("/inbox/<int:booking_id>")
@login_required
def thread(booking_id: int) -> tuple[str, int]:
    """One thread; opening it marks the other party's messages read."""
    booking, user = _party_booking_or_404(booking_id)
    mark_thread_read(booking.id, user.id)
    return _render_thread(booking, user)


@bp.get("/inbox/<int:booking_id>/messages")
@login_required
def poll(booking_id: int) -> Response:
    """Messages after ?after=<id> as JSON (the 5s poll endpoint)."""
    booking, user = _party_booking_or_404(booking_id)
    try:
        after = int(request.args.get("after", "0"))
    except ValueError:
        after = 0
    rows = (
        Message.query.filter(
            Message.booking_id == booking.id, Message.id > after
        )
        .order_by(Message.id.asc())
        .limit(100)
        .all()
    )
    return jsonify(
        {
            "messages": [
                {
                    "id": row.id,
                    "sender_name": (
                        row.sender.display_name if row.sender else "?"
                    ),
                    "body": row.body,
                    "mine": row.sender_id == user.id,
                    "created_at": row.created_at.isoformat(),
                }
                for row in rows
            ]
        }
    )


@bp.post("/inbox/<int:booking_id>/messages")
@login_required
def send(booking_id: int) -> Response:
    """Post one message; 303 back to the thread on success."""
    booking, user = _party_booking_or_404(booking_id)
    try:
        message = post_message(booking.id, user, request.form.get("body", ""))
    except ThreadLockedError:
        abort(403)
    except RateLimitedError as exc:
        flash(str(exc), "error")
        return _render_thread(booking, user, 429)
    except ValueError as exc:
        flash(str(exc), "error")
        return _render_thread(booking, user, 400)
    try:
        other_id = (
            booking.professor_id
            if user.id == booking.student_id
            else booking.student_id
        )
        notify_new_message(other_id, booking.id, user.display_name)
        send_message_email(
            booking.id, user.id,
            thread_url=url_for(
                "inbox.thread", booking_id=booking.id, _external=True
            ),
            snippet=message.body,
        )
    except Exception:  # noqa: BLE001 — pings must never break posting
        current_app.logger.exception("message ping failed")
    return redirect(url_for("inbox.thread", booking_id=booking.id), code=303)
