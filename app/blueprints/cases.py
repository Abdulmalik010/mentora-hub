"""Student workspace: dashboard, intake, case detail, booking, sessions."""
from __future__ import annotations

import json
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
    Booking, CaseFile, ClarificationQA, Document, MatchResult,
    ProfessorProfile, RunEvent, SessionRecord, User,
)
from ..security import current_user, login_required, role_required
from ..services.booking import (
    ACTIVE_STATUSES,
    DuplicateCheckoutError,
    InsufficientFundsError,
    SlotTakenError,
    create_booking,
)
from ..services.booking_workflow import (
    BookingAuthError,
    InvalidTransitionError,
    apply_transition,
    expire_stale_bookings,
)
from ..services.clarification import apply_answer_constraints, load_answers
from ..services.diagnosis import log_event, run_case_pipeline, run_post_answer_matching
from ..services.email_service import (
    case_file_context,
    send_accepted_emails,
    send_cancelled_email,
    send_declined_email,
    send_request_emails,
)
from ..services.messaging import get_threads, unread_message_count
from ..services.notifications import notify_transition
from ..services.pdf_service import build_session_notes_pdf
from ..services.sessions import (
    STEP_EVENTS,
    get_session_record,
    mapped_turns,
    new_run_id,
    recording_allowed,
    reset_record_for_upload,
    run_session_pipeline,
    save_session_audio,
    swap_speaker_map,
)
from ..services.slots import format_wat
from ..services.transcription import AudioRejected
from ..services.wallet import demo_balance
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
        demo_balance=demo_balance(user),
    )


@bp.get("/cases/new")
@role_required("student")
def new_form() -> str:
    """Render the new-request form."""
    return render_template("cases/new.html")


def _professor_dashboard(user: User) -> str:
    """Professor workspace: stats plus requests/upcoming/inbox/profile tabs."""
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
    requests, upcoming = [], []
    for booking in bookings:
        student = db.session.get(User, booking.student_id)
        case = (
            db.session.get(CaseFile, booking.case_id)
            if booking.case_id
            else None
        )
        preview = None
        if case is not None:
            context = case_file_context(case)
            preview = {
                "core_problem": context["core_problem"],
                "gaps": context["gaps"][:2],
                "question_count": len(context["questions"]),
            }
        row = {"booking": booking, "student": student, "preview": preview}
        if booking.status in ("requested", "reschedule_proposed"):
            requests.append(row)
        else:
            upcoming.append(row)
    profile = ProfessorProfile.query.filter_by(user_id=user.id).first()
    proposal_slots = _open_slots(user.id, profile) if profile else []
    tab = request.args.get("tab", "requests")
    if tab not in ("requests", "upcoming", "inbox", "profile"):
        tab = "requests"
    return render_template(
        "cases/prof_dashboard.html",
        demo_balance=demo_balance(user),
        pending_count=sum(
            1 for row in requests
            if row["booking"].status == "requested"
        ),
        upcoming_count=len(upcoming),
        unread_messages=unread_message_count(user.id),
        requests=requests,
        upcoming=upcoming,
        threads=get_threads(user.id),
        profile=profile,
        proposal_slots=proposal_slots,
        active_tab=tab,
    )


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
        try:
            notify_transition(booking.id, "accepted")
            send_accepted_emails(booking.id)
        except Exception:  # noqa: BLE001 — never undo the decision
            current_app.logger.exception("accept notifications failed")
            flash("Accepted, but notifications could not be sent.", "error")
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
        try:
            notify_transition(booking.id, "declined")
            send_declined_email(booking.id)
        except Exception:  # noqa: BLE001 — never undo the decision
            current_app.logger.exception("decline notifications failed")
            flash("Declined, but notifications could not be sent.", "error")
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
        try:
            notify_transition(booking.id, "proposal")
        except Exception:  # noqa: BLE001 — never undo the decision
            current_app.logger.exception("proposal notification failed")
            flash("Proposed, but the notification could not be sent.", "error")
    return redirect(
        url_for("cases.professor_case_file", booking_id=booking.id), code=303
    )


