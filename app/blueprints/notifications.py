"""Inbox notifications: page, unread count, mark-all-read (both roles)."""
from __future__ import annotations

from flask import Blueprint, Response, jsonify, redirect, render_template, url_for

from ..extensions import db
from ..models import Notification
from ..security import current_user, login_required
from ..services.notifications import mark_all_read, unread_count

bp = Blueprint("notifications", __name__)


@bp.get("/notifications")
@login_required
def inbox() -> str:
    """The user's notifications, newest first."""
    user = current_user()
    assert user is not None  # guaranteed by login_required
    notes = (
        Notification.query.filter_by(user_id=user.id)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .all()
    )
    return render_template("notifications/inbox.html", notes=notes)


@bp.post("/notifications/read-all")
@login_required
def read_all() -> Response:
    """Mark every notification read, back to the inbox."""
    user = current_user()
    assert user is not None  # guaranteed by login_required
    mark_all_read(user.id)
    return redirect(url_for("notifications.inbox"), code=303)


@bp.get("/notifications/unread-count")
@login_required
def count() -> Response:
    """Unread badge number, polled by the nav bell (JSON)."""
    user = current_user()
    assert user is not None  # guaranteed by login_required
    return jsonify({"count": unread_count(user.id)})
