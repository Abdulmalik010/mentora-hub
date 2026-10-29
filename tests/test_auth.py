"""Auth tests: register, login, logout, guards. No network, no API key."""
from __future__ import annotations

from flask import Flask
from flask.testing import FlaskClient

from app.models import ProfessorProfile, StudentProfile, User
from app.security import login_required, role_required
from scripts.seed import seed_database

STUDENT = {
    "display_name": "Test Student",
    "email": "student@example.com",
    "password": "password123",
    "role": "student",
    "level": "masters",
    "field": "Statistics",
}
PROFESSOR = {
    "display_name": "Test Professor",
    "email": "prof@example.com",
    "password": "password123",
    "role": "professor",
    "department": "Economics",
}


def register(client: FlaskClient, data: dict[str, str]):  # type: ignore[type-arg]
    """POST the registration form."""
    return client.post("/auth/register", data=data)


def login(client: FlaskClient, email: str, password: str):  # type: ignore[type-arg]
    """POST the login form."""
    return client.post("/auth/login", data={"email": email, "password": password})


def session_user_id(client: FlaskClient) -> object:  # type: ignore[type-arg]
    """User id stored in the test client's session, if any."""
    with client.session_transaction() as session:
        return session.get("user_id")


def test_register_login_logout_roundtrip(app: Flask) -> None:
    """Register logs in, index shows the name, logout clears the session."""
    client = app.test_client()
    response = register(client, STUDENT)
    assert response.status_code == 302
    assert session_user_id(client) is not None
    assert b"Test Student" in client.get("/").data
    assert client.post("/auth/logout").status_code == 302
    assert session_user_id(client) is None
    assert b"Test Student" not in client.get("/").data


def test_register_creates_matching_profile(app: Flask) -> None:
    """Role-specific fields land on the right profile row."""
    client = app.test_client()
    assert register(client, STUDENT).status_code == 302
    student = User.query.filter_by(email="student@example.com").one()
    assert student.role == "student" and not student.is_sample
    assert student.check_password("password123")
    profile = StudentProfile.query.filter_by(user_id=student.id).one()
    assert (profile.level, profile.field) == ("masters", "Statistics")

    client.post("/auth/logout")
    assert register(client, PROFESSOR).status_code == 302
    prof = User.query.filter_by(email="prof@example.com").one()
    assert prof.role == "professor"
    assert (
        ProfessorProfile.query.filter_by(user_id=prof.id).one().department
        == "Economics"
    )


def test_wrong_password_rejected(app: Flask) -> None:
    """Correct email plus wrong password yields a generic 401."""
    client = app.test_client()
    register(client, STUDENT)
    client.post("/auth/logout")
    response = login(client, "student@example.com", "wrongpassword")
    assert response.status_code == 401
    assert b"Invalid email or password." in response.data
    assert session_user_id(client) is None


def test_unknown_email_rejected_without_enumeration(app: Flask) -> None:
    """Unknown emails get the identical generic error as wrong passwords."""
    client = app.test_client()
    response = login(client, "nobody@example.com", "password123")
    assert response.status_code == 401
    assert b"Invalid email or password." in response.data


def test_duplicate_email_rejected(app: Flask) -> None:
    """Second registration with the same email fails with 400."""
    client = app.test_client()
    assert register(client, STUDENT).status_code == 302
    client.post("/auth/logout")
    response = register(client, STUDENT)
    assert response.status_code == 400
    assert b"already registered" in response.data


def test_invalid_role_and_short_password_rejected(app: Flask) -> None:
    """Bad roles and short passwords fail validation with 400."""
    client = app.test_client()
    bad_role = dict(STUDENT, email="a@example.com", role="admin")
    assert register(client, bad_role).status_code == 400
    short_pw = dict(STUDENT, email="b@example.com", password="short")
    response = register(client, short_pw)
    assert response.status_code == 400
    assert b"at least 8 characters" in response.data


def test_seeded_user_can_login(app: Flask) -> None:
    """Seed accounts authenticate with the SEED_DEMO_PASSWORD value."""
    import os

    seed_database()
    client = app.test_client()
    response = login(
        client, "sample-student-01@example.com", os.environ["SEED_DEMO_PASSWORD"]
    )
    assert response.status_code == 302
    assert session_user_id(client) is not None


def test_null_hash_user_cannot_login(app: Flask) -> None:
    """Rows without a stored hash can never authenticate at the app layer."""
    from app.extensions import db

    user = User(display_name="No Hash", email="nohash@example.com", role="student")
    db.session.add(user)
    db.session.commit()
    client = app.test_client()
    response = login(client, "nohash@example.com", "anything")
    assert response.status_code == 401
    assert session_user_id(client) is None


def test_post_without_csrf_token_rejected(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """With CSRF enabled, tokenless POSTs fail even with valid credentials."""
    from app import create_app

    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-only-not-a-real-secret",
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path}/csrf.db",
        }
    )
    ctx = app.app_context()
    ctx.push()
    try:
        from app.extensions import db

        db.create_all()
        seed_database()
        client = app.test_client()
        response = client.post(
            "/auth/login",
            data={"email": "sample-student-01@example.com", "password": "x"},
        )
        assert response.status_code == 400
        assert client.post("/auth/logout").status_code == 400
    finally:
        db.session.remove()
        db.drop_all()
        ctx.pop()


def test_login_required_and_role_required_guards(app: Flask) -> None:
    """Anonymous users redirect; wrong roles get 403; right roles pass."""
    app.add_url_rule(
        "/_guarded", endpoint="_guarded", view_func=login_required(lambda: "guarded-ok")
    )
    app.add_url_rule(
        "/_prof-only",
        endpoint="_prof-only",
        view_func=role_required("professor")(lambda: "prof-ok"),
    )
    client = app.test_client()

    anonymous = client.get("/_prof-only", follow_redirects=False)
    assert anonymous.status_code == 302
    assert "/auth/login" in anonymous.headers["Location"]

    register(client, STUDENT)
    assert client.get("/_guarded").status_code == 200
    assert client.get("/_prof-only").status_code == 403

    client.post("/auth/logout")
    register(client, PROFESSOR)
    assert client.get("/_prof-only").status_code == 200