def _launch_pipeline(app: Flask, case_id: int, run_id: str) -> None:
    """Start intake in a daemon thread (monkeypatched in tests)."""
    thread = threading.Thread(
        target=run_case_pipeline, args=(app, case_id, run_id), daemon=True
    )
    thread.start()


def _launch_matching(app: Flask, case_id: int, run_id: str) -> None:
    """Start post-answer matching in a daemon thread (monkeypatched in tests)."""
    thread = threading.Thread(
        target=run_post_answer_matching, args=(app, case_id, run_id),
        daemon=True,
    )
    thread.start()


def _launch_session_pipeline(app: Flask, booking_id: int, run_id: str) -> None:
    """Start session transcription in a daemon thread (monkeypatched)."""
    thread = threading.Thread(
        target=run_session_pipeline, args=(app, booking_id, run_id),
        daemon=True,
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
    questions: list[ClarificationQA] = []
    if case.status == "awaiting_answers":
        questions = (
            ClarificationQA.query.filter_by(case_id=case.id)
            .order_by(ClarificationQA.id)
            .all()
        )
    snapshot = case.candidate_snapshot or {}
    return render_template(
        "cases/detail.html", case=case, events=events, match_cards=match_cards,
        questions=questions,
        filters_applied=snapshot.get("filters_applied", []) or [],
        filters_relaxed=snapshot.get("relaxed", []) or [],
    )


@bp.post("/cases/<int:case_id>/answers")
@role_required("student")
def submit_answers(case_id: int) -> Response:
    """Store clarifying answers (or skip), constrain, launch matching.

    One round only: the case must be ``awaiting_answers``. Submit applies
    the answers as retrieval constraints; skip matches the raw snapshot.
    """
    case = _own_case_or_404(case_id)
    if case.status != "awaiting_answers":
        flash("This case is not waiting for answers.", "error")
        return redirect(
            url_for("cases.detail", case_id=case.id), code=303
        )
    action = request.form.get("action", "submit")
    rows = (
        ClarificationQA.query.filter_by(case_id=case.id)
        .order_by(ClarificationQA.id)
        .all()
    )
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if action == "skip":
        if case.run_id:
            log_event(case.run_id, "answers_skipped", "Student skipped; matching now")
        flash("Skipped. Matching on the diagnosis alone.", "success")
    else:
        for row in rows:
            choice = request.form.get(f"choice_{row.id}", "").strip()
            text = request.form.get(f"text_{row.id}", "").strip()
            answer = text or choice
            if answer:
                row.answer = answer[:2000]
                row.answered_at = now
        answers = load_answers(case.id)
        _apply_constraints_to_snapshot(case, answers)
        if case.run_id:
            log_event(
                case.run_id, "answers_submitted",
                f"Student answered {len(answers)}/{len(rows)}; matching now",
                payload={"answered": len(answers), "asked": len(rows)},
            )
        flash("Answers saved. Matching now.", "success")
    case.status = "running"
    db.session.commit()
    _launch_matching(current_app, case.id, case.run_id or "")
    return redirect(url_for("cases.detail", case_id=case.id), code=303)


def _apply_constraints_to_snapshot(
    case: CaseFile, answers: dict[str, str]
) -> None:
    """Filter/boost the snapshot candidates from answers (caller commits).

    Rates ride in the snapshot, so no re-retrieval is needed at submit;
    times overlap reads live profiles (availability may have changed).
    """
    snapshot = dict(case.candidate_snapshot or {})
    candidates = [
        {
            "professor_id": item["professor_id"],
            "score": item.get("score", 0),
            "rate": item.get("rate"),
        }
        for item in snapshot.get("candidates", []) or []
        if isinstance(item, dict) and "professor_id" in item
    ]
    if not candidates:
        return
    constrained = apply_answer_constraints(candidates, answers)
    snapshot["candidates"] = [
        {
            "professor_id": hit["professor_id"],
            "score": hit["score"],
            "rate": hit.get("rate"),
        }
        for hit in constrained.candidates
    ]
    snapshot["constraint_block"] = constrained.prompt_block
    snapshot["filters_applied"] = constrained.filters_applied
    snapshot["relaxed"] = constrained.relaxed
    case.candidate_snapshot = snapshot


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
    """Oversized bodies bounce back to the sending page with an explanation."""
    flash("Upload too large for the server to accept.", "error")
    target = request.referrer or url_for("cases.new_form")
    if not target.startswith("/"):
        target = url_for("cases.new_form")
    return redirect(target)


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


def _own_party_booking_or_404(booking_id: int) -> Booking:
    """Booking where the current user is the student or the professor."""
    booking = db.session.get(Booking, booking_id)
    user = current_user()
    if (
        booking is None
        or user is None
        or user.id not in (booking.student_id, booking.professor_id)
    ):
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
    except InsufficientFundsError as exc:
        flash(str(exc), "error")
        return _render_book_form(case, professor, profile, match, 400)
    except SlotTakenError as exc:
        flash(str(exc), "error")
        return _render_book_form(case, professor, profile, match, 409)
    flash("Session requested.", "success")
    try:
        notify_transition(booking.id, "request_created")
        send_request_emails(
            booking.id,
            review_url=url_for(
                "cases.professor_case_file", booking_id=booking.id,
                _external=True,
            ),
        )
    except Exception:  # noqa: BLE001 — notify must never break the booking
        current_app.logger.exception("booking notifications failed")
        flash("Requested, but the notifications could not be sent.", "error")
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
        record=get_session_record(booking.id),
    )


