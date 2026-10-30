"""Shared pytest fixtures."""
from __future__ import annotations

import pytest

from app import create_app
from app.extensions import db


@pytest.fixture(autouse=True)
def _seed_demo_password(monkeypatch):  # type: ignore[no-untyped-def]
    """Provide the seed password every test needs (sample-only value)."""
    monkeypatch.setenv("SEED_DEMO_PASSWORD", "test-seed-password-123")


@pytest.fixture(autouse=True)
def _email_outbox(monkeypatch, tmp_path):  # type: ignore[no-untyped-def]
    """Tests never touch Resend: outbox provider into a throwaway dir."""
    monkeypatch.setenv("EMAIL_PROVIDER", "outbox")
    monkeypatch.setenv("EMAIL_OUTBOX_DIR", str(tmp_path / "outbox"))
    monkeypatch.delenv("DEMO_RECIPIENT_OVERRIDE", raising=False)
    monkeypatch.delenv("RESEND_API_KEY", raising=False)


@pytest.fixture(autouse=True)
def _fast_password_hash(monkeypatch):  # type: ignore[no-untyped-def]
    """Stub scrypt in tests: suite-wide seeding would otherwise take minutes.

    Login semantics are preserved (right password passes, wrong fails, NULL
    and empty stay blocked, empty set_password still raises); only the KDF
    cost is removed. Production hashing is unchanged.
    """
    monkeypatch.setattr(
        "app.models.generate_password_hash", lambda p: f"testhash:{p}"
    )
    monkeypatch.setattr(
        "app.models.check_password_hash",
        lambda h, p: isinstance(h, str) and h == f"testhash:{p}",
    )


@pytest.fixture
def app(tmp_path):  # type: ignore[no-untyped-def]
    """App with a throwaway file database (SQLite ``:memory:`` is per-connection)."""
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-only-not-a-real-secret",
            "WTF_CSRF_ENABLED": False,  # CSRF has its own dedicated test
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path}/test.db",
            "UPLOAD_FOLDER": str(tmp_path / "uploads"),
        }
    )
    ctx = app.app_context()
    ctx.push()
    db.create_all()
    yield app
    db.session.remove()
    db.drop_all()
    ctx.pop()
