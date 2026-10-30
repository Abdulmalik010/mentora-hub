"""Profile tests: wizard, editor validation, directory inclusion, opt-outs."""
from __future__ import annotations

from datetime import datetime, timezone

from flask import Flask
from flask.testing import FlaskClient

from app.extensions import db
from app.models import ProfessorProfile, StudentProfile, User
from app.services.matching import search_professors
from app.services.profiles import validate_professor_form
from app.services.slots import generate_slots, validate_availability


def register_professor(client: FlaskClient, email: str = "new-prof@example.com"):
    """Register a professor; returns the POST response (logged in on success)."""
    return client.post(
        "/auth/register",
        data={
            "display_name": "New Professor",
            "email": email,
            "password": "password-123",
            "role": "professor",
            "department": "Statistics",
        },
    )


def make_professor(
    email: str,
    *,
    accepting: bool = True,
    areas: list[str] | None = None,
    display_name: str = "Dr. Test Professor",
) -> User:
    """Persist a non-sample professor directly (caller runs inside app ctx)."""
    user = User(display_name=display_name, email=email, role="professor")
    user.set_password("password-123")
    db.session.add(user)
    db.session.flush()
    db.session.add(
        ProfessorProfile(
            user_id=user.id,
            department="Statistics",
            research_areas=areas if areas is not None else ["survey sampling"],
            bio="Synthetic test profile.",
            rate=10000,
            timezone="Africa/Lagos",
            availability={
                "days": ["Monday"],
                "windows": [["10:00", "14:00"]],
            },
            accepting_new=accepting,
        )
    )
    db.session.commit()
    return user


def valid_wizard_form() -> dict:
    """Complete, valid onboarding payload."""
    return {
        "first_name": "Ada",
        "last_name": "Okafor",
        "title": "Dr.",
        "rank": "Senior Lecturer",
        "department": "Statistics",
        "research_areas": "survey sampling, causal inference",
        "bio": "Synthetic test bio.",
        "rate": "15000",
        "timezone": "Africa/Lagos",
        "days": ["Monday", "Wednesday"],
        "window_opens": ["10:00", "15:00"],
        "window_closes": ["12:00", "17:00"],
        "accepting_new": "yes",
    }


def test_professor_register_redirects_to_wizard(app: Flask) -> None:
    """New professors land on the onboarding wizard, logged in."""
    client = app.test_client()
    response = register_professor(client)
    assert response.status_code in (302, 303)
    assert response.headers["Location"].endswith("/profile/setup")
    page = client.get("/profile/setup")
    assert page.status_code == 200
    assert "Complete your profile" in page.get_data(as_text=True)


def test_wizard_valid_post_completes_profile(app: Flask) -> None:
    """Wizard persists names, areas, windows and the composed display name."""
    client = app.test_client()
    register_professor(client)
    response = client.post("/profile/setup", data=valid_wizard_form())
    assert response.status_code == 303
    user = User.query.filter_by(email="new-prof@example.com").one()
    profile = ProfessorProfile.query.filter_by(user_id=user.id).one()
    assert user.display_name == "Dr. Ada Okafor"
    assert profile.rank == "Senior Lecturer"
    assert profile.research_areas == ["survey sampling", "causal inference"]
    assert profile.rate == 15000
    assert profile.availability == {
        "days": ["Monday", "Wednesday"],
        "windows": [["10:00", "12:00"], ["15:00", "17:00"]],
    }
    assert profile.accepting_new is True


def test_wizard_overlapping_windows_rejected(app: Flask) -> None:
    """Overlapping windows fail with a 400 and keep the wizard up."""
    client = app.test_client()
    register_professor(client)
    form = valid_wizard_form()
    form["window_opens"] = ["10:00", "11:00"]
    form["window_closes"] = ["12:00", "13:00"]
    response = client.post("/profile/setup", data=form)
    assert response.status_code == 400
    assert "must not overlap" in response.get_data(as_text=True)


def test_setup_requires_professor_role(app: Flask) -> None:
    """Students get 403 on the wizard; anonymous users go to login."""
    client = app.test_client()
    client.post(
        "/auth/register",
        data={
            "display_name": "Student One",
            "email": "student-one@example.com",
            "password": "password-123",
            "role": "student",
            "level": "masters",
            "field": "Statistics",
        },
    )
    assert client.get("/profile/setup").status_code == 403
    anonymous = app.test_client()
    response = anonymous.get("/profile/setup")
    assert response.status_code in (301, 302, 303)


def test_validate_availability_edges() -> None:
    """Whole-hour, order, overlap, day and presence rules all fire."""
    assert "pick at least one day" in validate_availability([], [("10:00", "12:00")])
    errors = validate_availability(["Monday"], [("10:30", "12:00")])
    assert any("on the hour" in error for error in errors)
    errors = validate_availability(["Monday"], [("14:00", "12:00")])
    assert any("before it starts" in error for error in errors)
    assert "unknown day: Funday" in validate_availability(
        ["Funday"], [("10:00", "12:00")]
    )
    errors = validate_availability(
        ["Monday"], [("10:00", "12:00"), ("11:00", "13:00")]
    )
    assert "time windows must not overlap" in errors
    assert "add at least one time window" in validate_availability(["Monday"], [])
    assert validate_availability(
        ["Monday"], [("10:00", "12:00"), ("12:00", "14:00")]
    ) == []


