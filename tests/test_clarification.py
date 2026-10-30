"""Clarification tests: questions, constraints, speculative handoff. No network."""
from __future__ import annotations

import json
import os
from typing import Any

from flask import Flask

from app.extensions import db
from app.models import (
    CaseFile, ClarificationQA, MatchResult, ProfessorProfile, RunEvent,
    ToolCallLog, User,
)
from app.services.clarification import (
    apply_answer_constraints,
    generate_questions,
    load_answers,
    parse_budget_cap,
    times_overlap,
    validate_questions,
)
from app.services.diagnosis import _run_clarification_phase, run_post_answer_matching
from app.services.matching import run_matching
from app.services.meta_client import ChatResult
from tests.test_booking import login_sample_student
from tests.test_matching import FakeMatchClient, make_ranking, seed_match_case

GAP_IDS = {"g1", "g2"}

CANNED_QUESTIONS = {
    "questions": [
        {
            "key": "budget",
            "type": "choice",
            "question": "Max budget per session?",
            "options": ["≤ ₦15,000", "≤ ₦25,000", "≤ ₦50,000", "No limit"],
            "why": "Rates vary widely across matches.",
            "gap_ids": ["g1"],
        },
        {
            "key": "goal",
            "type": "text",
            "question": "What do you want from the session?",
            "options": [],
            "why": "Shapes the agenda.",
            "gap_ids": ["g2", "g9"],
        },
    ]
}


