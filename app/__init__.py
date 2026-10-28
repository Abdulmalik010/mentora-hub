"""Flask application factory."""
from __future__ import annotations

from typing import Any

from flask import Flask

from .config import Config
from .extensions import db


def create_app(config_override: dict[str, Any] | None = None) -> Flask:
    """Create and configure the Mentora Flask application."""
    app = Flask(__name__)
    app.config.from_object(Config)
    if config_override:
        app.config.update(config_override)

    db.init_app(app)

    from .blueprints.agent import bp as agent_bp
    from .blueprints.auth import bp as auth_bp
    from .blueprints.bookings import bp as bookings_bp
    from .blueprints.professors import bp as professors_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(professors_bp, url_prefix="/professors")
    app.register_blueprint(bookings_bp, url_prefix="/bookings")
    app.register_blueprint(agent_bp, url_prefix="/agent")

    @app.get("/health")
    def health() -> dict[str, str]:
        """App-level liveness probe (blueprints expose their own too)."""
        return {"status": "ok", "app": "mentora"}

    return app
