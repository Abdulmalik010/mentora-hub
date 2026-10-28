"""Bookings blueprint (scaffold: health route only)."""
from flask import Blueprint

bp = Blueprint("bookings", __name__)


@bp.get("/health")
def health() -> dict[str, str]:
    """Liveness probe for the bookings blueprint."""
    return {"status": "ok", "blueprint": "bookings"}
