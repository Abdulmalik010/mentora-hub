"""Student workspace: dashboard, intake, case detail, booking, sessions."""
from __future__ import annotations

import secrets
import threading
import uuid
from datetime import datetime, timezone
from typing import Any

from flask import (
    Blueprint, Response, abort, current_app, flash, jsonify, redirect,
    render_template, request, url_for,
)
from flask import Flask

from ..extensions import db
from ..models import (
    Booking, CaseFile, Document, MatchResult, ProfessorProfile, RunEvent,
    User,
)
from ..security import current_user, login_required, role_required
from ..services.booking import (
    ACTIVE_STATUSES,
    DuplicateCheckoutError,
    SlotTakenError,
    create_booking,
)
from ..services.booking_workflow import (
    BookingAuthError,
    InvalidTransitionError,
    apply_transition,
    expire_stale_bookings,
)
from ..services.diagnosis import run_case_pipeline
from ..services.email_service import case_file_context, send_booking_emails
from ..services.extraction import ExtractionError, save_upload, validate_upload
from ..services.matching import get_case_matches
from ..services.slots import Slot, generate_slots, slot_from_key

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
@login_required
def dashboard() -> str:
    """Role home: the student's cases, or the professor's bookings."""
    user = current_user()
    assert user is not None  # guaranteed by login_required
    if user.role == "professor":
        return _professor_dashboard(user)
    if user.role != "student":
        abort(403)
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


def _professor_dashboard(user: User) -> str:
    """Upcoming active bookings for one professor, soonest first."""
    _expire_stale()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    bookings = (
        Booking.query.filter(
            Booking.professor_id == user.id,
            Booking.status.in_(ACTIVE_STATUSES),
            Booking.scheduled_at.is_not(None),
            Booking.scheduled_at >= now,
        )
        .order_by(Booking.scheduled_at.asc())
        .all()
    )
    rows = [
        {
            "booking": booking,
            "student": db.session.get(User, booking.student_id),
        }
        for booking in bookings
    ]
    return render_template("cases/prof_dashboard.html", rows=rows)


@bp.get("/dashboard/bookings/<int:booking_id>")
@role_required("professor")
def professor_case_file(booking_id: int) -> str:
    """Read-only case file: the same content the email carried.

    Restricted to the booked professor, and only when the student
    consented to share the diagnosis; anything else is a 404.
    """
    _expire_stale()
    booking = db.session.get(Booking, booking_id)
    user = current_user()
    if (
        booking is None
        or user is None
        or booking.professor_id != user.id
        or not booking.consent_share_diagnosis
    ):
        abort(404)
    case = db.session.get(CaseFile, booking.case_id) if booking.case_id else None
    if case is None:
        abort(404)
    student = db.session.get(User, booking.student_id)
    profile = ProfessorProfile.query.filter_by(user_id=user.id).first()
    proposal_slots = (
        _open_slots(user.id, profile) if profile is not None else []
    )
    return render_template(
        "cases/case_file.html",
        booking=booking,
        case=case,
        student=student,
        file=case_file_context(case),
        proposal_slots=proposal_slots,
    )


@bp.post("/dashboard/bookings/<int:booking_id>/accept")
@role_required("professor")
def professor_accept(booking_id: int) -> Response:
    """Accept the request: capture the demo hold, reveal the link."""
    _expire_stale()
    booking = _own_professor_booking_or_404(booking_id)
    user = current_user()
    assert user is not None  # guaranteed by role_required
    try:
        apply_transition(booking.id, "accept", actor_user=user)
    except BookingAuthError:
        abort(403)
    except (InvalidTransitionError, SlotTakenError) as exc:
        flash(str(exc), "error")
    else:
        flash(
            "Session accepted. The meeting link is now visible to both.",
            "success",
        )
    return redirect(
        url_for("cases.professor_case_file", booking_id=booking.id), code=303
    )


@bp.post("/dashboard/bookings/<int:booking_id>/decline")
@role_required("professor")
def professor_decline(booking_id: int) -> Response:
    """Decline with a reason: release the hold, free the slot."""
    _expire_stale()
    booking = _own_professor_booking_or_404(booking_id)
    user = current_user()
    assert user is not None  # guaranteed by role_required
    try:
        apply_transition(
            booking.id, "decline", actor_user=user,
            reason=request.form.get("reason", ""),
        )
    except BookingAuthError:
        abort(403)
    except (InvalidTransitionError, SlotTakenError) as exc:
        flash(str(exc), "error")
    else:
        flash("Request declined.", "success")
    return redirect(
        url_for("cases.professor_case_file", booking_id=booking.id), code=303
    )


