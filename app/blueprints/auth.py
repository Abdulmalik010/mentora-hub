"""Auth blueprint (scaffold: health route only)."""
from flask import Blueprint

bp = Blueprint("auth", __name__)


@bp.get("/health")
def health() -> dict[str, str]:
    """Liveness probe for the auth blueprint."""
    return {"status": "ok", "blueprint": "auth"}
