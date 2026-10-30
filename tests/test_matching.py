"""Matching tests: tools, validator, tool-loop logging, routes. No network."""
from __future__ import annotations

import json
from datetime import date
from typing import Any

from flask import Flask

from app.extensions import db
from app.models import CaseFile, MatchResult, RunEvent, ToolCallLog, User
from app.services.matching import (
    check_availability,
    coerce_ranking,
    get_professor_profile,
    matching_tools,
    only_order_errors,
    run_matching,
    search_professors,
    summarize_tool_call,
    validate_ranking,
)
from app.services.meta_client import ChatResult, ToolCallRequest
from scripts.seed import seed_database
from tests.test_intake import login, make_student

DIAGNOSIS = {
    "field": "Economics",
    "level": "masters",
    "core_problem": "Weak identification strategy.",
    "gaps": [
        {
            "category": "statistics",
            "description": "No standard errors reported.",
            "severity": 3,
            "evidence": [{"page": 1, "quote": "results were significant"}],
        },
        {
            "category": "methodology",
            "description": "Convenience sample of friends.",
            "severity": 2,
            "evidence": [{"page": 2, "quote": "asked my friends"}],
        },
    ],
    "what_student_already_tried": [],
    "questions_for_professor": [],
    "expertise_keywords": ["econometrics"],
    "confidence": 0.7,
}


def make_ranking(*prof_ids: int) -> dict[str, Any]:
    """Valid 3-match ranking citing gaps g1/g2."""
    return {
        "matches": [
            {
                "professor_id": pid,
                "score": 90 - 5 * rank,
                "reasons": [
                    {
                        "gap_id": "g1",
                        "page": 1,
                        "quote": "results were significant",
                        "explanation": "Teaches inference.",
                    }
                ],
                "caveats": [],
                "next_slot": "2026-11-02 10:00 WAT",
            }
            for rank, pid in enumerate(prof_ids)
        ]
    }


class FakeMatchClient:
    """Fake serving one tool call, a shortlist, then queued rankings."""

    def __init__(self, rankings: list[dict[str, Any]]) -> None:
        self.rankings = list(rankings)
        self.calls = 0

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: Any = None,
        *,
        model: str,
        response_format: dict[str, Any] | None = None,
        effort: str | None = None,
    ) -> ChatResult:
        """Branch ranking calls from research calls by response_format."""
        assert model, "matching must pass a model"
        if response_format is not None:
            return ChatResult(text=json.dumps(self.rankings.pop(0)))
        self.calls += 1
        if self.calls == 1:
            return ChatResult(
                text="",
                tool_calls=(
                    ToolCallRequest(
                        id="call_1",
                        name="search_professors",
                        arguments={"keywords": ["econometrics"]},
                    ),
                ),
                raw_assistant_message={"role": "assistant", "content": ""},
            )
        return ChatResult(text="Shortlist: 12, 2, 1.")


def seed_match_case() -> CaseFile:
    """Seed professors and persist a diagnosed case; return it."""
    seed_database()
    student = User.query.filter_by(email="sample-student-01@example.com").one()
    case = CaseFile(
        student_id=student.id, problem_text="Identification is weak.",
        status="running", run_id="run-match-1",
        diagnosis=json.loads(json.dumps(DIAGNOSIS)), grounding_rate=1.0,
    )
    db.session.add(case)
    db.session.commit()
    return case


def test_search_professors_ranks_by_keyword(app: Flask) -> None:
    """Econometrics query ranks the econometrics professor first."""
    seed_database()
    hits = search_professors(["econometrics"])
    assert hits[0]["professor_id"] == 8
    assert hits[0]["score"] > hits[-1]["score"]
    dept = search_professors(["writing"], department="English Literature")
    assert dept and all(hit["department"] == "English Literature" for hit in dept)


