"""Professors blueprint: public directory plus health probe."""
from flask import Blueprint, abort, render_template, request

from ..extensions import db
from ..models import ProfessorProfile, User
from ..services.matching import search_professors

bp = Blueprint("professors", __name__)

DEPARTMENTS = (
    "Statistics",
    "Computer Science",
    "Economics",
    "English Literature",
)


@bp.get("/health")
def health() -> dict[str, str]:
    """Liveness probe for the professors blueprint."""
    return {"status": "ok", "blueprint": "professors"}


@bp.get("")
def index() -> str:
    """Public directory with keyword search and department filter."""
    query = request.args.get("q", "").strip()
    department = request.args.get("department", "").strip() or None
    if department not in DEPARTMENTS:
        department = None
    keywords = [query] if query else []
    results = search_professors(keywords, department, limit=50)
    return render_template(
        "professors/index.html",
        results=results,
        query=query,
        department=department,
        departments=DEPARTMENTS,
    )


@bp.get("/<int:user_id>")
def detail(user_id: int) -> str:
    """Public profile page; 404 for unknown or non-professor ids."""
    user = db.session.get(User, user_id)
    profile = ProfessorProfile.query.filter_by(user_id=user_id).first()
    if user is None or profile is None or user.role != "professor":
        abort(404)
    return render_template(
        "professors/detail.html", professor=user, profile=profile
    )
