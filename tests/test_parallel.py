"""Parallel diagnosis tests: orchestration, partial failure, mode flag.

No network: a routing fake answers specialist, merge and ranking prompts.
"""
from __future__ import annotations

import json
from typing import Any

from flask import Flask

from app.extensions import db
from app.models import CaseFile, Document, RunEvent
from app.services.diagnosis import run_case_pipeline
from app.services.extraction import save_upload
from app.services.meta_client import ChatResult
from scripts.make_samples import PDF_FLAWS, PDF_PAGES, pdf_bytes
from tests.test_intake import make_student

STAT_GAP = {
    "category": "statistics",
    "description": "Accepts the null at p = 0.06.",
    "severity": 3,
    "evidence": [{"page": 1, "quote": PDF_FLAWS[0]["quote"]}],
}
METHOD_GAP = {
    "category": "methodology",
    "description": "Generalizes from 8 hostel friends.",
    "severity": 2,
    "evidence": [{"page": 2, "quote": PDF_FLAWS[1]["quote"]}],
}
LIT_GAP = {
    "category": "literature",
    "description": "Claims no literature exists without review.",
    "severity": 1,
    "evidence": [{"page": 2, "quote": PDF_FLAWS[2]["quote"]}],
}
MERGE_PAYLOAD = {
    "field": "Statistics",
    "level": "masters",
    "core_problem": "Weak tests, overstated claims.",
    "what_student_already_tried": ["Ran the regression twice."],
    "questions_for_professor": ["Is my power adequate?"],
    "expertise_keywords": ["hypothesis testing"],
    "confidence": 0.8,
}


class RoutingFake:
    """Fake client routing specialist/merge prompts to canned payloads."""

    def __init__(self, fail_on: tuple[str, ...] = ()) -> None:
        self.fail_on = fail_on

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: Any = None,
        *,
        model: str,
        response_format: dict[str, Any] | None = None,
        effort: str | None = None,
    ) -> ChatResult:
        """Answer by prompt marker; raise for names in fail_on."""
        text = json.dumps(messages)
        if "MERGE PASS" in text:
            if "merge" in self.fail_on:
                raise RuntimeError("merge down")
            return ChatResult(text=json.dumps(MERGE_PAYLOAD))
        for name, gap in (
            ("methodology", METHOD_GAP),
            ("statistics", STAT_GAP),
            ("breadth", LIT_GAP),
        ):
            if f"CATEGORY FOCUS: {name}" in text:
                if name in self.fail_on:
                    raise RuntimeError(f"{name} down")
                return ChatResult(text=json.dumps({"gaps": [gap]}))
        raise AssertionError("unexpected prompt without a routing marker")


def seed_parallel_case(app: Flask, tmp_path) -> CaseFile:  # type: ignore[no-untyped-def]
    """Persist a student, sample upload and running case; return the case."""
    user = make_student("parallel@example.com")
    stored = save_upload(pdf_bytes(PDF_PAGES), "pdf", tmp_path / "uploads")
    document = Document(
        student_id=user.id, file_path=str(stored), extracted_text=""
    )
    db.session.add(document)
    db.session.flush()
    case = CaseFile(
        student_id=user.id, document_id=document.id,
        problem_text="My supervisor says my conclusions overstate my tests.",
        status="running", run_id="run-parallel-1",
    )
    db.session.add(case)
    db.session.commit()
    return case


def event_types(run_id: str) -> list[str]:
    """Timeline event types in sequence order."""
    return [
        event.type
        for event in RunEvent.query.filter_by(run_id=run_id)
        .order_by(RunEvent.seq).all()
    ]


def test_parallel_success_merges_and_ranks(app: Flask, tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Three specialists merge into ranked, grounded gaps with telemetry."""
    case = seed_parallel_case(app, tmp_path)
    run_case_pipeline(
        app, case.id, "run-parallel-1",
        chat_client=RoutingFake(), model="fake-model",
    )
    db.session.refresh(case)
    assert case.status == "done"
    assert case.diagnosis["core_problem"] == "Weak tests, overstated claims."
    assert [gap["severity"] for gap in case.diagnosis["gaps"]] == [3, 2, 1]
    assert case.diagnosis["partial"] is False
    assert case.grounding_rate == 1.0
    assert sorted(event_types("run-parallel-1")) == sorted(
        [
            "upload_received", "text_extracted", "diagnosis_started",
            "specialist_done", "specialist_done", "specialist_done",
            "merge_finished", "grounding_checked",
        ]
    )
    done = RunEvent.query.filter_by(
        run_id="run-parallel-1", type="specialist_done"
    ).all()
    assert all("gaps" in event.payload and "latency_s" in event.payload for event in done)


def test_parallel_partial_failure_keeps_going(app: Flask, tmp_path) -> None:  # type: ignore[no-untyped-def]
    """One dead specialist is flagged; the other gaps still persist."""
    case = seed_parallel_case(app, tmp_path)
    run_case_pipeline(
        app, case.id, "run-parallel-1",
        chat_client=RoutingFake(fail_on=("statistics",)), model="fake-model",
    )
    db.session.refresh(case)
    assert case.status == "done"
    assert case.diagnosis["partial"] is True
    assert case.diagnosis["failed_specialists"] == ["statistics"]
    assert len(case.diagnosis["gaps"]) == 2
    assert "specialist_failed" in event_types("run-parallel-1")


def test_parallel_total_failure_marks_error(app: Flask, tmp_path) -> None:  # type: ignore[no-untyped-def]
    """No surviving specialist means a failed run, not an empty diagnosis."""
    case = seed_parallel_case(app, tmp_path)
    run_case_pipeline(
        app, case.id, "run-parallel-1",
        chat_client=RoutingFake(
            fail_on=("methodology", "statistics", "breadth")
        ),
        model="fake-model",
    )
    db.session.refresh(case)
    assert case.status == "error"
    assert "run_failed" in event_types("run-parallel-1")


def test_parallel_merge_failure_keeps_gaps(app: Flask, tmp_path) -> None:  # type: ignore[no-untyped-def]
    """A dead merge still persists the grounded specialist gaps."""
    case = seed_parallel_case(app, tmp_path)
    run_case_pipeline(
        app, case.id, "run-parallel-1",
        chat_client=RoutingFake(fail_on=("merge",)), model="fake-model",
    )
    db.session.refresh(case)
    assert case.status == "done"
    assert len(case.diagnosis["gaps"]) == 3
    assert case.diagnosis["core_problem"] == ""
    assert "merge_failed" in event_types("run-parallel-1")


def test_invalid_mode_fails_clearly(app: Flask, tmp_path) -> None:  # type: ignore[no-untyped-def]
    """A bad DIAGNOSIS_MODE becomes a run_failed event naming the value."""
    app.config["DIAGNOSIS_MODE"] = "turbo"
    case = seed_parallel_case(app, tmp_path)
    run_case_pipeline(
        app, case.id, "run-parallel-1",
        chat_client=RoutingFake(), model="fake-model",
    )
    db.session.refresh(case)
    assert case.status == "error"
    failed = RunEvent.query.filter_by(
        run_id="run-parallel-1", type="run_failed"
    ).one()
    assert "turbo" in failed.label