def test_matching_tools_list_db_departments(app: Flask) -> None:
    """The search-tool filter names live DB departments, never a stale list."""
    from app.models import ProfessorProfile

    seed_database()
    tools = matching_tools()
    description = tools[0]["function"]["parameters"]["properties"][
        "department"
    ]["description"]
    assert "Agricultural Science" in description
    assert "Statistics" in description
    user = User(display_name="Dr. Xeno Guest", email="xeno@example.com",
                role="professor")
    user.set_password("password-123")
    db.session.add(user)
    db.session.flush()
    db.session.add(
        ProfessorProfile(
            user_id=user.id, department="Xenolinguistics",
            research_areas=[], bio="", availability={},
        )
    )
    db.session.commit()
    fresh = matching_tools()[0]["function"]["parameters"]["properties"][
        "department"
    ]["description"]
    assert "Xenolinguistics" in fresh


def test_register_accepts_seed_departments(app: Flask) -> None:
    """Registration admits every seeded department and rejects unknown ones."""
    seed_database()
    client = app.test_client()
    good = client.post(
        "/auth/register",
        data={
            "display_name": "New Physicist",
            "email": "physicist@example.com",
            "password": "password-123",
            "role": "professor",
            "department": "Physics",
        },
    )
    assert good.status_code in (302, 303)
    bad = client.post(
        "/auth/register",
        data={
            "display_name": "Atlantis Scholar",
            "email": "atlantis@example.com",
            "password": "password-123",
            "role": "professor",
            "department": "Atlantis Studies",
        },
    )
    assert bad.status_code == 400


def test_matching_eval_cases_cover_seed(app: Flask) -> None:
    """The committed 40 eval cases resolve against the 35 seeded professors."""
    from pathlib import Path

    from scripts.seed import PROFESSOR_SPECS

    seed_database()
    path = Path(app.root_path).parent / "eval" / "matching_cases.json"
    cases = json.loads(path.read_text(encoding="utf-8"))
    assert len(cases) == 40
    total = len(PROFESSOR_SPECS)
    seen: set[int] = set()
    for case in cases:
        for pid in case["acceptable_ids"]:
            assert 1 <= pid <= total
            seen.add(pid)
    assert seen == set(range(1, total + 1))
    fields = {case["diagnosis"]["field"] for case in cases}
    assert {"Physics", "Law", "Agricultural Science"} <= fields


def test_tool_search_clamps_limit_to_five(app: Flask) -> None:
    """The agent-facing search wrapper never returns more than 5 rows."""
    from app.services.matching import build_tool_map

    seed_database()
    results = build_tool_map()["search_professors"](
        {"keywords": ["e"], "limit": 50}
    )
    assert len(results) == 5


def test_profile_and_availability_tools(app: Flask) -> None:
    """Profile returns full rows; availability computes real future dates."""
    seed_database()
    profile = get_professor_profile(8)
    assert profile["department"] == "Economics"
    assert get_professor_profile(999) == {"error": "unknown professor_id: 999"}
    slots = check_availability(1, 14)
    assert slots["slots"], "Mon/Wed/Fri pattern must hit inside 14 days"
    first = date.fromisoformat(slots["slots"][0]["date"])
    assert first > date.today() and first.strftime("%A") in (
        "Monday", "Wednesday", "Friday",
    )
    assert check_availability(999) == {"error": "unknown professor_id: 999"}


def test_ranking_validator(app: Flask) -> None:
    """Valid rankings pass; bad ids, counts and empty fields fail."""
    seed_database()
    prof_ids = {user.id for user in User.query.filter_by(role="professor")}
    assert validate_ranking(make_ranking(12, 2, 1), prof_ids, {"g1", "g2"}) == []
    bad_prof = make_ranking(999, 2, 1)
    assert any("professor_id" in error for error in validate_ranking(bad_prof, prof_ids, {"g1", "g2"}))
    bad_gap = make_ranking(12, 2, 1)
    bad_gap["matches"][0]["reasons"][0]["gap_id"] = "g9"
    assert any("gap_id" in error for error in validate_ranking(bad_gap, prof_ids, {"g1", "g2"}))
    short = {"matches": make_ranking(12, 2, 1)["matches"][:2]}
    assert any("3 matches" in error for error in validate_ranking(short, prof_ids, {"g1", "g2"}))
    coerced = coerce_ranking({"matches": [{"professor_id": "x", "score": 500}]})
    assert coerced["matches"][0]["professor_id"] == -1
    assert coerced["matches"][0]["score"] == 100


