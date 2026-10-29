"""Idempotent development seed: synthetic professors and students.

Run from the project root: ``python -m scripts.seed`` (requires the
``SEED_DEMO_PASSWORD`` env var). Creates tables when missing. Every record
is synthetic sample data (``is_sample=True``,
``@example.com`` emails, ``[SAMPLE DATA]`` bios): no real names or photos.
"""
from __future__ import annotations

import os

from app import create_app
from app.extensions import db
from app.models import ProfessorProfile, StudentProfile, User


def _demo_password() -> str:
    """Sample-only login password; seeding refuses to run without it."""
    password = os.environ.get("SEED_DEMO_PASSWORD", "")
    if not password:
        raise RuntimeError(
            "SEED_DEMO_PASSWORD must be set to seed (sample-only password; see README)"
        )
    return password

DEPARTMENTS: tuple[str, ...] = (
    "Statistics",
    "Computer Science",
    "Economics",
    "English Literature",
)

RESEARCH_AREAS: dict[str, list[str]] = {
    "Statistics": [
        "Bayesian inference",
        "Survey sampling",
        "Regression modelling",
        "Experimental design",
    ],
    "Computer Science": [
        "Machine learning",
        "Databases",
        "Algorithms",
        "Software engineering",
    ],
    "Economics": [
        "Development economics",
        "Econometrics",
        "Labour markets",
        "Public policy",
    ],
    "English Literature": [
        "African literature",
        "Academic writing",
        "Literary theory",
        "Stylistics",
    ],
}

STUDENT_LEVELS: tuple[str, ...] = ("undergraduate", "masters", "phd")
STUDENT_FIELDS: tuple[str, ...] = ("Statistics", "Computer Science", "Economics")

SAMPLE_BIO = (
    "[SAMPLE DATA] Synthetic professor profile for development and demo only; "
    "not a real person."
)


def _get_or_create_user(email: str, **fields: object) -> tuple[User, bool]:
    """Fetch a user by email or create one; True when newly created."""
    user = User.query.filter_by(email=email).first()
    if user is not None:
        return user, False
    user = User(email=email, **fields)  # type: ignore[arg-type]
    db.session.add(user)
    db.session.flush()
    return user, True


def seed_database() -> dict[str, int]:
    """Seed 12 professors and 3 students; safe to run repeatedly.

    Must run inside an app context. Existing rows (matched by email) keep
    their data; only a missing password hash is backfilled, so re-runs are
    otherwise no-ops.
    """
    password = _demo_password()
    for i in range(1, 13):
        dept = DEPARTMENTS[(i - 1) // 3]
        areas = RESEARCH_AREAS[dept]
        user, _ = _get_or_create_user(
            f"sample-professor-{i:02d}@example.com",
            display_name=f"Sample Professor {i:02d}",
            role="professor",
            is_sample=True,
        )
        if user.password_hash is None:
            user.set_password(password)
        if user.professor_profile is None:
            pick = ((i - 1) % 3, (i % 4))
            db.session.add(
                ProfessorProfile(
                    user_id=user.id,
                    department=dept,
                    research_areas=[areas[pick[0]], areas[pick[1]]],
                    bio=f"{SAMPLE_BIO} Advises on {dept.lower()} coursework and theses.",
                    rate=10000.0 + i * 2500.0,
                    timezone="Africa/Lagos",
                    availability={
                        "days": ["Monday", "Wednesday", "Friday"][0 : (i % 3) + 1],
                        "hours": "10:00-14:00 WAT",
                    },
                )
            )

    for i, (level, field) in enumerate(zip(STUDENT_LEVELS, STUDENT_FIELDS), 1):
        user, _ = _get_or_create_user(
            f"sample-student-0{i}@example.com",
            display_name=f"Sample Student 0{i}",
            role="student",
            is_sample=True,
        )
        if user.password_hash is None:
            user.set_password(password)
        if user.student_profile is None:
            db.session.add(
                StudentProfile(user_id=user.id, level=level, field=field)
            )

    db.session.commit()
    professors = User.query.filter_by(role="professor", is_sample=True).count()
    students = User.query.filter_by(role="student", is_sample=True).count()
    return {"professors": professors, "students": students}


def main() -> None:
    """Create tables if missing, seed, and print the resulting counts."""
    app = create_app()
    with app.app_context():
        db.create_all()
        counts = seed_database()
    print(
        f"Seeded (idempotent): "
        f"{counts['professors']} professors, {counts['students']} students."
    )


if __name__ == "__main__":
    main()