class ClarifyFake:
    """Canned structured answers for the question-generation call."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.models: list[str] = []

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: Any = None,
        *,
        model: str,
        response_format: dict[str, Any] | None = None,
        effort: str | None = None,
    ) -> ChatResult:
        """Serve the canned payload, recording the model used."""
        self.models.append(model)
        return ChatResult(text=json.dumps(self.payload))


def seed_database_user(email: str, availability: dict[str, Any]) -> None:
    """Minimal non-sample professor with the given availability."""
    user = User(display_name="Dr. Test Overlap", email=email, role="professor")
    user.set_password("password-123")
    db.session.add(user)
    db.session.flush()
    db.session.add(
        ProfessorProfile(
            user_id=user.id, department="Statistics", research_areas=[],
            bio="", rate=10000.0, timezone="Africa/Lagos",
            availability=availability, accepting_new=True,
        )
    )
    db.session.commit()


def pause_case() -> CaseFile:
    """Seeded case paused at awaiting_answers with 2 canned questions."""
    case = seed_match_case()
    fake = ClarifyFake(CANNED_QUESTIONS)
    proceed = _run_clarification_phase(case, case.run_id or "run-qa-1", fake, "spark-x", "low")
    assert proceed is False
    db.session.refresh(case)
    assert case.status == "awaiting_answers"
    return case


def test_validate_questions_drops_garbage() -> None:
    """Bad keys, types, option counts and dup keys are dropped; cap is 3."""
    raw = {
        "questions": [
            {"key": "budget", "type": "choice", "question": "Budget?",
             "options": ["a", "b", "c"], "why": "w", "gap_ids": ["g1"]},
            {"key": "motto", "type": "choice", "question": "Motto?",
             "options": ["a", "b", "c"], "why": "w", "gap_ids": []},
            {"key": "goal", "type": "chat", "question": "Goal?",
             "options": [], "why": "w", "gap_ids": []},
            {"key": "times", "type": "choice", "question": "Times?",
             "options": ["only", "two"], "why": "w", "gap_ids": []},
            {"key": "budget", "type": "choice", "question": "Budget again?",
             "options": ["a", "b", "c"], "why": "w", "gap_ids": []},
            {"key": "deadline", "type": "choice", "question": "When?",
             "options": ["a", "b", "c"], "why": "w", "gap_ids": ["g7"]},
            {"key": "goal", "type": "text", "question": "Goal?",
             "options": [], "why": "w", "gap_ids": []},
        ]
    }
    valid = validate_questions(raw, GAP_IDS)
    assert [item["key"] for item in valid] == ["budget", "deadline", "goal"]
    assert valid[1]["gap_ids"] == []  # unknown gap stripped, question kept


def test_generate_questions_uses_spark_canned(app: Flask) -> None:
    """Generation validates the model payload and records the model."""
    case = seed_match_case()
    fake = ClarifyFake(CANNED_QUESTIONS)
    questions = generate_questions(
        fake, case.diagnosis or {}, ["g1", "g2"], "spark-x", "low"
    )
    assert fake.models == ["spark-x"]
    assert [item["key"] for item in questions] == ["budget", "goal"]
    assert questions[1]["gap_ids"] == ["g2"]


def test_parse_budget_cap() -> None:
    """Naira amounts parse; no-limit phrases and garbage yield None."""
    assert parse_budget_cap("≤ ₦25,000") == 25000
    assert parse_budget_cap("25000") == 25000
    assert parse_budget_cap("25k") == 25000
    assert parse_budget_cap("2m") == 2_000_000
    assert parse_budget_cap("No limit") is None
    assert parse_budget_cap("flexible") is None
    assert parse_budget_cap("not sure") is None
    assert parse_budget_cap("") is None


def test_times_overlap(app: Flask) -> None:
    """Weekday-morning pattern overlaps mornings only."""
    availability = {"days": ["Monday"], "windows": [["10:00", "14:00"]]}
    assert times_overlap(availability, "Weekday mornings") is True
    assert times_overlap(availability, "Weekday evenings") is False
    assert times_overlap(availability, "Weekends") is False
    assert times_overlap(availability, "whenever") is False
    assert times_overlap(None, "Weekday mornings") is False


def test_budget_filters_and_relaxes(app: Flask) -> None:
    """Budget drops pricey candidates; empty results relax with a note."""
    seed_match_case()
    candidates = [
        {"professor_id": 1, "score": 5, "rate": 11000.0},
        {"professor_id": 8, "score": 9, "rate": 18000.0},
        {"professor_id": 30, "score": 7, "rate": None},
        {"professor_id": 35, "score": 6, "rate": 45000.0},
    ]
    filtered = apply_answer_constraints(candidates, {"budget": "≤ ₦25,000"})
    assert [hit["professor_id"] for hit in filtered.candidates] == [1, 8, 30]
    assert filtered.filters_applied == ["Budget ≤ ₦25,000/session"]
    assert filtered.relaxed == []
    pricey = [hit for hit in candidates if hit.get("rate")]
    relaxed = apply_answer_constraints(pricey, {"budget": "₦5,000"})
    assert [hit["professor_id"] for hit in relaxed.candidates] == [1, 8, 35]
    assert relaxed.filters_applied == []
    assert len(relaxed.relaxed) == 1 and "relaxed" in relaxed.relaxed[0]


def test_times_boost_reorders_overlapping(app: Flask) -> None:
    """Weekend availability outranks equal weekday scores on weekends."""
    seed_database_user(
        "weekend@example.com", {"days": ["Saturday"], "windows": [["10:00", "14:00"]]}
    )
    seed_database_user(
        "weekday@example.com", {"days": ["Monday"], "windows": [["10:00", "14:00"]]}
    )
    weekend = User.query.filter_by(email="weekend@example.com").one()
    weekday = User.query.filter_by(email="weekday@example.com").one()
    candidates = [
        {"professor_id": weekday.id, "score": 5, "rate": 10000.0},
        {"professor_id": weekend.id, "score": 5, "rate": 10000.0},
    ]
    boosted = apply_answer_constraints(candidates, {"times": "Weekends"})
    assert [hit["professor_id"] for hit in boosted.candidates] == [
        weekend.id, weekday.id,
    ]
    assert boosted.filters_applied == ["Preferred times: Weekends"]
    assert "prefers Weekends" in boosted.prompt_block


def test_goal_and_deadline_join_prompt(app: Flask) -> None:
    """Goal and deadline surface in the ranking prompt and filter list."""
    seed_match_case()
    candidates = [{"professor_id": 8, "score": 9, "rate": 18000.0}]
    result = apply_answer_constraints(
        candidates,
        {"goal": "Fix my identification.", "deadline": "Within 2 weeks"},
    )
    assert result.candidates == candidates  # soft constraints keep everyone
    assert "Fix my identification." in result.prompt_block
    assert "Within 2 weeks" in result.prompt_block
    assert "Session goal considered in ranking" in result.filters_applied
    assert "Deadline: Within 2 weeks" in result.filters_applied


def test_clarification_phase_pauses_with_snapshot(app: Flask) -> None:
    """Questions pause the pipeline; snapshot and rows persist."""
    case = pause_case()
    rows = ClarificationQA.query.filter_by(case_id=case.id).all()
    assert [row.question_key for row in rows] == ["budget", "goal"]
    assert all(row.answer is None for row in rows)
    snapshot = case.candidate_snapshot or {}
    assert len(snapshot["candidates"]) == 8
    assert snapshot["keywords"] == ["econometrics"]
    assert snapshot["field"] == "Economics"
    assert snapshot["candidates"][0]["professor_id"] == 8
    assert RunEvent.query.filter_by(
        run_id=case.run_id, type="questions_ready"
    ).count() == 1
    assert ToolCallLog.query.filter_by(tool_name="search_professors").count() == 1


def test_clarification_failure_and_empty_proceed(app: Flask) -> None:
    """Failed or empty question generation never blocks matching."""
    case = seed_match_case()

    class Exploding:
        def chat(self, *args: Any, **kwargs: Any) -> ChatResult:
            raise RuntimeError("model is down")

    assert _run_clarification_phase(
        case, case.run_id or "run-qa-1", Exploding(), "spark-x", "low"
    ) is True
    assert RunEvent.query.filter_by(
        run_id=case.run_id, type="questions_failed"
    ).count() == 1
    assert (case.candidate_snapshot or {}).get("candidates")  # speculated anyway

    assert _run_clarification_phase(
        case, case.run_id or "run-qa-1", ClarifyFake({"questions": []}),
        "spark-x", "low",
    ) is True
    assert ClarificationQA.query.filter_by(case_id=case.id).count() == 0


def test_speculative_handoff_skips_search(app: Flask) -> None:
    """Post-answer matching reuses the snapshot: no second search."""
    case = pause_case()
    searches_before = ToolCallLog.query.filter_by(
        tool_name="search_professors"
    ).count()
    assert searches_before == 1
    outcome = run_matching(
        case, case.run_id or "run-qa-1",
        FakeMatchClient([make_ranking(12, 2, 1)]),
        model="fake-match", effort=None, snapshot=case.candidate_snapshot,
    )
    assert [row.professor_id for row in outcome.matches] == [12, 2, 1]
    assert ToolCallLog.query.filter_by(
        tool_name="search_professors"
    ).count() == searches_before
    assert RunEvent.query.filter_by(
        run_id=case.run_id, type="candidates_reused"
    ).count() == 1


def test_snapshot_fallback_searches_fresh(app: Flask) -> None:
    """A stale snapshot (dead ids) falls back to a logged fresh search."""
    case = seed_match_case()
    snapshot = {
        "keywords": ["econometrics"],
        "field": "Economics",
        "candidates": [{"professor_id": 999, "score": 9, "rate": None}],
        "constraint_block": "",
        "filters_applied": [],
        "relaxed": [],
    }
    outcome = run_matching(
        case, "run-match-1", FakeMatchClient([make_ranking(8, 7, 9)]),
        model="fake-match", effort=None, snapshot=snapshot,
    )
    assert [row.professor_id for row in outcome.matches] == [8, 7, 9]
    assert ToolCallLog.query.filter_by(
        tool_name="search_professors"
    ).count() == 1  # the fallback search really ran
    assert RunEvent.query.filter_by(
        run_id="run-match-1", type="candidates_reused"
    ).count() == 0


def test_question_panel_renders(app: Flask) -> None:
    """Awaiting cases show chips, free text, submit and skip."""
    case = pause_case()
    client = app.test_client()
    login_sample_student(client)
    html = client.get(f"/cases/{case.id}").get_data(as_text=True)
    assert "Mentora needs 2 quick answers" in html
    assert "Max budget per session?" in html
    assert "≤ ₦25,000" in html
    assert "Why we ask:" in html
    assert "Skip and match now" in html
    assert "Submit and match" in html


def test_submit_answers_constrains_and_launches(app: Flask, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Submit persists answers, filters the snapshot, launches matching."""
    case = pause_case()
    launched: list[tuple[int, str]] = []
    monkeypatch.setattr(
        "app.blueprints.cases._launch_matching",
        lambda app_obj, case_id, run_id: launched.append((case_id, run_id)),
    )
    rows = ClarificationQA.query.filter_by(case_id=case.id).all()
    budget_row = next(row for row in rows if row.question_key == "budget")
    goal_row = next(row for row in rows if row.question_key == "goal")
    client = app.test_client()
    login_sample_student(client)
    response = client.post(
        f"/cases/{case.id}/answers",
        data={
            "action": "submit",
            f"choice_{budget_row.id}": "≤ ₦15,000",
            f"text_{goal_row.id}": "Fix my identification.",
        },
    )
    assert response.status_code == 303
    assert launched == [(case.id, case.run_id)]
    db.session.refresh(case)
    assert case.status == "running"
    assert load_answers(case.id) == {
        "budget": "≤ ₦15,000",
        "goal": "Fix my identification.",
    }
    snapshot = case.candidate_snapshot or {}
    assert [hit["professor_id"] for hit in snapshot["candidates"]] == [1, 2, 3, 4, 5]
    assert "Budget ≤ ₦15,000/session" in snapshot["filters_applied"]
    assert "Fix my identification." in snapshot["constraint_block"]


