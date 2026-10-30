"""Self-service profiles: professor editor, student page, setup wizard."""
from __future__ import annotations

from typing import Any

from flask import (
    Blueprint, Response, flash, redirect, render_template, request, url_for,
)

from ..extensions import db
from ..models import ProfessorProfile, StudentProfile
from ..security import current_user, login_required, role_required
from ..services.profiles import (
    RANKS,
    TITLES,
    apply_professor_form,
    apply_student_form,
    department_choices,
    validate_professor_form,
    validate_student_form,
)
from ..services.slots import WEEKDAYS

bp = Blueprint("profiles", __name__)


def _professor_form_data() -> dict[str, Any]:
    """Flatten the editor POST into the shape validation expects."""
    opens = request.form.getlist("window_opens")
    closes = request.form.getlist("window_closes")
    return {
        "first_name": request.form.get("first_name", ""),
        "last_name": request.form.get("last_name", ""),
        "title": request.form.get("title", ""),
        "rank": request.form.get("rank", ""),
        "department": request.form.get("department", ""),
        "research_areas": request.form.get("research_areas", ""),
        "bio": request.form.get("bio", ""),
        "rate": request.form.get("rate", ""),
        "timezone": request.form.get("timezone", ""),
        "days": request.form.getlist("days"),
        "windows": list(zip(opens, closes)),
        "accepting_new": request.form.get("accepting_new") == "yes",
    }


def _professor_initial(profile: ProfessorProfile) -> dict[str, Any]:
    """Current profile values in editor shape (for GET and re-render)."""
    availability = profile.availability or {}
    return {
        "first_name": profile.first_name or "",
        "last_name": profile.last_name or "",
        "title": profile.title or "",
        "rank": profile.rank or "",
        "department": profile.department or "",
        "research_areas": ", ".join(profile.research_areas or []),
        "bio": profile.bio or "",
        "rate": "" if profile.rate is None else str(int(profile.rate)),
        "timezone": profile.timezone or "",
        "days": availability.get("days", []) or [],
        "windows": [
            (str(window[0]), str(window[1]))
            for window in (availability.get("windows", []) or [])
            if len(window) == 2
        ],
        "accepting_new": profile.accepting_new is not False,
    }


def _render_professor_editor(
    data: dict[str, Any], *, setup: bool, status: int = 200
) -> tuple[str, int]:
    """Editor page with selects fed from constants and the DB list."""
    return (
        render_template(
            "profiles/edit.html",
            role="professor",
            setup=setup,
            data=data,
            titles=TITLES,
            ranks=RANKS,
            departments=department_choices(),
            weekdays=WEEKDAYS,
            post_url=url_for(
                "profiles.setup" if setup else "profiles.edit"
            ),
        ),
        status,
    )


@bp.get("/profile")
@login_required
def edit() -> str | tuple[str, int]:
    """Own profile editor (professor fields or the small student form)."""
    user = current_user()
    assert user is not None  # guaranteed by login_required
    if user.role == "professor":
        profile = ProfessorProfile.query.filter_by(user_id=user.id).first()
        if profile is None:
            profile = ProfessorProfile(
                user_id=user.id, department=department_choices()[0]
            )
            db.session.add(profile)
            db.session.commit()
        return _render_professor_editor(_professor_initial(profile), setup=False)
    student_profile = StudentProfile.query.filter_by(user_id=user.id).first()
    if student_profile is None:
        student_profile = StudentProfile(
            user_id=user.id, level="", field=""
        )
        db.session.add(student_profile)
        db.session.commit()
    return render_template(
        "profiles/edit.html",
        role="student",
        setup=False,
        data={
            "display_name": user.display_name,
            "level": student_profile.level,
            "field": student_profile.field,
        },
        post_url=url_for("profiles.edit"),
    )


@bp.post("/profile")
@login_required
def save() -> Response | tuple[str, int]:
    """Validate and persist the own-profile form."""
    user = current_user()
    assert user is not None  # guaranteed by login_required
    if user.role == "professor":
        data = _professor_form_data()
        errors = validate_professor_form(data)
        if errors:
            for error in errors:
                flash(error, "error")
            return _render_professor_editor(data, setup=False, status=400)
        profile = ProfessorProfile.query.filter_by(user_id=user.id).first()
        assert profile is not None  # created on GET
        apply_professor_form(user, profile, data)
        db.session.commit()
        flash("Profile saved.", "success")
        return redirect(url_for("profiles.edit"), code=303)
    data = {
        "display_name": request.form.get("display_name", ""),
        "level": request.form.get("level", ""),
        "field": request.form.get("field", ""),
    }
    errors = validate_student_form(data)
    if errors:
        for error in errors:
            flash(error, "error")
        return (
            render_template(
                "profiles/edit.html", role="student", setup=False,
                data=data, post_url=url_for("profiles.edit"),
            ),
            400,
        )
    student_profile = StudentProfile.query.filter_by(user_id=user.id).first()
    assert student_profile is not None  # created on GET
    apply_student_form(user, student_profile, data)
    db.session.commit()
    flash("Profile saved.", "success")
    return redirect(url_for("profiles.edit"), code=303)


@bp.get("/profile/setup")
@role_required("professor")
def setup_form() -> tuple[str, int]:
    """Onboarding wizard step 2: complete the professor profile."""
    user = current_user()
    assert user is not None  # guaranteed by role_required
    profile = ProfessorProfile.query.filter_by(user_id=user.id).first()
    if profile is None:
        profile = ProfessorProfile(
            user_id=user.id, department=department_choices()[0]
        )
        db.session.add(profile)
        db.session.commit()
    return _render_professor_editor(_professor_initial(profile), setup=True)


@bp.post("/profile/setup")
@role_required("professor")
def setup() -> Response | tuple[str, int]:
    """Persist the wizard profile, then enter the workspace."""
    user = current_user()
    assert user is not None  # guaranteed by role_required
    data = _professor_form_data()
    errors = validate_professor_form(data)
    if errors:
        for error in errors:
            flash(error, "error")
        return _render_professor_editor(data, setup=True, status=400)
    profile = ProfessorProfile.query.filter_by(user_id=user.id).first()
    assert profile is not None  # created on GET
    apply_professor_form(user, profile, data)
    db.session.commit()
    flash("Profile complete. Welcome to your workspace.", "success")
    return redirect(url_for("cases.dashboard"), code=303)
