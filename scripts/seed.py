"""Idempotent development seed: 35 synthetic professors, 3 students.

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

# Importable spec: (department, research areas, specialty blurb). Order is the
# deterministic seed order, so a fresh database assigns professor ids 1..35;
# scripts/make_matching_cases.py derives eval expectations from this table.
# 15 departments ("about 14" per the brief: the 4 originals plus the 11 named
# additions), 2-3 professors each. Deliberately no political science or
# clinical medicine. Area strings are retrieval keys: each spec's own areas
# must not appear as substrings in any other spec's areas or blurb.
PROFESSOR_SPECS: tuple[tuple[str, list[str], str], ...] = (
    ("Statistics", ["Bayesian inference", "Clinical trials"],
     "Advises on Bayesian methods and clinical trial design."),
    ("Statistics", ["Survey sampling", "Official statistics"],
     "Advises on survey design and official statistics."),
    ("Statistics", ["Time series", "Forecasting"],
     "Advises on time series modelling and forecasting."),
    ("Computer Science", ["Machine learning", "Natural language processing"],
     "Advises on machine learning and language models."),
    ("Computer Science", ["Databases", "Data engineering"],
     "Advises on databases and data pipelines."),
    ("Computer Science", ["Algorithms", "Optimization"],
     "Advises on algorithms and optimization."),
    ("Economics", ["Development economics", "Poverty measurement"],
     "Advises on development and poverty measurement."),
    ("Economics", ["Econometrics", "Policy evaluation"],
     "Advises on econometrics and policy evaluation."),
    ("Economics", ["Labour markets", "Education economics"],
     "Advises on labour markets and education economics."),
    ("English Literature", ["African literature", "Postcolonial theory"],
     "Advises on African literature and postcolonial theory."),
    ("English Literature", ["Academic writing", "Rhetoric"],
     "Advises on academic writing and rhetoric."),
    ("Biology", ["Genetics", "Molecular biology"],
     "Advises on genetics and molecular biology."),
    ("Biology", ["Ecology", "Biodiversity conservation"],
     "Advises on ecology and biodiversity conservation."),
    ("Biology", ["Microbiology", "Plant physiology"],
     "Advises on microbiology and plant physiology."),
    ("Chemistry", ["Organic chemistry", "Chemical synthesis"],
     "Advises on organic chemistry and chemical synthesis."),
    ("Chemistry", ["Analytical chemistry", "Spectroscopy"],
     "Advises on analytical chemistry and spectroscopy."),
    ("Physics", ["Astrophysics", "Cosmology"],
     "Advises on astrophysics and cosmology."),
    ("Physics", ["Condensed matter", "Materials physics"],
     "Advises on condensed matter and materials physics."),
    ("Mathematics", ["Pure mathematics", "Number theory"],
     "Advises on pure mathematics and number theory."),
    ("Mathematics", ["Numerical analysis", "Scientific computing"],
     "Advises on numerical analysis and scientific computing."),
    ("Mathematics", ["Operations research", "Probability theory"],
     "Advises on operations research and probability theory."),
    ("Civil Engineering", ["Structural engineering", "Construction materials"],
     "Advises on structural engineering and construction materials."),
    ("Civil Engineering", ["Water resources", "Hydrology"],
     "Advises on water resources and hydrology."),
    ("Electrical Engineering", ["Power systems", "Renewable energy"],
     "Advises on power systems and renewable energy."),
    ("Electrical Engineering", ["Signal processing", "Control systems"],
     "Advises on signal processing and control systems."),
    ("Law", ["Constitutional law", "Human rights law"],
     "Advises on constitutional law and human rights law."),
    ("Law", ["Commercial law", "Contract law"],
     "Advises on commercial law and contract law."),
    ("Education", ["Curriculum studies", "Instructional design"],
     "Advises on curriculum studies and instructional design."),
    ("Education", ["Educational assessment", "Learning analytics"],
     "Advises on educational assessment and learning analytics."),
    ("Psychology", ["Cognitive psychology", "Behavioral neuroscience"],
     "Advises on cognitive psychology and behavioral neuroscience."),
    ("Psychology", ["Developmental psychology", "Educational psychology"],
     "Advises on developmental and educational psychology."),
    ("Business Administration", ["Financial management", "Corporate finance"],
     "Advises on financial management and corporate finance."),
    ("Business Administration", ["Marketing", "Consumer behavior"],
     "Advises on marketing and consumer behavior."),
    ("Agricultural Science", ["Crop science", "Soil fertility"],
     "Advises on crop science and soil fertility."),
    ("Agricultural Science", ["Agricultural economics", "Farm management"],
     "Advises on agricultural economics and farm management."),
)

STUDENT_LEVELS: tuple[str, ...] = ("undergraduate", "masters", "phd")
STUDENT_FIELDS: tuple[str, ...] = ("Statistics", "Computer Science", "Economics")

SAMPLE_BIO = (
    "[SAMPLE DATA] Synthetic professor profile for development and demo only; "
    "not a real person."
)

# Fictional identities aligned with PROFESSOR_SPECS order:
# (first name, last name, title, rank). Ordinary invented combinations; any
# resemblance to real people is coincidental. Display names carry no numbers,
# so the old NN label no longer implies anything about user ids.
PROFESSOR_NAMES: tuple[tuple[str, str, str, str], ...] = (
    ("Adaeze", "Nwosu", "Prof.", "Professor"),
    ("Tunde", "Alabi", "Dr.", "Senior Lecturer"),
    ("Yuki", "Tanaka", "Dr.", "Associate Professor"),
    ("Olumide", "Adeyemi", "Dr.", "Associate Professor"),
    ("James", "Whitfield", "Dr.", "Senior Lecturer"),
    ("Chen", "Wei", "Prof.", "Professor"),
    ("Aisha", "Bello", "Prof.", "Professor"),
    ("Chiamaka", "Obi", "Dr.", "Senior Lecturer"),
    ("Diego", "Fernandez", "Dr.", "Associate Professor"),
    ("Zanele", "Dlamini", "Dr.", "Senior Lecturer"),
    ("Maria", "Santos", "Prof.", "Professor"),
    ("Lars", "Johansson", "Dr.", "Senior Lecturer"),
    ("Funke", "Adewale", "Dr.", "Senior Lecturer"),
    ("Priya", "Sharma", "Prof.", "Professor"),
    ("Ibrahim", "Musa", "Prof.", "Professor"),
    ("Grace", "Okonkwo", "Dr.", "Lecturer I"),
    ("Rajesh", "Iyer", "Dr.", "Associate Professor"),
    ("Ingrid", "Larsen", "Dr.", "Senior Lecturer"),
    ("Sofia", "Rossi", "Dr.", "Lecturer I"),
    ("Carlos", "Mendez", "Dr.", "Senior Lecturer"),
    ("Hauwa", "Garba", "Dr.", "Senior Lecturer"),
    ("Kwame", "Mensah", "Dr.", "Senior Lecturer"),
    ("Peter", "Novak", "Prof.", "Professor"),
    ("Mei", "Lin", "Dr.", "Associate Professor"),
    ("Ngozi", "Eze", "Dr.", "Lecturer I"),
    ("Oliver", "Bennett", "Dr.", "Lecturer I"),
    ("Anna", "Kowalski", "Dr.", "Associate Professor"),
    ("Zainab", "Yusuf", "Dr.", "Senior Lecturer"),
    ("Emeka", "Diallo", "Dr.", "Lecturer I"),
    ("Samuel", "Boateng", "Dr.", "Associate Professor"),
    ("Fatima", "Hassan", "Dr.", "Senior Lecturer"),
    ("Elena", "Petrova", "Prof.", "Professor"),
    ("Jae", "Park", "Dr.", "Lecturer I"),
    ("David", "Osei", "Dr.", "Lecturer I"),
    ("Nadia", "Rahman", "Dr.", "Senior Lecturer"),
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
    """Seed 35 professors and 3 students; safe to run repeatedly.

    Must run inside an app context. Existing sample rows (matched by email)
    are refreshed to the canonical spec values, so re-runs are convergent
    no-ops once the database matches the spec.
    """
    password = _demo_password()
    for i, ((dept, areas, blurb), ident) in enumerate(
        zip(PROFESSOR_SPECS, PROFESSOR_NAMES), 1
    ):
        first_name, last_name, title, rank = ident
        display_name = f"{title} {first_name} {last_name}"
        user, _ = _get_or_create_user(
            f"sample-professor-{i:02d}@example.com",
            display_name=display_name,
            role="professor",
            is_sample=True,
        )
        if user.password_hash is None:
            user.set_password(password)
        if user.is_sample:
            user.display_name = display_name
        profile_fields = {
            "first_name": first_name,
            "last_name": last_name,
            "title": title,
            "rank": rank,
            "department": dept,
            "research_areas": list(areas),
            "bio": f"{SAMPLE_BIO} {blurb}",
            "rate": 10000.0 + i * 1000.0,
            "timezone": "Africa/Lagos",
            "availability": {
                "days": ["Monday", "Wednesday", "Friday"][0 : (i % 3) + 1],
                "windows": [["10:00", "14:00"]],
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