def test_validate_professor_form_edges(app: Flask) -> None:
    """Title, rate, timezone, areas and names are all checked."""
    base = {
        "first_name": "Ada",
        "last_name": "Okafor",
        "title": "Dr.",
        "rank": "Senior Lecturer",
        "department": "Statistics",
        "research_areas": "survey sampling",
        "bio": "ok",
        "rate": "15000",
        "timezone": "Africa/Lagos",
        "days": ["Monday"],
        "windows": [("10:00", "12:00")],
        "accepting_new": True,
    }
    assert validate_professor_form(base) == []
    bad_title = dict(base, title="King")
    assert any("title" in error for error in validate_professor_form(bad_title))
    bad_rate = dict(base, rate="-5")
    assert any("negative" in error for error in validate_professor_form(bad_rate))
    bad_tz = dict(base, timezone="Mars/Olympus")
    assert any("timezone" in error for error in validate_professor_form(bad_tz))
    many = dict(base, research_areas=", ".join(f"area {n}" for n in range(9)))
    assert any("at most 8" in error for error in validate_professor_form(many))
    empty_areas = dict(base, research_areas="  ")
    assert any("research area" in error for error in validate_professor_form(empty_areas))
    no_name = dict(base, first_name=" ")
    assert any("first name" in error for error in validate_professor_form(no_name))


def test_multi_window_slot_generation() -> None:
    """Both windows produce hourly slots on listed weekdays only."""
    availability = {
        "days": ["Monday"],
        "windows": [["10:00", "12:00"], ["15:00", "16:00"]],
    }
    # A Sunday noon UTC anchors the week: offsets 1..7 cover Mon..Sun.
    anchor = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)
    slots = generate_slots(availability, days_ahead=7, now=anchor)
    wat_hours = sorted(
        slot.start_wat.hour for slot in slots if slot.start_wat.strftime("%A") == "Monday"
    )
    assert wat_hours == [10, 11, 15]
    assert all(slot.start_wat.strftime("%A") == "Monday" for slot in slots)


def test_matching_excludes_opted_out_professors(app: Flask) -> None:
    """accepting_new=False removes a professor from search hits."""
    make_professor("accepting@example.com", accepting=True)
    hidden = make_professor(
        "hidden@example.com", accepting=False, display_name="Dr. Hidden Scholar"
    )
    hits = search_professors(["sampling"])
    ids = [hit["professor_id"] for hit in hits]
    assert hidden.id not in ids
    assert len(ids) == 1


def test_directory_badges_and_exclusion(app: Flask) -> None:
    """Directory shows Self-registered, hides opted-out professors."""
    make_professor(
        "visible@example.com",
        accepting=True,
        display_name="Dr. Visible Scholar",
    )
    make_professor(
        "optout@example.com",
        accepting=False,
        display_name="Dr. Opted Out",
    )
    html = app.test_client().get("/professors").get_data(as_text=True)
    assert "Dr. Visible Scholar" in html
    assert "Self-registered" in html
    assert "Dr. Opted Out" not in html
    assert "(demo)" in html


def test_detail_page_marks_not_accepting(app: Flask) -> None:
    """Direct profile links still render, flagged as not accepting."""
    hidden = make_professor(
        "direct@example.com",
        accepting=False,
        display_name="Dr. Direct Link",
    )
    response = app.test_client().get(f"/professors/{hidden.id}")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Not accepting requests" in html
    assert "Mon · 10:00-14:00 WAT" in html


def test_editor_renders_with_live_preview(app: Flask) -> None:
    """Professor editor GET shows the form and the preview card."""
    user = make_professor("editor@example.com")
    client = app.test_client()
    client.post(
        "/auth/login",
        data={"email": user.email, "password": "password-123"},
    )
    html = client.get("/profile").get_data(as_text=True)
    assert "Live preview" in html
    assert 'name="research_areas"' in html
    assert 'name="window_opens"' in html


def test_professor_edit_post_updates_profile(app: Flask) -> None:
    """Saving the editor persists changes and composes the display name."""
    user = make_professor("save@example.com")
    client = app.test_client()
    client.post(
        "/auth/login",
        data={"email": user.email, "password": "password-123"},
    )
    form = valid_wizard_form()
    form["accepting_new"] = "yes"
    response = client.post("/profile", data=form)
    assert response.status_code == 303
    db.session.expire_all()
    updated = db.session.get(User, user.id)
    assert updated is not None
    assert updated.display_name == "Dr. Ada Okafor"


def test_student_profile_edit(app: Flask) -> None:
    """Students get the small name/level/field form, persisted on POST."""
    client = app.test_client()
    client.post(
        "/auth/register",
        data={
            "display_name": "Student Two",
            "email": "student-two@example.com",
            "password": "password-123",
            "role": "student",
            "level": "masters",
            "field": "Statistics",
        },
    )
    assert "Profile" in client.get("/profile").get_data(as_text=True)
    response = client.post(
        "/profile",
        data={
            "display_name": "Student Two Renamed",
            "level": "phd",
            "field": "Economics",
        },
    )
    assert response.status_code == 303
    user = User.query.filter_by(email="student-two@example.com").one()
    profile = StudentProfile.query.filter_by(user_id=user.id).one()
    assert user.display_name == "Student Two Renamed"
    assert (profile.level, profile.field) == ("phd", "Economics")
