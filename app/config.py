"""Environment-only configuration.

Every setting reads from the environment (optionally via a local ``.env``
file); nothing secret is hardcoded. All values are stripped; empty counts
as missing. See ``.env.example``.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _get(name: str, default: str | None = None) -> str | None:
    """Read an env var, stripped; empty-after-strip counts as missing."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    stripped = raw.strip()
    return stripped if stripped else default


def _get_bool(name: str, default: bool = False) -> bool:
    """Read an env flag (1/true/yes, case-insensitive)."""
    raw = _get(name)
    if raw is None:
        return default
    return raw.lower() in ("1", "true", "yes")


class Config:
    """Base Flask configuration."""

    # No default: the factory fails fast when this is missing outside TESTING.
    SECRET_KEY: str | None = _get("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI: str = (
        _get("SQLALCHEMY_DATABASE_URI") or "sqlite:///mentora.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = "Lax"
    SESSION_COOKIE_SECURE: bool = _get_bool("SESSION_COOKIE_SECURE")

    # 10 MB file cap enforced in code; Flask-level cap adds form overhead.
    MAX_CONTENT_LENGTH: int = 10 * 1024 * 1024 + 512 * 1024
    UPLOAD_FOLDER: str = _get("UPLOAD_FOLDER") or str(_PROJECT_ROOT / "uploads")

    # META_API_KEY preferred; MODEL_API_KEY accepted (the name Meta docs use).
    META_API_KEY: str | None = _get("META_API_KEY") or _get("MODEL_API_KEY")
    META_BASE_URL: str | None = _get("META_BASE_URL")
    META_MODEL_AGENT: str | None = _get("META_MODEL_AGENT")
    META_MODEL_FAST: str | None = _get("META_MODEL_FAST")
    META_MODEL_TRANSCRIBE: str | None = _get("META_MODEL_TRANSCRIBE")
    META_EFFORT_AGENT: str | None = _get("META_EFFORT_AGENT")
    META_EFFORT_FAST: str = _get("META_EFFORT_FAST") or "low"

    EMAIL_PROVIDER: str | None = _get("EMAIL_PROVIDER")
    EMAIL_API_KEY: str | None = _get("EMAIL_API_KEY")
    EMAIL_FROM: str | None = _get("EMAIL_FROM")
    EMAIL_FROM_NAME: str = _get("EMAIL_FROM_NAME") or "Mentora"