@bp.post("/dashboard/bookings/<int:booking_id>/propose")
@role_required("professor")
def professor_propose(booking_id: int) -> Response:
    """Offer one alternative open slot for the student to answer."""
    _expire_stale()
    booking = _own_professor_booking_or_404(booking_id)
    user = current_user()
    assert user is not None  # guaranteed by role_required
    profile = ProfessorProfile.query.filter_by(user_id=user.id).first()
    choices = (
        {slot.key: slot for slot in _open_slots(user.id, profile)}
        if profile is not None
        else {}
    )
    slot = slot_from_key(request.form.get("new_slot", ""))
    if slot is None or slot.key not in choices:
        flash("Pick a valid open slot.", "error")
        return redirect(
            url_for("cases.professor_case_file", booking_id=booking.id),
            code=303,
        )
    try:
        apply_transition(
            booking.id, "propose", actor_user=user,
            new_start=slot.start_naive_utc,
        )
    except BookingAuthError:
        abort(403)
    except (InvalidTransitionError, SlotTakenError) as exc:
        flash(str(exc), "error")
    else:
        flash("Alternative proposed.", "success")
    return redirect(
        url_for("cases.professor_case_file", booking_id=booking.id), code=303
    )


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


def _matched_professor_or_404(
    case: CaseFile, professor_id: int
) -> tuple[User, ProfessorProfile, MatchResult]:
    """Match row plus professor/profile; 404 unless this case matched them."""
    match = MatchResult.query.filter_by(
        case_id=case.id, professor_id=professor_id
    ).first()
    professor = db.session.get(User, professor_id)
    profile = ProfessorProfile.query.filter_by(user_id=professor_id).first()
    if (
        match is None
        or professor is None
        or profile is None
        or professor.role != "professor"
    ):
        abort(404)
    return professor, profile, match


def _open_slots(professor_id: int, profile: ProfessorProfile) -> list[Slot]:
    """Generated slots minus starts held by active bookings."""
    booked = {
        row[0]
        for row in db.session.query(Booking.scheduled_at)
        .filter(
            Booking.professor_id == professor_id,
            Booking.status.in_(ACTIVE_STATUSES),
        )
        .all()
    }
    return [
        slot
        for slot in generate_slots(profile.availability or {})
        if slot.start_naive_utc not in booked
    ]


def _expire_stale() -> None:
    """Flip expired requests before any booking read (lazy expiry)."""
    expire_stale_bookings()


def _own_student_booking_or_404(booking_id: int) -> Booking:
    """Booking owned by the current student; 404 for anything else."""
    booking = db.session.get(Booking, booking_id)
    user = current_user()
    if booking is None or user is None or booking.student_id != user.id:
        abort(404)
    return booking


def _own_professor_booking_or_404(booking_id: int) -> Booking:
    """Booking owned by the current professor; 404 for anything else."""
    booking = db.session.get(Booking, booking_id)
    user = current_user()
    if booking is None or user is None or booking.professor_id != user.id:
        abort(404)
    return booking


def _render_book_form(
    case: CaseFile,
    professor: User,
    profile: ProfessorProfile,
    match: MatchResult,
    status: int = 200,
) -> tuple[str, int]:
    """Book page with slots grouped by WAT day."""
    groups: dict[str, list[Slot]] = {}
    for slot in _open_slots(professor.id, profile):
        wat = slot.start_wat
        groups.setdefault(f"{wat.strftime('%A, %B')} {wat.day}", []).append(slot)
    ordered = [
        (day, slots)
        for day, slots in sorted(
            groups.items(), key=lambda item: item[1][0].start_utc
        )
    ]
    return (
        render_template(
            "cases/book.html",
            case=case,
            professor=professor,
            profile=profile,
            match=match,
            slot_groups=ordered,
            idempotency_token=secrets.token_urlsafe(16),
        ),
        status,
    )


@bp.get("/cases/<int:case_id>/book/<int:professor_id>")
@role_required("student")
def book_form(case_id: int, professor_id: int) -> tuple[str, int]:
    """Slot picker, session summary, consent and demo payment."""
    _expire_stale()
    case = _own_case_or_404(case_id)
    professor, profile, match = _matched_professor_or_404(case, professor_id)
    return _render_book_form(case, professor, profile, match)


