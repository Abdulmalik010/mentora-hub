"""Shared pytest fixtures."""
from __future__ import annotations

import pytest

from app import create_app
from app.extensions import db


@pytest.fixture(autouse=True)
def _seed_demo_password(monkeypatch):  # type: ignore[no-untyped-def]
    """Provide the seed password every test needs (sample-only value)."""
    monkeypatch.setenv("SEED_DEMO_PASSWORD", "test-seed-password-123")


@pytest.fixture
def app(tmp_path):  # type: ignore[no-untyped-def]
    """App with a throwaway file database (SQLite ``:memory:`` is per-connection)."""
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-only-not-a-real-secret",
            "WTF_CSRF_ENABLED": False,  # CSRF has its own dedicated test
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path}/test.db",
        }
    )
    ctx = app.app_context()
    ctx.push()
    db.create_all()
    yield app
    db.session.remove()
    db.drop_all()
    ctx.pop()