def test_skip_matches_raw_snapshot(app: Flask, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Skip leaves answers empty and the snapshot unconstrained."""
    case = pause_case()
    launched: list[tuple[int, str]] = []
    monkeypatch.setattr(
        "app.blueprints.cases._launch_matching",
        lambda app_obj, case_id, run_id: launched.append((case_id, run_id)),
    )
    before = list((case.candidate_snapshot or {})["candidates"])
    client = app.test_client()
    login_sample_student(client)
    response = client.post(f"/cases/{case.id}/answers", data={"action": "skip"})
    assert response.status_code == 303
    assert launched == [(case.id, case.run_id)]
    db.session.refresh(case)
    assert case.status == "running"
    assert load_answers(case.id) == {}
    after = (case.candidate_snapshot or {})["candidates"]
    assert after == before
    assert (case.candidate_snapshot or {})["filters_applied"] == []


def test_answers_rejected_off_status(app: Flask, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Double submits and other owners' cases never launch matching."""
    case = pause_case()
    launched: list[tuple[int, str]] = []
    monkeypatch.setattr(
        "app.blueprints.cases._launch_matching",
        lambda app_obj, case_id, run_id: launched.append((case_id, run_id)),
    )
    client = app.test_client()
    login_sample_student(client)
    assert client.post(
        f"/cases/{case.id}/answers", data={"action": "skip"}
    ).status_code == 303
    assert len(launched) == 1
    retry = client.post(
        f"/cases/{case.id}/answers", data={"action": "skip"},
        follow_redirects=True,
    )
    assert "not waiting for answers" in retry.get_data(as_text=True)
    assert len(launched) == 1
    other = app.test_client()
    other.post(
        "/auth/login",
        data={
            "email": "sample-student-02@example.com",
            "password": os.environ["SEED_DEMO_PASSWORD"],
        },
    )
    assert other.post(
        f"/cases/{case.id}/answers", data={"action": "skip"}
    ).status_code == 404


def test_post_answer_matching_finishes(app: Flask) -> None:
    """Post-answer run persists matches and flips the case to done."""
    case = pause_case()
    run_post_answer_matching(
        app, case.id, case.run_id or "run-qa-1",
        match_client=FakeMatchClient([make_ranking(8, 7, 9)]),
        match_model="fake-match",
    )
    db.session.refresh(case)
    assert case.status == "done"
    assert MatchResult.query.filter_by(case_id=case.id).count() == 3


def test_match_page_shows_applied_filters(app: Flask, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """After submit + match, the case page lists the applied filters."""
    case = pause_case()

    def _sync_launch(app_obj: Flask, case_id: int, run_id: str) -> None:
        run_post_answer_matching(
            app_obj, case_id, run_id,
            match_client=FakeMatchClient([make_ranking(1, 2, 3)]),
            match_model="fake-match",
        )

    monkeypatch.setattr("app.blueprints.cases._launch_matching", _sync_launch)
    rows = ClarificationQA.query.filter_by(case_id=case.id).all()
    budget_row = next(row for row in rows if row.question_key == "budget")
    client = app.test_client()
    login_sample_student(client)
    client.post(
        f"/cases/{case.id}/answers",
        data={"action": "submit", f"choice_{budget_row.id}": "≤ ₦15,000"},
    )
    html = client.get(f"/cases/{case.id}").get_data(as_text=True)
    assert "Filters applied from your answers" in html
    assert "Budget ≤ ₦15,000/session" in html
    assert "Recommended professors" in html
