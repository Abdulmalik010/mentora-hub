"""Session helpers and route guards for blueprint views."""
from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from flask import abort, redirect, request, session, url_for

from .extensions import db
from .models import User

F = TypeVar("F", bound=Callable[..., Any])


def current_user() -> User | None:
    """User for the current session, or None when logged out."""
    user_id = session.get("user_id")
    if user_id is None:
        return None
    return db.session.get(User, user_id)


def login_required(view: F) -> F:
    """Redirect anonymous visitors to the login page (preserving target)."""
    @wraps(view)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if current_user() is None:
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)

    return wrapper  # type: ignore[return-value]


def role_required(role: str) -> Callable[[F], F]:
    """Require login plus an exact User.role; 403 on role mismatch."""
    def decorator(view: F) -> F:
        @wraps(view)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            user = current_user()
            if user is None:
                return redirect(url_for("auth.login", next=request.path))
            if user.role != role:
                abort(403)
            return view(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator
