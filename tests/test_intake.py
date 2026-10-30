"""Intake tests: extraction, validation, grounding, access, pipeline.

No network: the diagnosis pipeline runs against a canned fake client, and
route tests stub out the background-thread launcher so no real call can fire.
"""
from __future__ import annotations

import io
import json
from typing import Any

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app.extensions import db
from app.models import CaseFile, Document, RunEvent, User
from app.services.diagnosis import (
    check_grounding,
    coerce_diagnosis,
    normalize_text,
    run_case_pipeline,
)
from app.services.extraction import (
    ExtractionError,
    extract_text,
    save_upload,
    validate_upload,
)
from app.services.meta_client import ChatResult
from scripts.make_samples import (
    DOCX_FLAWS,
    DOCX_PARAGRAPHS,
    PDF_FLAWS,
    PDF_PAGES,
    docx_bytes,
    expected_flaws,
    pdf_bytes,
)

PROBLEM = "My regression residuals fan out and my supervisor questions the standard errors."
OTHER_PROBLEM = "I cannot tell whether my literature review actually supports my hypothesis."


def make_student(email: str = "intake@example.com") -> User:
    """Persist a student with a known password (needs app context)."""
    user = User(display_name="Intake Student", email=email, role="student")
    user.set_password("password123")
    db.session.add(user)
    db.session.commit()
    return user


def login(client: FlaskClient, email: str) -> Any:  # type: ignore[type-arg]
    """Log in with the shared test password."""
    return client.post(
        "/auth/login", data={"email": email, "password": "password123"}
    )


@pytest.fixture(autouse=True)
def _stub_matching(monkeypatch):  # type: ignore[no-untyped-def]
    """Intake tests cover diagnosis; matching is tested separately offline."""
    monkeypatch.setattr(
        "app.services.diagnosis._run_matching_phase", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(
        "app.services.diagnosis._run_clarification_phase",
        lambda *args, **kwargs: True,
    )


class CannedJsonClient:
    """Fake chat client returning one canned JSON payload as text."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.seen: list[list[dict[str, Any]]] = []

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: Any = None,
        *,
        model: str,
        response_format: dict[str, Any] | None = None,
        effort: str | None = None,
    ) -> ChatResult:
        """Record the prompt and return the canned diagnosis JSON."""
        assert model, "pipeline must pass a model"
        self.seen.append(messages)
        return ChatResult(text=json.dumps(self.payload))


def canned_diagnosis() -> dict[str, Any]:
    """Diagnosis with one grounded and one ungrounded evidence quote."""
    return {
        "field": "Statistics",
        "level": "masters",
        "core_problem": "Overstated conclusions from weak tests.",
        "gaps": [
            {
                "category": "statistics",
                "description": "Accepts the null at p = 0.06.",
                "severity": 3,
                "evidence": [
                    {"page": 1, "quote": PDF_FLAWS[0]["quote"]},
                    {"page": 2, "quote": "a sentence that appears nowhere"},
                ],
            }
        ],
        "what_student_already_tried": ["Ran the regression twice."],
        "questions_for_professor": ["Is my power adequate?"],
        "expertise_keywords": ["hypothesis testing"],
        "confidence": 0.7,
    }


def test_extract_generated_pdf(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Two-page sample PDF extracts with page markers and is not scanned."""
    path = tmp_path / "sample.pdf"
    path.write_bytes(pdf_bytes(PDF_PAGES))
    result = extract_text(path, "pdf")
    assert result.pages == 2
    assert result.scanned is False
    assert "[[page 1]]" in result.text and "[[page 2]]" in result.text
    assert "Peer Tutorials" in result.text


def test_extract_generated_docx(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Sample DOCX extracts paragraphs with a single page marker."""
    path = tmp_path / "sample.docx"
    path.write_bytes(docx_bytes(DOCX_PARAGRAPHS))
    result = extract_text(path, "docx")
    assert result.pages == 1
    assert result.text.startswith("[[page 1]]")
    assert "TODO: expand this section before submission." in result.text


def test_expected_quotes_ground_against_samples(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Every expected.json flaw quote is verbatim in its extracted sample."""
    pdf_path = tmp_path / "s.pdf"
    pdf_path.write_bytes(pdf_bytes(PDF_PAGES))
    docx_path = tmp_path / "s.docx"
    docx_path.write_bytes(docx_bytes(DOCX_PARAGRAPHS))
    sources = {
        "thesis_excerpt_stats.pdf": extract_text(pdf_path, "pdf").text,
        "thesis_excerpt_methods.docx": extract_text(docx_path, "docx").text,
    }
    for filename, entry in expected_flaws().items():
        source = normalize_text(sources[filename])
        for flaw in entry["flaws"]:
            assert normalize_text(flaw["quote"]) in source, (filename, flaw["quote"])


def test_upload_validation_rejects_bad_inputs() -> None:
    """Extension, signature, size, emptiness and encoding are all checked."""
    assert validate_upload("a.PDF", b"%PDF-1.4 fake") == "pdf"
    with pytest.raises(ExtractionError):
        validate_upload("a.exe", b"MZ...")
    with pytest.raises(ExtractionError, match="bad signature"):
        validate_upload("a.pdf", b"not a pdf at all")
    with pytest.raises(ExtractionError, match="bad signature"):
        validate_upload("a.docx", b"%PDF-1.4 wrong type")
    with pytest.raises(ExtractionError, match="empty"):
        validate_upload("a.txt", b"")
    with pytest.raises(ExtractionError, match="10 MB"):
        validate_upload("a.txt", b"x" * (10 * 1024 * 1024 + 1))
    with pytest.raises(ExtractionError, match="UTF-8"):
        validate_upload("a.txt", b"\xff\xfe invalid")
    real_docx = docx_bytes(["hello"])
    assert validate_upload("a.docx", real_docx) == "docx"


def test_grounding_checker_drops_ungrounded_quotes() -> None:
    """Ungrounded evidence is dropped and the rate reflects it."""
    diagnosis = coerce_diagnosis(canned_diagnosis())
    source = "Accepts the null at p = 0.06. " + PDF_FLAWS[0]["quote"]
    result = check_grounding(diagnosis, source)
    assert (result.checked, result.dropped) == (2, 1)
    assert result.rate == pytest.approx(0.5)
    kept = result.diagnosis["gaps"][0]["evidence"]
    assert len(kept) == 1 and kept[0]["quote"] == PDF_FLAWS[0]["quote"]


def test_grounding_empty_evidence_scores_one() -> None:
    """No evidence to check means nothing ungrounded."""
    result = check_grounding({"gaps": []}, "anything")
    assert (result.rate, result.checked, result.dropped) == (1.0, 0, 0)


def test_create_case_happy_path(app: Flask, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Valid POST stores the upload, creates the case and launches the run."""
    launched: list[tuple[int, str]] = []
    monkeypatch.setattr(
        "app.blueprints.cases._launch_pipeline",
        lambda app_obj, case_id, run_id: launched.append((case_id, run_id)),
    )
    make_student()
    client = app.test_client()
    login(client, "intake@example.com")
    response = client.post(
        "/cases/new",
        data={
            "problem_text": PROBLEM,
            "document": (io.BytesIO(pdf_bytes(PDF_PAGES)), "thesis.pdf"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 302
    case = CaseFile.query.one()
    assert case.problem_text == PROBLEM and case.status == "running"
    assert case.run_id and launched == [(case.id, case.run_id)]
    document = Document.query.one()
    assert document.id == case.document_id
    assert response.headers["Location"].endswith(f"/cases/{case.id}")


def test_create_case_validates_problem_and_file(app: Flask) -> None:
    """Short problem text and bad uploads bounce with 400 and no case."""
    make_student()
    client = app.test_client()
    login(client, "intake@example.com")
    assert (
        client.post("/cases/new", data={"problem_text": "too short"}).status_code
        == 400
    )
    bad = client.post(
        "/cases/new",
        data={
            "problem_text": PROBLEM,
            "document": (io.BytesIO(b"nope"), "evil.pdf"),
        },
        content_type="multipart/form-data",
    )
    assert bad.status_code == 400
    assert CaseFile.query.count() == 0


def test_cases_are_owner_only(app: Flask, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Another student gets 404 on detail and event stream alike."""
    monkeypatch.setattr(
        "app.blueprints.cases._launch_pipeline", lambda *args: None
    )
    make_student("owner@example.com")
    make_student("other@example.com")
    client = app.test_client()
    login(client, "owner@example.com")
    client.post("/cases/new", data={"problem_text": PROBLEM})
    case = CaseFile.query.one()
    client.post("/auth/logout")
    login(client, "other@example.com")
    assert client.get(f"/cases/{case.id}").status_code == 404
    assert client.get(f"/cases/{case.id}/events").status_code == 404
    assert b"Case #1" not in client.get("/dashboard").data


def test_upload_form_requires_csrf_token(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """With CSRF on, a tokenless intake POST is rejected with 400."""
    from app import create_app

    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-only-not-a-real-secret",
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path}/csrf-cases.db",
            "UPLOAD_FOLDER": str(tmp_path / "uploads"),
        }
    )
    ctx = app.app_context()
    ctx.push()
    try:
        db.create_all()
        make_student()
        client = app.test_client()
        login(client, "intake@example.com")
        response = client.post("/cases/new", data={"problem_text": PROBLEM})
        assert response.status_code == 400
        assert CaseFile.query.count() == 0
    finally:
        db.session.remove()
        db.drop_all()
        ctx.pop()


def _seed_case_with_pdf(app: Flask, tmp_path, pdf_data: bytes) -> CaseFile:  # type: ignore[no-untyped-def]
    """Persist a student, stored upload and running case; return the case."""
    user = make_student()
    stored = save_upload(pdf_data, "pdf", tmp_path / "uploads")
    document = Document(
        student_id=user.id, file_path=str(stored), extracted_text=""
    )
    db.session.add(document)
    db.session.flush()
    case = CaseFile(
        student_id=user.id, document_id=document.id, problem_text=PROBLEM,
        status="running", run_id="run-test-1",
    )
    db.session.add(case)
    db.session.commit()
    return case


def test_pipeline_completes_and_writes_events(app: Flask, tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Fake-client run persists diagnosis, rate and an ordered timeline."""
    app.config["DIAGNOSIS_MODE"] = "single"
    case = _seed_case_with_pdf(app, tmp_path, pdf_bytes(PDF_PAGES))
    fake = CannedJsonClient(canned_diagnosis())
    run_case_pipeline(app, case.id, "run-test-1", chat_client=fake, model="fake-model")

    db.session.refresh(case)
    assert case.status == "done"
    assert case.diagnosis["field"] == "Statistics"
    assert case.grounding_rate == pytest.approx(0.5)
    events = RunEvent.query.filter_by(run_id="run-test-1").order_by(RunEvent.seq).all()
    assert [event.type for event in events] == [
        "upload_received", "text_extracted", "diagnosis_started",
        "diagnosis_finished", "grounding_checked",
    ]
    assert [event.seq for event in events] == [1, 2, 3, 4, 5]
    assert all(event.status == "ok" for event in events)
    assert "2 page" in events[1].label
    assert fake.seen and "<<<STUDENT_DOCUMENT>>>" in json.dumps(fake.seen[0])


def test_pipeline_falls_back_to_native_pdf(app: Flask, tmp_path) -> None:  # type: ignore[no-untyped-def]
    """A scanned PDF is sent natively and the decision is logged as an event."""
    app.config["DIAGNOSIS_MODE"] = "single"
    case = _seed_case_with_pdf(app, tmp_path, pdf_bytes([[""]]))
    fake = CannedJsonClient({**canned_diagnosis(), "gaps": []})
    run_case_pipeline(app, case.id, "run-test-1", chat_client=fake, model="fake-model")

    db.session.refresh(case)
    assert case.status == "done"
    types = [
        event.type
        for event in RunEvent.query.filter_by(run_id="run-test-1")
        .order_by(RunEvent.seq).all()
    ]
    assert types == [
        "upload_received", "text_extracted", "native_pdf_fallback",
        "diagnosis_started", "diagnosis_finished", "grounding_checked",
    ]
    blocks = fake.seen[0][1]["content"]
    assert any(block.get("type") == "file" for block in blocks)


def test_pipeline_marks_case_error_on_model_failure(app: Flask, tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Model exceptions become run_failed events, not raised errors."""
    app.config["DIAGNOSIS_MODE"] = "single"
    case = _seed_case_with_pdf(app, tmp_path, pdf_bytes(PDF_PAGES))

    class ExplodingClient(CannedJsonClient):
        def chat(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("model is down")

    run_case_pipeline(
        app, case.id, "run-test-1", chat_client=ExplodingClient({}), model="fake-model"
    )
    db.session.refresh(case)
    assert case.status == "error"
    failed = RunEvent.query.filter_by(run_id="run-test-1", type="run_failed").one()
    assert failed.status == "error" and "model is down" in failed.label
