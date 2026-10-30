"""Profile editing: validation and persistence for both roles.

Professors edit title, name, rank, department, research areas, bio, rate,
timezone, weekly availability and the accepting toggle; display names stay
composed as "Title First Last" so matching, cards and emails agree.
Students edit display name, level and field.
"""
from __future__ import annotations

from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.exc import OperationalError

from ..extensions import db
from ..models import ProfessorProfile, StudentProfile, User
from .slots import WEEKDAYS, validate_availability

TITLES = ("Prof.", "Dr.", "Mr.", "Mrs.", "Ms.")
RANKS = (
    "Professor",
    "Associate Professor",
    "Senior Lecturer",
    "Lecturer I",
    "Lecturer II",
    "Assistant Lecturer",
)
FALLBACK_DEPARTMENTS = (
    "Statistics",
    "Computer Science",
    "Economics",
    "English Literature",
    "Biology",
    "Chemistry",
    "Physics",
    "Mathematics",
    "Civil Engineering",
    "Electrical Engineering",
    "Law",
    "Education",
    "Psychology",
    "Business Administration",
    "Agricultural Science",
)
MAX_AREAS = 8
MAX_BIO_CHARS = 2000


def department_choices() -> list[str]:
    """Distinct departments in the DB, or the canonical list when empty.

    Falls back when the table is empty or missing (pre-seed database), so
    registration and directory pages never 500 before the first seed.
    """
    try:
        rows = (
            db.session.query(ProfessorProfile.department)
            .distinct()
            .order_by(ProfessorProfile.department)
            .all()
        )
    except OperationalError:
        db.session.rollback()
        return list(FALLBACK_DEPARTMENTS)
    names = sorted({row[0] for row in rows if row[0]})
    return names or list(FALLBACK_DEPARTMENTS)


def parse_areas(raw: str) -> list[str]:
    """Comma-separated tag input to a deduped area list (order kept)."""
    seen: list[str] = []
    for part in (raw or "").split(","):
        area = " ".join(part.split())
        if area and area not in seen:
            seen.append(area)
    return seen


def validate_professor_form(form: dict[str, Any]) -> list[str]:
    """Check professor editor input; errors empty means valid."""
    errors = []
    if not str(form.get("first_name", "")).strip():
        errors.append("first name is required")
    if not str(form.get("last_name", "")).strip():
        errors.append("last name is required")
    if str(form.get("title", "")) not in TITLES:
        errors.append("title must be one of: " + ", ".join(TITLES))
    if str(form.get("rank", "")) not in RANKS:
        errors.append("rank must be one of: " + ", ".join(RANKS))
    if str(form.get("department", "")) not in department_choices():
        errors.append("department must come from the list")
    areas = parse_areas(str(form.get("research_areas", "")))
    if not areas:
        errors.append("add at least one research area")
    if len(areas) > MAX_AREAS:
        errors.append(f"at most {MAX_AREAS} research areas")
    if len(str(form.get("bio", ""))) > MAX_BIO_CHARS:
        errors.append(f"bio must be {MAX_BIO_CHARS} characters or fewer")
    try:
        rate = float(str(form.get("rate", "") or ""))
        if rate < 0:
            errors.append("rate cannot be negative")
    except ValueError:
        errors.append("rate must be a number of naira")
    try:
        ZoneInfo(str(form.get("timezone", "") or ""))
    except (ZoneInfoNotFoundError, ValueError):
        errors.append("timezone must be a valid IANA name (e.g. Africa/Lagos)")
    days = [day for day in form.get("days", []) if day in WEEKDAYS]
    windows = [
        (str(opens), str(closes))
        for opens, closes in form.get("windows", [])
        if opens or closes
    ]
    errors.extend(validate_availability(days, windows))
    return errors


def apply_professor_form(
    user: User, profile: ProfessorProfile, form: dict[str, Any]
) -> None:
    """Persist validated professor input (caller commits)."""
    first_name = str(form.get("first_name", "")).strip()
    last_name = str(form.get("last_name", "")).strip()
    title = str(form.get("title", ""))
    profile.first_name = first_name
    profile.last_name = last_name
    profile.title = title
    profile.rank = str(form.get("rank", ""))
    profile.department = str(form.get("department", ""))
    profile.research_areas = parse_areas(str(form.get("research_areas", "")))
    profile.bio = str(form.get("bio", ""))
    profile.rate = float(str(form.get("rate", "") or 0))
    profile.timezone = str(form.get("timezone", ""))
    profile.availability = {
        "days": sorted(
            {day for day in form.get("days", []) if day in WEEKDAYS},
            key=WEEKDAYS.index,
        ),
        "windows": [
            [opens, closes]
            for opens, closes in form.get("windows", [])
            if opens and closes
        ],
    }
    profile.accepting_new = bool(form.get("accepting_new"))
    user.display_name = f"{title} {first_name} {last_name}".strip()


def validate_student_form(form: dict[str, Any]) -> list[str]:
    """Check student editor input; errors empty means valid."""
    errors = []
    if not str(form.get("display_name", "")).strip():
        errors.append("name is required")
    if not str(form.get("level", "")).strip():
        errors.append("level is required")
    if not str(form.get("field", "")).strip():
        errors.append("field is required")
    return errors


def apply_student_form(
    user: User, profile: StudentProfile, form: dict[str, Any]
) -> None:
    """Persist validated student input (caller commits)."""
    user.display_name = str(form.get("display_name", "")).strip()
    profile.level = str(form.get("level", "")).strip()
    profile.field = str(form.get("field", "")).strip()
