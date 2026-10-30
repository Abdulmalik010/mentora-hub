"""Shared pytest fixtures."""
from __future__ import annotations

import shutil
from pathlib import Path

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
def _no_network(monkeypatch):  # type: ignore[no-untyped-def]
    """Unit tests never touch the network: sockets fail loudly.

    Regression guard: live API keys exist in the developer's .env, so any
    unfaked client would silently spend credit and slow the suite.
    """
    import socket as _socket

    def _blocked(*args: object, **kwargs: object) -> object:
        raise AssertionError("network access is forbidden in unit tests")

    monkeypatch.setattr(_socket, "socket", _blocked)


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


@pytest.fixture(scope="session")
def _session_state(tmp_path_factory):  # type: ignore[no-untyped-def]
    """One app + one database file for the session (routes/schema built once).

    Returns ``(app, db_path, template_path)``. Per-test isolation comes
    from restoring the pristine template bytes over the live file (see
    the ``app`` fixture), which Flask/SQLAlchemy permit after requests
    have been served, unlike extension re-registration.
    """
    workdir = tmp_path_factory.mktemp("session-app")
    db_path = workdir / "session.db"
    template = workdir / "template.db"
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-only-not-a-real-secret",
            "WTF_CSRF_ENABLED": False,  # CSRF has its own dedicated tests
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
        }
    )
    # Probe routes for the guard test: registered once, before any request
    # (Flask forbids add_url_rule after the first request is served).
    from app.security import login_required, role_required

    app.add_url_rule(
        "/_guarded", endpoint="_guarded", view_func=login_required(lambda: "guarded-ok")
    )
    app.add_url_rule(
        "/_prof-only",
        endpoint="_prof-only",
        view_func=role_required("professor")(lambda: "prof-ok"),
    )
    ctx = app.app_context()
    ctx.push()
    db.create_all()
    db.session.remove()
    db.engine.dispose()
    shutil.copy(db_path, template)
    ctx.pop()
    return app, db_path, template


@pytest.fixture
def app(tmp_path, _session_state):  # type: ignore[no-untyped-def]
    """Session app with a freshly restored database and upload dir.

    Route compilation and schema build happen once per session (~200ms
    saved per test); each test still starts from a pristine database
    (pooled connections disposed, WAL sidecars dropped, template bytes
    restored) and a private upload folder. Config mutations are rolled
    back so one test's overrides never leak into the next.
    """
    session_app, db_path, template = _session_state
    ctx = session_app.app_context()
    ctx.push()
    db.session.remove()
    db.engine.dispose()
    for suffix in ("-wal", "-shm"):
        sidecar = Path(f"{db_path}{suffix}")
        if sidecar.exists():
            sidecar.unlink()
    shutil.copy(template, db_path)
    saved_config = dict(session_app.config)
    session_app.config["UPLOAD_FOLDER"] = str(tmp_path / "uploads")
    yield session_app
    db.session.remove()
    ctx.pop()
    session_app.config.clear()
    session_app.config.update(saved_config)
