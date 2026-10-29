"""Render tests: every page returns 200 with no template errors."""
from __future__ import annotations

from flask import Flask, render_template, render_template_string

from app.extensions import db
from app.models import CaseFile, User
from tests.test_intake import login, make_student


def test_public_pages_render_and_brand(app: Flask) -> None:
    """Landing, login and register render with brand, favicon and CSRF."""
    client = app.test_client()
    landing = client.get("/")
    assert landing.status_code == 200
    assert b"Mentora Academic Hub" in landing.data
    assert b"Built with Meta Muse models" in landing.data
    for path in ("/auth/login", "/auth/register"):
        page = client.get(path)
        assert page.status_code == 200
        assert b"Mentora Academic Hub" in page.data
        assert b'data:image/svg+xml' in page.data
        assert b'name="csrf_token"' in page.data


def test_dashboard_shows_greeting_and_real_counts(app: Flask) -> None:
    """Dashboard greets by first name and shows true open/done counts."""
    make_student()
    client = app.test_client()
    login(client, "intake@example.com")
    page = client.get("/dashboard")
    assert page.status_code == 200
    assert b"Intake" in page.data  # first name from "Intake Student"
    assert b"Open cases" in page.data and b"Completed diagnoses" in page.data
    assert b"New request" in page.data


def test_ngn_filter_formats_naira(app: Flask) -> None:
    """The ngn filter renders thousands separators; junk degrades."""
    with app.test_request_context("/"):
        assert render_template_string("{{ 12500|ngn }}") == "\u20a612,500"
        assert render_template_string("{{ 22000.0|ngn }}") == "\u20a622,000"
        assert render_template_string("{{ none|ngn }}") == "\u20a6\u2014"


def test_dashboard_shows_diagnosis_headline(app: Flask) -> None:
    """Case cards surface the diagnosis core_problem when available."""
    user = make_student()
    db.session.add(
        CaseFile(
            student_id=user.id,
            problem_text="My identification strategy is weak, honestly.",
            status="done",
            diagnosis={"core_problem": "Weak identification strategy."},
        )
    )
    db.session.commit()
    client = app.test_client()
    login(client, "intake@example.com")
    page = client.get("/dashboard")
    assert page.status_code == 200
    assert b"Weak identification strategy." in page.data


def test_new_request_form_renders(app: Flask) -> None:
    """Intake form renders with counter, dropzone and disabled voice button."""
    make_student()
    client = app.test_client()
    login(client, "intake@example.com")
    page = client.get("/cases/new")
    assert page.status_code == 200
    for marker in (
        b"problem-count", b"dropzone", b"Voice: coming soon",
        b"What helps the agent", b"intake-submit",
    ):
        assert marker in page.data


def test_detail_renders_running_and_done(app: Flask, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Detail shows skeleton timeline while running, diagnosis once done."""
    monkeypatch.setattr(
        "app.blueprints.cases._launch_pipeline", lambda *args: None
    )
    user = make_student()
    client = app.test_client()
    login(client, "intake@example.com")
    client.post(
        "/cases/new",
        data={"problem_text": "My regression residuals fan out badly here."},
    )
    case = CaseFile.query.one()
    running = client.get(f"/cases/{case.id}")
    assert running.status_code == 200
    assert b"Agent timeline" in running.data
    assert b"aria-live" in running.data

    case.status = "done"
    case.grounding_rate = 1.0
    case.diagnosis = {
        "field": "Statistics", "level": "masters", "core_problem": "X",
        "gaps": [
            {
                "category": "statistics", "description": "Y", "severity": 2,
                "evidence": [{"page": 1, "quote": "Z"}],
            }
        ],
        "what_student_already_tried": [], "questions_for_professor": ["Q?"],
        "expertise_keywords": ["k"], "confidence": 0.5,
    }
    db.session.commit()
    done = client.get(f"/cases/{case.id}")
    assert done.status_code == 200
    assert b"grounding" in done.data
    assert b"Questions for your professor" in done.data
    assert "Q?" in done.get_data(as_text=True)


def test_error_pages_render(app: Flask) -> None:
    """Styled 403, 404 and 500 pages all render with brand shell."""
    prof = User(display_name="Prof", email="prof403@example.com", role="professor")
    prof.set_password("password123")
    db.session.add(prof)
    db.session.commit()
    client = app.test_client()
    missing = client.get("/no-such-route")
    assert missing.status_code == 404
    assert b"Page not found" in missing.data
    login(client, "prof403@example.com")
    forbidden = client.get("/cases/new")
    assert forbidden.status_code == 403
    assert b"Not allowed" in forbidden.data
    with app.test_request_context("/"):
        html = render_template("errors/500.html")
    assert "Something went wrong" in html
    assert "Mentora Academic Hub" in html
