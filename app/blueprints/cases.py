"""Student cases: dashboard, intake form, case detail, event stream."""
from __future__ import annotations

import threading
import uuid
from datetime import datetime
from typing import Any

from flask import (
    Blueprint, Response, abort, current_app, flash, jsonify, redirect,
    render_template, request, url_for,
)
from flask import Flask

from ..extensions import db
from ..models import CaseFile, Document, ProfessorProfile, RunEvent, User
from ..security import current_user, role_required
from ..services.diagnosis import run_case_pipeline
from ..services.extraction import ExtractionError, save_upload, validate_upload
from ..services.matching import get_case_matches

bp = Blueprint("cases", __name__)

MIN_PROBLEM_CHARS = 20


def _own_case_or_404(case_id: int) -> CaseFile:
    """Case owned by the current student; 404 for anything else."""
    case = db.session.get(CaseFile, case_id)
    user = current_user()
    if case is None or user is None or case.student_id != user.id:
        abort(404)
    return case


@bp.get("/dashboard")
@role_required("student")
def dashboard() -> str:
    """Student's cases plus the new-request action."""
    user = current_user()
    assert user is not None  # guaranteed by role_required
    cases = (
        CaseFile.query.filter_by(student_id=user.id)
        .order_by(CaseFile.created_at.desc())
        .all()
    )
    open_count = CaseFile.query.filter(
        CaseFile.student_id == user.id,
        CaseFile.status.in_(["pending", "running"]),
    ).count()
    done_count = CaseFile.query.filter_by(
        student_id=user.id, status="done"
    ).count()
    hour = datetime.now().hour
    greeting = (
        "Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening"
    )
    return render_template(
        "cases/dashboard.html",
        cases=cases,
        greeting=greeting,
        open_count=open_count,
        done_count=done_count,
    )


@bp.get("/cases/new")
@role_required("student")
def new_form() -> str:
    """Render the new-request form."""
    return render_template("cases/new.html")


def _launch_pipeline(app: Flask, case_id: int, run_id: str) -> None:
    """Start intake in a daemon thread (monkeypatched in tests)."""
    thread = threading.Thread(
        target=run_case_pipeline, args=(app, case_id, run_id), daemon=True
    )
    thread.start()


@bp.post("/cases/new")
@role_required("student")
def create_case() -> Response | tuple[str, int]:
    """Validate intake, store the upload, launch the pipeline, redirect."""
    user = current_user()
    assert user is not None  # guaranteed by role_required
    problem_text = request.form.get("problem_text", "").strip()
    if len(problem_text) < MIN_PROBLEM_CHARS:
        flash(f"Describe your problem in at least {MIN_PROBLEM_CHARS} characters.", "error")
        return render_template("cases/new.html"), 400

    document: Document | None = None
    upload = request.files.get("document")
    if upload is not None and upload.filename:
        try:
            data = upload.read()
            ext = validate_upload(upload.filename, data)
            stored = save_upload(data, ext, current_app.config["UPLOAD_FOLDER"])
        except ExtractionError as exc:
            flash(str(exc), "error")
            return render_template("cases/new.html"), 400
        document = Document(
            student_id=user.id, file_path=str(stored), extracted_text=""
        )
        db.session.add(document)
        db.session.flush()

    run_id = uuid.uuid4().hex
    case = CaseFile(
        student_id=user.id,
        document_id=document.id if document else None,
        problem_text=problem_text,
        status="running",
        run_id=run_id,
    )
    db.session.add(case)
    db.session.commit()
    _launch_pipeline(current_app._get_current_object(), case.id, run_id)
    return redirect(url_for("cases.detail", case_id=case.id))


@bp.get("/cases/<int:case_id>")
@role_required("student")
def detail(case_id: int) -> str:
    """Two-column case page: diagnosis left, agent timeline right."""
    case = _own_case_or_404(case_id)
    events = []
    if case.run_id:
        events = (
            RunEvent.query.filter_by(run_id=case.run_id)
            .order_by(RunEvent.seq)
            .all()
        )
    match_cards = []
    for match in get_case_matches(case.id):
        professor = db.session.get(User, match.professor_id)
        profile = ProfessorProfile.query.filter_by(
            user_id=match.professor_id
        ).first()
        if professor is not None and profile is not None:
            match_cards.append(
                {"match": match, "professor": professor, "profile": profile}
            )
    return render_template(
        "cases/detail.html", case=case, events=events, match_cards=match_cards
    )


@bp.get("/cases/<int:case_id>/events")
@role_required("student")
def events(case_id: int) -> Response:
    """Pollable event stream for one case (JSON, `?after=seq`)."""
    case = _own_case_or_404(case_id)
    after = request.args.get("after", 0, type=int)
    rows: list[RunEvent] = []
    if case.run_id:
        rows = (
            RunEvent.query.filter_by(run_id=case.run_id)
            .filter(RunEvent.seq > after)
            .order_by(RunEvent.seq)
            .all()
        )
    payload: dict[str, Any] = {
        "status": case.status,
        "events": [
            {
                "seq": event.seq,
                "type": event.type,
                "label": event.label,
                "status": event.status,
                "payload": event.payload,
                "created_at": event.created_at.isoformat(),
            }
            for event in rows
        ],
    }
    return jsonify(payload)


@bp.app_errorhandler(413)
def too_large(error: Any) -> Response:
    """Oversized bodies bounce back to the intake form with an explanation."""
    flash("Upload too large: the limit is 10 MB per file.", "error")
    return redirect(url_for("cases.new_form"))
