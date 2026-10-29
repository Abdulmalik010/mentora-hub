"""Flask application factory."""
from __future__ import annotations

from typing import Any

from flask import Flask

from .config import Config
from .extensions import csrf, db


def create_app(config_override: dict[str, Any] | None = None) -> Flask:
    """Create and configure the Mentora Flask application."""
    app = Flask(__name__)
    app.config.from_object(Config)
    if config_override:
        app.config.update(config_override)
    if not app.config.get("TESTING") and not app.config.get("SECRET_KEY"):
        raise RuntimeError("SECRET_KEY must be set in the environment (see .env.example)")

    db.init_app(app)
    csrf.init_app(app)

    from .blueprints.agent import bp as agent_bp
    from .blueprints.auth import bp as auth_bp
    from .blueprints.bookings import bp as bookings_bp
    from .blueprints.cases import bp as cases_bp
    from .blueprints.professors import bp as professors_bp

    app.register_blueprint(cases_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(professors_bp, url_prefix="/professors")
    app.register_blueprint(bookings_bp, url_prefix="/bookings")
    app.register_blueprint(agent_bp, url_prefix="/agent")

    @app.get("/health")
    def health() -> dict[str, str]:
        """App-level liveness probe (blueprints expose their own too)."""
        return {"status": "ok", "app": "mentora"}

    @app.context_processor
    def inject_user() -> dict[str, object]:
        """Expose the session user to every template as ``current_user``."""
        from .security import current_user

        return {"current_user": current_user()}

    @app.get("/")
    def index() -> str:
        """Home page (factory-level route; no extra blueprint for one page)."""
        from flask import render_template

        return render_template("index.html")

    return app