@bp.get("/sessions/<int:booking_id>/room")
@login_required
def session_room(booking_id: int) -> str:
    """Session room: meeting link, recording panel, 6-step timeline.

    Visible to the booking's student and professor. The recording panel
    is gated on the slot window (DEMO_ALLOW_ANYTIME skips the check);
    the meeting link follows the accepted-only reveal rule.
    """
    booking = _own_party_booking_or_404(booking_id)
    record = get_session_record(booking.id)
    events: list[RunEvent] = []
    if record is not None and record.run_id:
        events = (
            RunEvent.query.filter_by(run_id=record.run_id)
            .order_by(RunEvent.seq)
            .all()
        )
    done_types = {event.type for event in events}
    steps = [
        {"event": name, "done": name in done_types} for name in STEP_EVENTS
    ]
    allowed, reason = recording_allowed(
        booking, demo_anytime=bool(current_app.config.get("DEMO_ALLOW_ANYTIME"))
    )
    student = db.session.get(User, booking.student_id)
    professor = db.session.get(User, booking.professor_id)
    return render_template(
        "sessions/room.html",
        booking=booking, record=record, events=events, steps=steps,
        student=student, professor=professor,
        recording_allowed=allowed, recording_reason=reason,
        turns=mapped_turns(record) if record is not None else [],
    )


@bp.get("/sessions/<int:booking_id>/room/events")
@login_required
def session_room_events(booking_id: int) -> Response:
    """Pollable room timeline (JSON, `?after=seq`)."""
    booking = _own_party_booking_or_404(booking_id)
    record = get_session_record(booking.id)
    after = request.args.get("after", 0, type=int)
    rows: list[RunEvent] = []
    if record is not None and record.run_id:
        rows = (
            RunEvent.query.filter_by(run_id=record.run_id)
            .filter(RunEvent.seq > after)
            .order_by(RunEvent.seq)
            .all()
        )
    return jsonify(
        {
            "status": record.status if record is not None else "pending",
            "events": [
                {
                    "seq": event.seq,
                    "type": event.type,
                    "label": event.label,
                    "status": event.status,
                    "created_at": event.created_at.isoformat(),
                }
                for event in rows
            ],
        }
    )


