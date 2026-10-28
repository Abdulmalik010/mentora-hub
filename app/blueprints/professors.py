"""Professors blueprint (scaffold: health route only)."""
from flask import Blueprint

bp = Blueprint("professors", __name__)


@bp.get("/health")
def health() -> dict[str, str]:
    """Liveness probe for the professors blueprint."""
    return {"status": "ok", "blueprint": "professors"}
