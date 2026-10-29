"""Flask application factory."""
from __future__ import annotations

from typing import Any

from flask import Flask, render_template

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

    @app.template_filter("ngn")
    def format_ngn(value: object) -> str:
        """Format a naira amount with thousands separators (``₦12,500``)."""
        try:
            amount = float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return "₦—"
        return f"₦{amount:,.0f}"

    @app.get("/")
    def index() -> str:
        """Home page (factory-level route; no extra blueprint for one page)."""
        return render_template("index.html")

    @app.errorhandler(403)
    def forbidden(error: object) -> tuple[str, int]:
        """Styled 403 page."""
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(error: object) -> tuple[str, int]:
        """Styled 404 page."""
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(error: object) -> tuple[str, int]:
        """Styled 500 page."""
        return render_template("errors/500.html"), 500

    return app