def unordered_ranking() -> dict[str, Any]:
    """Valid ranking except scores ascend instead of descending."""
    ranking = make_ranking(12, 2, 1)
    for match, score in zip(ranking["matches"], (80, 90, 85)):
        match["score"] = score
    return ranking


def test_ranking_validator_rejects_bad_scores(app: Flask) -> None:
    """Scores must be integers 0-100 and strictly descending."""
    seed_database()
    prof_ids = {user.id for user in User.query.filter_by(role="professor")}
    gaps = {"g1", "g2"}
    unordered = unordered_ranking()
    errors = validate_ranking(unordered, prof_ids, gaps)
    assert any("strictly descending" in error for error in errors)
    assert only_order_errors(errors)
    non_int = make_ranking(12, 2, 1)
    non_int["matches"][0]["score"] = "90"
    assert any(
        "must be an integer" in error
        for error in validate_ranking(non_int, prof_ids, gaps)
    )
    out_of_range = make_ranking(12, 2, 1)
    out_of_range["matches"][1]["score"] = 101
    assert any(
        "outside 0-100" in error
        for error in validate_ranking(out_of_range, prof_ids, gaps)
    )
    mixed = unordered_ranking()
    mixed["matches"][0]["professor_id"] = 999
    assert not only_order_errors(validate_ranking(mixed, prof_ids, gaps))


def test_matching_sorts_and_flags_unordered_scores(app: Flask) -> None:
    """Order-only violations sort by score and persist flagged, not fatal."""
    case = seed_match_case()
    outcome = run_matching(
        case, "run-match-1",
        FakeMatchClient([unordered_ranking(), unordered_ranking()]),
        model="fake-match", effort=None,
    )
    assert [row.score for row in outcome.matches] == [90, 85, 80]
    assert [row.professor_id for row in outcome.matches] == [2, 1, 12]
    assert all(row.score_flagged for row in outcome.matches)
    assert RunEvent.query.filter_by(
        run_id="run-match-1", type="matching_scores_sorted"
    ).count() == 1
    assert RunEvent.query.filter_by(
        run_id="run-match-1", type="matching_validated"
    ).count() == 1


def test_summarize_tool_call(app: Flask) -> None:
    """Each tool renders a one-line human summary; unknown tools degrade."""
    seed_database()
    search_result = json_dumps_hits(search_professors(["econometrics"]))
    label = summarize_tool_call(
        "search_professors", {"keywords": ["econometrics"]}, search_result
    )
    assert label.startswith("Searched all departments for 'econometrics'")
    assert "Dr. Chiamaka Obi" in label
    profile_label = summarize_tool_call(
        "get_professor_profile", {"professor_id": 8},
        json.dumps(get_professor_profile(8)),
    )
    assert profile_label == (
        "Checked profile: Dr. Chiamaka Obi, Economics: "
        "Econometrics, Policy evaluation"
    )
    availability_label = summarize_tool_call(
        "check_availability", {"professor_id": 12, "days": 14},
        json.dumps(check_availability(12, 14)),
    )
    assert availability_label.startswith("Availability for professor 12: ")
    assert availability_label.endswith(" open days")
    assert summarize_tool_call("mystery_tool", {}, None) == "mystery_tool completed"
    assert summarize_tool_call(
        "get_professor_profile", {"professor_id": 999},
        json.dumps({"error": "unknown professor_id: 999"}),
    ) == "Checked profile 999: not found"