@bp.post("/cases/<int:case_id>/book/<int:professor_id>")
@role_required("student")
def book_submit(case_id: int, professor_id: int) -> Response | tuple[str, int]:
    """Validate slot plus consent, then race-safe create the booking.

    The idempotency token is resolved before any slot validation so a
    retry never re-validates a slot this same checkout just took.
    """
    _expire_stale()
    user = current_user()
    assert user is not None  # guaranteed by role_required
    case = _own_case_or_404(case_id)
    professor, profile, match = _matched_professor_or_404(case, professor_id)
    token = request.form.get("idempotency_token", "").strip()
    if not token:
        flash("Checkout expired; please try again.", "error")
        return _render_book_form(case, professor, profile, match, 400)
    duplicate = Booking.query.filter_by(idempotency_key=token).first()
    if duplicate is not None:
        if (
            duplicate.student_id != user.id
            or duplicate.case_id != case.id
            or duplicate.professor_id != professor.id
        ):
            flash("Checkout token does not match this session.", "error")
            return _render_book_form(case, professor, profile, match, 400)
        return redirect(
            url_for("cases.confirmation", booking_id=duplicate.id), code=303
        )
    slot = slot_from_key(request.form.get("slot", ""))
    valid_keys = {
        open_slot.key for open_slot in _open_slots(professor.id, profile)
    }
    if slot is None or slot.key not in valid_keys:
        flash("Pick a valid open slot.", "error")
        return _render_book_form(case, professor, profile, match, 400)
    if request.form.get("consent") != "yes":
        flash("Consent to share your diagnosis is required.", "error")
        return _render_book_form(case, professor, profile, match, 400)
    try:
        booking = create_booking(
            student_id=user.id,
            professor_id=professor.id,
            case_id=case.id,
            start_naive_utc=slot.start_naive_utc,
            consent_share_diagnosis=True,
            idempotency_key=token,
        )
    except DuplicateCheckoutError as exc:
        return redirect(
            url_for("cases.confirmation", booking_id=exc.booking.id), code=303
        )
    except SlotTakenError as exc:
        flash(str(exc), "error")
        return _render_book_form(case, professor, profile, match, 409)
    flash("Session requested.", "success")
    try:
        send_booking_emails(booking.id)
    except Exception:  # noqa: BLE001 — email must never break the booking
        current_app.logger.exception("booking emails failed")
        flash("Booked, but the notification emails could not be sent.", "error")
    return redirect(
        url_for("cases.confirmation", booking_id=booking.id), code=303
    )


@bp.get("/sessions")
@role_required("student")
def sessions_list() -> str:
    """Student's bookings, soonest first."""
    _expire_stale()
    user = current_user()
    assert user is not None  # guaranteed by role_required
    bookings = (
        Booking.query.filter_by(student_id=user.id)
        .order_by(Booking.scheduled_at.asc())
        .all()
    )
    rows = [
        {
            "booking": booking,
            "professor": db.session.get(User, booking.professor_id),
        }
        for booking in bookings
    ]
    return render_template("sessions/list.html", rows=rows)


@bp.get("/sessions/<int:booking_id>/confirmation")
@role_required("student")
def confirmation(booking_id: int) -> str:
    """Post-checkout receipt; the 303 target, safe to refresh and share."""
    _expire_stale()
    booking = _own_student_booking_or_404(booking_id)
    professor = db.session.get(User, booking.professor_id)
    return render_template(
        "cases/confirmation.html", booking=booking, professor=professor
    )


@bp.get("/sessions/<int:booking_id>")
@role_required("student")
def session_detail(booking_id: int) -> str:
    """One booking: status, slot, gated link, case, consent, demo receipt."""
    _expire_stale()
    booking = _own_student_booking_or_404(booking_id)
    professor = db.session.get(User, booking.professor_id)
    case = db.session.get(CaseFile, booking.case_id) if booking.case_id else None
    return render_template(
        "sessions/detail.html",
        booking=booking,
        professor=professor,
        case=case,
    )


@bp.post("/sessions/<int:booking_id>/cancel")
@role_required("student")
def student_cancel(booking_id: int) -> Response:
    """Withdraw a pending request; the demo hold is released."""
    _expire_stale()
    booking = _own_student_booking_or_404(booking_id)
    user = current_user()
    assert user is not None  # guaranteed by role_required
    try:
        apply_transition(booking.id, "cancel", actor_user=user)
    except BookingAuthError:
        abort(403)
    except (InvalidTransitionError, SlotTakenError) as exc:
        flash(str(exc), "error")
    else:
        flash("Request cancelled. The demo hold was released.", "success")
    return redirect(
        url_for("cases.session_detail", booking_id=booking.id), code=303
    )


@bp.post("/sessions/<int:booking_id>/proposal/accept")
@role_required("student")
def student_accept_proposal(booking_id: int) -> Response:
    """Take the professor's alternative slot; the session is accepted."""
    _expire_stale()
    booking = _own_student_booking_or_404(booking_id)
    user = current_user()
    assert user is not None  # guaranteed by role_required
    try:
        apply_transition(booking.id, "accept_proposal", actor_user=user)
    except BookingAuthError:
        abort(403)
    except (InvalidTransitionError, SlotTakenError) as exc:
        flash(str(exc), "error")
    else:
        flash("New time accepted. The meeting link is on this page.", "success")
    return redirect(
        url_for("cases.session_detail", booking_id=booking.id), code=303
    )


@bp.post("/sessions/<int:booking_id>/proposal/decline")
@role_required("student")
def student_decline_proposal(booking_id: int) -> Response:
    """Turn down the alternative; the request is cancelled and released."""
    _expire_stale()
    booking = _own_student_booking_or_404(booking_id)
    user = current_user()
    assert user is not None  # guaranteed by role_required
    try:
        apply_transition(booking.id, "decline_proposal", actor_user=user)
    except BookingAuthError:
        abort(403)
    except (InvalidTransitionError, SlotTakenError) as exc:
        flash(str(exc), "error")
    else:
        flash("Proposal declined. The demo hold was released.", "success")
    return redirect(
        url_for("cases.session_detail", booking_id=booking.id), code=303
    )
