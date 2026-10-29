"""Idempotent development seed: 20 synthetic professors, 3 students.

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

# Importable spec: (department, research areas, specialty blurb). Order is the
# deterministic seed order, so a fresh database assigns professor ids 1..20;
# scripts/make_matching_cases.py derives eval expectations from this table.
PROFESSOR_SPECS: tuple[tuple[str, list[str], str], ...] = (
    ("Statistics", ["Bayesian inference", "Clinical trials"],
     "Advises on Bayesian methods and clinical trial design."),
    ("Statistics", ["Survey sampling", "Official statistics"],
     "Advises on survey design and official statistics."),
    ("Statistics", ["Time series", "Forecasting"],
     "Advises on time series modelling and forecasting."),
    ("Statistics", ["Experimental design", "Causal inference"],
     "Advises on experiments and causal inference."),
    ("Statistics", ["Multivariate analysis", "Psychometrics"],
     "Advises on multivariate methods and psychometrics."),
    ("Computer Science", ["Machine learning", "Natural language processing"],
     "Advises on machine learning and language models."),
    ("Computer Science", ["Databases", "Data engineering"],
     "Advises on databases and data pipelines."),
    ("Computer Science", ["Algorithms", "Optimization"],
     "Advises on algorithms and optimization."),
    ("Computer Science", ["Software engineering", "Programming languages"],
     "Advises on software design and programming languages."),
    ("Computer Science", ["Computer vision", "Image analysis"],
     "Advises on computer vision and image analysis."),
    ("Economics", ["Development economics", "Poverty measurement"],
     "Advises on development and poverty measurement."),
    ("Economics", ["Econometrics", "Policy evaluation"],
     "Advises on econometrics and policy evaluation."),
    ("Economics", ["Labour markets", "Education economics"],
     "Advises on labour markets and education economics."),
    ("Economics", ["Monetary economics", "Financial markets"],
     "Advises on monetary economics and financial markets."),
    ("Economics", ["Behavioral economics", "Experimental economics"],
     "Advises on behavioral and experimental economics."),
    ("English Literature", ["African literature", "Postcolonial theory"],
     "Advises on African literature and postcolonial theory."),
    ("English Literature", ["Academic writing", "Rhetoric"],
     "Advises on academic writing and rhetoric."),
    ("English Literature", ["Literary theory", "Narratology"],
     "Advises on literary theory and narrative analysis."),
    ("English Literature", ["Stylistics", "Discourse analysis"],
     "Advises on stylistics and discourse analysis."),
    ("English Literature", ["Comparative literature", "Translation studies"],
     "Advises on comparative literature and translation."),
)

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
    for i, (dept, areas, blurb) in enumerate(PROFESSOR_SPECS, 1):
        user, _ = _get_or_create_user(
            f"sample-professor-{i:02d}@example.com",
            display_name=f"Sample Professor {i:02d}",
            role="professor",
            is_sample=True,
        )
        if user.password_hash is None:
            user.set_password(password)
        profile_fields = {
            "department": dept,
            "research_areas": list(areas),
            "bio": f"{SAMPLE_BIO} {blurb}",
            "rate": 10000.0 + i * 1000.0,
            "timezone": "Africa/Lagos",
            "availability": {
                "days": ["Monday", "Wednesday", "Friday"][0 : (i % 3) + 1],
                "hours": "10:00-14:00 WAT",
            },
        }
        if user.professor_profile is None:
            db.session.add(ProfessorProfile(user_id=user.id, **profile_fields))
        elif user.is_sample:
            # Seed owns sample rows: refresh stale specs, still convergent.
            for key, value in profile_fields.items():
                setattr(user.professor_profile, key, value)

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