def json_dumps_hits(hits: list[dict[str, Any]]) -> str:
    """Serialize tool hits the way the tool loop stores results."""
    return json.dumps(hits)


def test_run_matching_persists_and_logs(app: Flask) -> None:
    """Fake run persists 3 ranked rows and logs tools in both tables."""
    case = seed_match_case()
    outcome = run_matching(
        case, "run-match-1", FakeMatchClient([make_ranking(12, 2, 1)]),
        model="fake-match", effort=None,
    )
    assert [row.rank for row in outcome.matches] == [1, 2, 3]
    assert outcome.matches[0].professor_id == 12
    assert MatchResult.query.filter_by(case_id=case.id).count() == 3
    assert ToolCallLog.query.filter_by(tool_name="search_professors").count() == 1
    types = [
        event.type
        for event in RunEvent.query.filter_by(run_id="run-match-1")
        .order_by(RunEvent.seq).all()
    ]
    assert types == [
        "matching_started", "tool_call", "matching_validated", "matching_finished",
    ]
    tool_event = RunEvent.query.filter_by(run_id="run-match-1", type="tool_call").one()
    assert tool_event.label.startswith(
        "Searched all departments for 'econometrics'"
    )
    assert "Dr. Chiamaka Obi" in tool_event.label
    assert tool_event.payload["tool"] == "search_professors"
    assert tool_event.payload["arguments"] == {"keywords": ["econometrics"]}
    assert "display_name" in (tool_event.payload["result"] or "")


def test_matching_retries_once_then_persists(app: Flask) -> None:
    """An invalid first ranking triggers exactly one retry."""
    case = seed_match_case()
    run_matching(
        case, "run-match-1",
        FakeMatchClient([make_ranking(999, 2, 1), make_ranking(12, 2, 1)]),
        model="fake-match", effort=None,
    )
    assert RunEvent.query.filter_by(
        run_id="run-match-1", type="matching_retry"
    ).count() == 1
    assert MatchResult.query.filter_by(case_id=case.id).count() == 3


def test_matching_twice_invalid_raises(app: Flask) -> None:
    """Two bad rankings fail the run instead of persisting junk."""
    import pytest

    case = seed_match_case()
    with pytest.raises(ValueError, match="ranking invalid after retry"):
        run_matching(
            case, "run-match-1",
            FakeMatchClient([make_ranking(999, 2, 1), make_ranking(998, 2, 1)]),
            model="fake-match", effort=None,
        )
    assert MatchResult.query.filter_by(case_id=case.id).count() == 0


def test_professors_directory_is_public(app: Flask) -> None:
    """Anonymous visitors can browse, search and filter professors."""
    seed_database()
    client = app.test_client()
    index = client.get("/professors")
    assert index.status_code == 200
    assert b"Sample profile" in index.data
    assert b"Prof. Adaeze Nwosu" in index.data
    assert "sample pricing" in index.get_data(as_text=True)
    filtered = client.get("/professors?q=econometrics&department=Economics")
    assert filtered.status_code == 200
    assert b"Dr. Chiamaka Obi" in filtered.data
    assert b"Prof. Adaeze Nwosu" not in filtered.data
    assert "\u20a618,000" in filtered.get_data(as_text=True)


def test_professor_detail_and_404(app: Flask) -> None:
    """Detail renders the profile; unknown ids 404."""
    seed_database()
    client = app.test_client()
    page = client.get("/professors/8")
    assert page.status_code == 200
    assert b"Econometrics" in page.data and b"Sample profile" in page.data
    assert b"Dr. Chiamaka Obi" in page.data  # /professors/8
    assert b"Senior Lecturer" in page.data
    assert "\u20a618,000" in page.get_data(as_text=True)
    assert client.get("/professors/999").status_code == 404