@bp.post("/sessions/<int:booking_id>/room/audio")
@login_required
def session_room_audio(booking_id: int) -> Response:
    """Accept a consented WAV upload and launch the pipeline worker."""
    booking = _own_party_booking_or_404(booking_id)
    allowed, reason = recording_allowed(
        booking, demo_anytime=bool(current_app.config.get("DEMO_ALLOW_ANYTIME"))
    )
    if not allowed:
        flash(reason, "error")
        return redirect(
            url_for("cases.session_room", booking_id=booking.id), code=303
        )
    if request.form.get("consent") != "yes":
        flash("Recording needs your explicit consent: tick the checkbox.", "error")
        return redirect(
            url_for("cases.session_room", booking_id=booking.id), code=303
        )
    upload = request.files.get("audio")
    if upload is None or not (upload.filename or "").strip():
        flash("Choose a WAV file (or record one) first.", "error")
        return redirect(
            url_for("cases.session_room", booking_id=booking.id), code=303
        )
    try:
        path = save_session_audio(
            upload.filename or "", upload.read(),
            current_app.config["UPLOAD_FOLDER"],
        )
    except AudioRejected as exc:
        flash(str(exc), "error")
        return redirect(
            url_for("cases.session_room", booking_id=booking.id), code=303
        )
    record = get_session_record(booking.id)
    if record is None:
        record = SessionRecord(booking_id=booking.id)
        db.session.add(record)
    run_id = new_run_id()
    reset_record_for_upload(record, path, run_id)
    db.session.commit()
    _launch_session_pipeline(current_app, booking.id, run_id)
    flash("Audio received; transcription started.", "success")
    return redirect(url_for("cases.session_room", booking_id=booking.id), code=303)


@bp.post("/sessions/<int:booking_id>/room/speakers/swap")
@login_required
def session_room_swap_speakers(booking_id: int) -> Response:
    """Flip the Professor/Student speaker mapping (one click)."""
    booking = _own_party_booking_or_404(booking_id)
    record = get_session_record(booking.id)
    if record is None or not record.speaker_map:
        flash("Nothing to swap yet: transcribe audio first.", "error")
        return redirect(
            url_for("cases.session_room", booking_id=booking.id), code=303
        )
    record.speaker_map = swap_speaker_map(record.speaker_map)
    db.session.commit()
    flash("Speaker roles swapped.", "success")
    if request.form.get("next") == "transcript":
        return redirect(
            url_for("cases.session_transcript", booking_id=booking.id), code=303
        )
    return redirect(url_for("cases.session_room", booking_id=booking.id), code=303)


@bp.get("/sessions/<int:booking_id>/room/transcript")
@login_required
def session_transcript(booking_id: int) -> str:
    """Transcript view with mapped speaker labels (parties only)."""
    booking = _own_party_booking_or_404(booking_id)
    record = get_session_record(booking.id)
    if record is None or not record.turns:
        abort(404)
    student = db.session.get(User, booking.student_id)
    professor = db.session.get(User, booking.professor_id)
    return render_template(
        "sessions/transcript.html",
        booking=booking, record=record, turns=mapped_turns(record),
        student=student, professor=professor,
    )


@bp.get("/sessions/<int:booking_id>/room/notes.pdf")
@login_required
def session_notes_pdf(booking_id: int) -> Response:
    """Notes PDF download, regenerated from the database on demand."""
    booking = _own_party_booking_or_404(booking_id)
    record = get_session_record(booking.id)
    if record is None or not record.notes:
        abort(404)
    student = db.session.get(User, booking.student_id)
    professor = db.session.get(User, booking.professor_id)
    pdf_bytes = build_session_notes_pdf(
        student_name=student.display_name if student else "?",
        professor_name=professor.display_name if professor else "?",
        slot_text=format_wat(booking.scheduled_at) if booking.scheduled_at else "—",
        final_notes=json.loads(record.notes),
        fidelity_rate=record.fidelity_rate,
    )
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": (
                f"attachment; filename=mentora-session-notes-{booking.id}.pdf"
            )
        },
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
        try:
            notify_transition(booking.id, "cancelled")
            send_cancelled_email(booking.id)
        except Exception:  # noqa: BLE001 — never undo the decision
            current_app.logger.exception("cancel notifications failed")
            flash("Cancelled, but notifications could not be sent.", "error")
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
        try:
            notify_transition(booking.id, "proposal_accepted")
        except Exception:  # noqa: BLE001 — never undo the decision
            current_app.logger.exception("proposal-answer notification failed")
            flash("Accepted, but the notification could not be sent.", "error")
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
        try:
            notify_transition(booking.id, "proposal_declined")
        except Exception:  # noqa: BLE001 — never undo the decision
            current_app.logger.exception("proposal-answer notification failed")
            flash("Declined, but the notification could not be sent.", "error")
    return redirect(
        url_for("cases.session_detail", booking_id=booking.id), code=303
    )
