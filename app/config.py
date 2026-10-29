"""Environment-only configuration.

Every setting reads from the environment (optionally via a local ``.env``
file); nothing secret is hardcoded. See ``.env.example``.
"""
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base Flask configuration."""

    # No default: the factory fails fast when this is missing outside TESTING.
    SECRET_KEY: str | None = os.environ.get("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI: str = os.environ.get(
        "SQLALCHEMY_DATABASE_URI", "sqlite:///mentora.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = "Lax"
    SESSION_COOKIE_SECURE: bool = os.environ.get(
        "SESSION_COOKIE_SECURE", ""
    ).lower() in ("1", "true", "yes")

    # META_API_KEY preferred; MODEL_API_KEY accepted (the name Meta docs use).
    META_API_KEY: str | None = os.environ.get("META_API_KEY") or os.environ.get(
        "MODEL_API_KEY"
    )
    META_BASE_URL: str | None = os.environ.get("META_BASE_URL")
    META_MODEL_AGENT: str | None = os.environ.get("META_MODEL_AGENT")
    META_MODEL_FAST: str | None = os.environ.get("META_MODEL_FAST")
    META_MODEL_TRANSCRIBE: str | None = os.environ.get("META_MODEL_TRANSCRIBE")

    EMAIL_PROVIDER: str | None = os.environ.get("EMAIL_PROVIDER")
    EMAIL_API_KEY: str | None = os.environ.get("EMAIL_API_KEY")
    EMAIL_FROM: str | None = os.environ.get("EMAIL_FROM")
    EMAIL_FROM_NAME: str | None = os.environ.get("EMAIL_FROM_NAME", "Mentora")