def test_case_detail_shows_match_cards(app: Flask) -> None:
    """Persisted matches render as cards with score rings and gap chips."""
    case = seed_match_case()
    case.status = "done"
    for rank, pid in enumerate((12, 2, 1), 1):
        db.session.add(
            MatchResult(
                case_id=case.id, professor_id=pid, rank=rank, score=90,
                reasons=[
                    {
                        "gap_id": "g1", "page": 1,
                        "quote": "results were significant",
                        "explanation": "Teaches inference.",
                    }
                ],
                caveats=["Busy term."], next_slot="2026-11-02 10:00 WAT",
            )
        )
    db.session.commit()
    import os

    client = app.test_client()
    client.post(
        "/auth/login",
        data={
            "email": "sample-student-01@example.com",
            "password": os.environ["SEED_DEMO_PASSWORD"],
        },
    )
    page = client.get(f"/cases/{case.id}")
    assert page.status_code == 200
    html = page.get_data(as_text=True)
    assert "Recommended professors" in html
    assert "Match score 90 out of 100" in html
    assert 'href="#gap-g1"' in html
    assert f"/cases/{case.id}/book/12" in html
    assert "₦22,000" in html


def test_full_pipeline_includes_matching(app: Flask, tmp_path) -> None:  # type: ignore[no-untyped-def]
    """End of pipeline: diagnosis plus persisted matches, status done."""
    from scripts.make_samples import PDF_PAGES, pdf_bytes
    from tests.test_parallel import RoutingFake, seed_parallel_case

    seed_database()
    case = seed_parallel_case(app, tmp_path)
    from app.services.diagnosis import run_case_pipeline

    run_case_pipeline(
        app, case.id, "run-full-1",
        chat_client=RoutingFake(), model="fake-diagnosis",
        match_client=FakeMatchClient([make_ranking(12, 2, 1)]),
        match_model="fake-match",
    )
    db.session.refresh(case)
    assert case.status == "done"
    assert MatchResult.query.filter_by(case_id=case.id).count() == 3
    types = [
        event.type
        for event in RunEvent.query.filter_by(run_id="run-full-1")
        .order_by(RunEvent.seq).all()
    ]
    assert "matching_finished" in types
    assert types.index("grounding_checked") < types.index("matching_started")


def test_matching_degrades_on_tool_budget(app: Flask) -> None:
    """A sweeping agent is capped at 12 calls; ranking uses the findings."""
    case = seed_match_case()

    class SweepingFake(FakeMatchClient):
        def chat(self, messages, tools=None, **kwargs):  # type: ignore[no-untyped-def]
            if kwargs.get("response_format") is not None:
                return ChatResult(text=json.dumps(self.rankings.pop(0)))
            self.calls += 1
            base = self.calls * 2
            return ChatResult(
                text="",
                tool_calls=tuple(
                    ToolCallRequest(
                        id=f"call_{base + offset}",
                        name="search_professors",
                        arguments={"keywords": ["statistics"]},
                    )
                    for offset in (0, 1)
                ),
                raw_assistant_message={"role": "assistant", "content": ""},
            )

    run_matching(
        case, "run-match-1", SweepingFake([make_ranking(12, 2, 1)]),
        model="fake-match", effort=None,
    )
    assert MatchResult.query.filter_by(case_id=case.id).count() == 3
    assert RunEvent.query.filter_by(
        run_id="run-match-1", type="tool_call"
    ).count() == 12
    exhausted = RunEvent.query.filter_by(
        run_id="run-match-1", type="tool_budget_exhausted"
    ).one()
    assert "12 findings" in exhausted.label


def test_student_case_routes_still_guarded(app: Flask) -> None:
    """Anonymous users bounce off case routes while professors stay public."""
    client = app.test_client()
    assert client.get("/cases/new").status_code == 302
    assert client.get("/professors").status_code == 200
    make_student()
    login(client, "intake@example.com")
    assert client.get("/professors").status_code == 200
