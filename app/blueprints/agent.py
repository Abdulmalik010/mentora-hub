"""Agent blueprint (scaffold: health route only)."""
from flask import Blueprint

bp = Blueprint("agent", __name__)


@bp.get("/health")
def health() -> dict[str, str]:
    """Liveness probe for the agent blueprint."""
    return {"status": "ok", "blueprint": "agent"}
