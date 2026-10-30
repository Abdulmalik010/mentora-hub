"""Auth blueprint: register, login, logout over Flask sessions."""
from __future__ import annotations

from flask import (
    Blueprint,
    Response,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from ..extensions import db
from ..models import ProfessorProfile, StudentProfile, User

bp = Blueprint("auth", __name__)

VALID_ROLES = ("student", "professor")
STUDENT_LEVELS = ("undergraduate", "masters", "phd")
DEPARTMENTS = (
    "Statistics",
    "Computer Science",
    "Economics",
    "English Literature",
)
MIN_PASSWORD_LEN = 8


@bp.get("/health")
def health() -> dict[str, str]:
    """Liveness probe for the auth blueprint."""
    return {"status": "ok", "blueprint": "auth"}


def _register_context() -> dict[str, object]:
    """Select options shared by the register form renders."""
    return {"roles": VALID_ROLES, "levels": STUDENT_LEVELS, "departments": DEPARTMENTS}


@bp.get("/register")
def register_form() -> str:
    """Render the registration form."""
    return render_template("auth/register.html", **_register_context())


@bp.post("/register")
def register() -> Response | tuple[str, int]:
    """Create a user plus matching profile; log them in on success."""
    display_name = request.form.get("display_name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    role = request.form.get("role", "")
    level = request.form.get("level", "")
    field = request.form.get("field", "").strip()
    department = request.form.get("department", "")

    error: str | None = None
    if not display_name or not email or not password or role not in VALID_ROLES:
        error = "Name, email, password and a valid role are required."
    elif len(password) < MIN_PASSWORD_LEN:
        error = f"Password must be at least {MIN_PASSWORD_LEN} characters."
    elif User.query.filter_by(email=email).first() is not None:
        error = "That email is already registered."
    elif role == "student" and (level not in STUDENT_LEVELS or not field):
        error = "Students need a level and a field of study."
    elif role == "professor" and department not in DEPARTMENTS:
        error = "Professors need a department."
    if error is not None:
        flash(error, "error")
        return render_template("auth/register.html", **_register_context()), 400

    user = User(display_name=display_name, email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.flush()
    if role == "student":
        db.session.add(StudentProfile(user_id=user.id, level=level, field=field))
    else:
        db.session.add(
            ProfessorProfile(
                user_id=user.id,
                department=department,
                research_areas=[],
                bio="",
                availability={},
            )
        )
    db.session.commit()
    session["user_id"] = user.id
    flash("Registered and logged in.", "ok")
    if role == "professor":
        return redirect(url_for("profiles.setup"))
    return redirect(url_for("index"))


@bp.get("/login")
def login_form() -> str:
    """Render the login form."""
    return render_template("auth/login.html")


def _safe_next(raw: str) -> str:
    """Allow only relative redirect targets (open-redirect guard)."""
    if raw.startswith("/") and not raw.startswith("//"):
        return raw
    return url_for("index")


@bp.post("/login")
def login() -> Response | tuple[str, int]:
    """Check credentials; generic error on failure (no account enumeration)."""
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    user = User.query.filter_by(email=email).first()
    if user is None or not user.check_password(password):
        flash("Invalid email or password.", "error")
        return render_template("auth/login.html"), 401
    session["user_id"] = user.id
    flash("Logged in.", "ok")
    target = request.form.get("next") or request.args.get("next") or ""
    return redirect(_safe_next(target))


@bp.post("/logout")
def logout() -> Response:
    """Clear the session and return to the home page."""
    session.pop("user_id", None)
    flash("Logged out.", "ok")
    return redirect(url_for("index"))
