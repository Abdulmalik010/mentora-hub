"""Evidence-based professor matching: tools, ranking, validation.

The matching agent (Muse Wonder) researches professors through tools, then a
structured call produces the top-3 ranking. Rankings are validated in code
(professor ids exist, cited gap ids exist, exactly 3 matches) with one retry.
"""
from __future__ import annotations

import json
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from .diagnosis import json_dumps, log_event, normalize_text
from ..extensions import db
from ..models import CaseFile, MatchResult, ProfessorProfile, User
from .slots import availability_windows, format_wat, generate_slots
from .meta_client import (
    ChatClient,
    ChatResult,
    ToolBudgetExceeded,
    ToolCallRecord,
    complete_json,
    log_tool_call_to_db,
    run_tool_loop,
)

MATCH_MAX_ITERATIONS = 3
MATCH_MAX_TOOL_CALLS = 12
MATCH_TIMEOUT_S = 180.0
MATCH_MAX_ATTEMPTS = 5
FAST_CANDIDATE_LIMIT = 8
FIELD_BOOST = 4

SCORE_ANCHORS = (
    "Score each professor 0-100 (integers, strictly descending: "
    "match 1 > match 2 > match 3). Anchors: 90+ covers every "
    "high-severity gap with direct specialty overlap; 75-89 covers most "
    "gaps or the top gap very well; 60-74 partially relevant, useful "
    "caveats; below 60 weak fit, only when no better candidate exists."
)

MATCH_SYSTEM_PROMPT = (
    "You are Mentora's matching researcher. Find the best professors for a "
    "student's diagnosed gaps using ONLY the provided tools. You have at "
    "most 3 turns: BATCH every independent tool call into a single turn "
    "(one search plus several profile reads together), inspect at most 3 "
    "finalist profiles, check availability for finalists only. Stop calling "
    "tools as soon as you have 3 strong candidates; do NOT sweep the whole "
    "directory. End with a short shortlist summary naming professor ids."
)

def matching_tools() -> list[dict[str, Any]]:
    """Tool schemas with the department filter drawn from the database.

    Built per call (not a module constant) so self-registered departments
    and seed changes reach the agent without a restart.
    """
    from .profiles import department_choices

    departments = ", ".join(department_choices())
    return [
        {
            "type": "function",
            "function": {
                "name": "search_professors",
                "description": (
                    "Keyword search over professor departments, research "
                    "areas and bios. Returns professor user ids with match "
                    "scores."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "keywords": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": (
                                "Expertise keywords from the diagnosis."
                            ),
                        },
                        "department": {
                            "type": "string",
                            "description": (
                                "Optional department filter; one of: "
                                f"{departments}."
                            ),
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Max results (1-5, default 5).",
                        },
                    },
                    "required": ["keywords"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_professor_profile",
                "description": "Full profile for one professor user id.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "professor_id": {"type": "integer"},
                    },
                    "required": ["professor_id"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "check_availability",
                "description": "Upcoming open slots for one professor user id.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "professor_id": {"type": "integer"},
                        "days": {
                            "type": "integer",
                            "description": (
                                "Look-ahead window in days (default 14)."
                            ),
                        },
                    },
                    "required": ["professor_id"],
                    "additionalProperties": False,
                },
            },
        },
    ]

RANKING_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "matches": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "professor_id": {"type": "integer"},
                    "score": {"type": "integer", "minimum": 0, "maximum": 100},
                    "reasons": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "gap_id": {"type": "string"},
                                "page": {"type": "integer", "minimum": 1},
                                "quote": {"type": "string"},
                                "explanation": {"type": "string"},
                            },
                            "required": ["gap_id", "page", "quote", "explanation"],
                            "additionalProperties": False,
                        },
                    },
                    "caveats": {"type": "array", "items": {"type": "string"}},
                    "next_slot": {"type": "string"},
                },
                "required": ["professor_id", "score", "reasons", "caveats", "next_slot"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["matches"],
    "additionalProperties": False,
}


def search_professors(
    keywords: list[str],
    department: str | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Score professors by keyword overlap; research areas weigh most."""
    terms = [normalize_text(keyword) for keyword in keywords if keyword.strip()]
    limit = min(50, max(1, limit))
    scored: list[tuple[int, dict[str, Any]]] = []
    profiles = ProfessorProfile.query.all()
    for profile in profiles:
        if profile.accepting_new is False:
            continue
        if department and profile.department.lower() != department.lower():
            continue
        areas = normalize_text(" ".join(profile.research_areas or []))
        bio = normalize_text(profile.bio or "")
        dept = normalize_text(profile.department or "")
        score = 0
        for term in terms:
            if term in areas:
                score += 3
            if term in dept:
                score += 2
            if term in bio:
                score += 1
        user = db.session.get(User, profile.user_id)
        scored.append(
            (
                score,
                {
                    "professor_id": profile.user_id,
                    "display_name": user.display_name if user else "?",
                    "department": profile.department,
                    "research_areas": profile.research_areas,
                    "bio_snippet": (profile.bio or "")[:160],
                    "is_sample": bool(user and user.is_sample),
                    "rate": profile.rate,
                    "score": score,
                },
            )
        )
    scored.sort(key=lambda item: (-item[0], item[1]["professor_id"]))
    return [entry for _, entry in scored[:limit]]


def get_professor_profile(professor_id: int) -> dict[str, Any]:
    """Full profile row, or an error dict for unknown ids."""
    user = db.session.get(User, professor_id)
    profile = ProfessorProfile.query.filter_by(user_id=professor_id).first()
    if user is None or profile is None or user.role != "professor":
        return {"error": f"unknown professor_id: {professor_id}"}
    return {
        "professor_id": user.id,
        "display_name": user.display_name,
        "department": profile.department,
        "research_areas": profile.research_areas,
        "bio": profile.bio,
        "rate": profile.rate,
        "timezone": profile.timezone,
        "availability": profile.availability,
    }


def check_availability(professor_id: int, days: int = 14) -> dict[str, Any]:
    """Upcoming open dates computed from the weekly availability pattern."""
    profile = ProfessorProfile.query.filter_by(user_id=professor_id).first()
    if profile is None:
        return {"error": f"unknown professor_id: {professor_id}"}
    availability = profile.availability or {}
    open_days = availability.get("days", []) or []
    spans = ", ".join(
        f"{opens.strftime('%H:%M')}-{closes.strftime('%H:%M')}"
        for opens, closes in availability_windows(availability)
    )
    hours = f"{spans} WAT" if spans else ""
    window = min(60, max(1, days))
    today = date.today()
    slots = []
    for offset in range(1, window + 1):
        day = today + timedelta(days=offset)
        if day.strftime("%A") in open_days:
            slots.append({"date": day.isoformat(), "hours": hours})
    return {"professor_id": professor_id, "hours": hours, "slots": slots}


def retrieve_candidates(
    keywords: list[str],
    field: str | None = None,
    limit: int = FAST_CANDIDATE_LIMIT,
) -> list[dict[str, Any]]:
    """Fast-path retrieval: keyword search plus a same-field boost.

    Scores come from :func:`search_professors` (areas weigh most); hits in
    the diagnosis field gain FIELD_BOOST so department fit breaks ties.
    Deterministic; opt-outs stay excluded via the shared search.
    """
    hits = search_professors(keywords, limit=50)
    if field:
        wanted = field.strip().lower()
        for hit in hits:
            if str(hit.get("department", "")).lower() == wanted:
                hit["score"] = int(hit.get("score", 0)) + FIELD_BOOST
        hits.sort(key=lambda hit: (-hit["score"], hit["professor_id"]))
    return hits[: max(1, limit)]


def first_open_slot(profile: ProfessorProfile) -> str:
    """Next bookable slot in code (``""`` when no pattern yields one)."""
    slots = generate_slots(profile.availability or {})
    if not slots:
        return ""
    return format_wat(slots[0].start_naive_utc)


def build_tool_map() -> dict[str, Callable[[dict[str, Any]], Any]]:
    """Tool name to implementation, with defensive argument handling."""

    def _search(args: dict[str, Any]) -> Any:
        keywords = args.get("keywords", []) or []
        limit = min(5, max(1, int(args.get("limit", 5))))
        return search_professors(
            [str(k) for k in keywords if isinstance(k, str)],
            args.get("department"),
            limit,
        )

    def _profile(args: dict[str, Any]) -> Any:
        return get_professor_profile(int(args["professor_id"]))

    def _availability(args: dict[str, Any]) -> Any:
        return check_availability(
            int(args["professor_id"]), int(args.get("days", 14))
        )

    return {
        "search_professors": _search,
        "get_professor_profile": _profile,
        "check_availability": _availability,
    }


def coerce_ranking(raw: dict[str, Any]) -> dict[str, Any]:
    """Defensively normalize a model ranking (schema is not trusted blindly)."""
    matches = []
    for item in raw.get("matches", []) or []:
        if not isinstance(item, dict):
            continue
        try:
            professor_id = int(item.get("professor_id", -1))
        except (TypeError, ValueError):
            professor_id = -1
        try:
            score = int(item.get("score", 0))
        except (TypeError, ValueError):
            score = 0
        reasons = []
        for reason in item.get("reasons", []) or []:
            if not isinstance(reason, dict):
                continue
            try:
                page = max(1, int(reason.get("page", 1)))
            except (TypeError, ValueError):
                page = 1
            reasons.append(
                {
                    "gap_id": str(reason.get("gap_id", "")),
                    "page": page,
                    "quote": str(reason.get("quote", "")),
                    "explanation": str(reason.get("explanation", "")),
                }
            )
        caveats = item.get("caveats", []) or []
        matches.append(
            {
                "professor_id": professor_id,
                "score": min(100, max(0, score)),
                "reasons": reasons,
                "caveats": [str(c) for c in caveats if isinstance(c, str)],
                "next_slot": str(item.get("next_slot", "")),
            }
        )
    return {"matches": matches}


ORDER_ERROR_PREFIX = "scores "

def validate_ranking(
    ranking: dict[str, Any],
    professor_ids: set[int],
    gap_ids: set[str],
) -> list[str]:
    """Check a ranking; return human-readable errors (empty means valid)."""
    errors = []
    matches = ranking.get("matches", [])
    if len(matches) != 3:
        errors.append(f"expected exactly 3 matches, got {len(matches)}")
    scores: list[int] = []
    for position, match in enumerate(matches, 1):
        score = match.get("score")
        if isinstance(score, bool) or not isinstance(score, int):
            errors.append(f"match {position}: score must be an integer")
        elif not 0 <= score <= 100:
            errors.append(f"match {position}: score {score} outside 0-100")
        else:
            scores.append(score)
        if match.get("professor_id") not in professor_ids:
            errors.append(
                f"match {position}: unknown professor_id {match.get('professor_id')!r}"
            )
        if not match.get("reasons"):
            errors.append(f"match {position}: at least one reason is required")
        for reason in match.get("reasons", []):
            if reason.get("gap_id") not in gap_ids:
                errors.append(
                    f"match {position}: unknown gap_id {reason.get('gap_id')!r}"
                )
            if not reason.get("quote", "").strip():
                errors.append(f"match {position}: empty evidence quote")
        if not match.get("next_slot", "").strip():
            errors.append(f"match {position}: next_slot is required")
    if len(scores) == len(matches) and len(matches) > 1:
        for first, second in zip(scores, scores[1:]):
            if first <= second:
                errors.append(
                    f"scores not strictly descending: {scores} "
                    "(rank order must follow score order)"
                )
                break
    return errors


def only_order_errors(errors: list[str]) -> bool:
    """True when every error is a score-ordering violation (safe to sort)."""
    return bool(errors) and all(
        error.startswith(ORDER_ERROR_PREFIX) for error in errors
    )


@dataclass(frozen=True)
class MatchOutcome:
    """Persisted matches plus cost telemetry."""

    matches: list[MatchResult]
    latency_s: float
    usage: dict[str, Any]
    quote_grounding_rate: float | None


class _MatchRecorder:
    """ChatClient wrapper capturing results for usage reporting."""

    def __init__(self, inner: ChatClient) -> None:
        self._inner = inner
        self.results: list[ChatResult] = []

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: Sequence[dict[str, Any]] | None = None,
        *,
        model: str,
        response_format: dict[str, Any] | None = None,
        effort: str | None = None,
    ) -> ChatResult:
        """Delegate the call and record the normalized result."""
        result = self._inner.chat(
            messages, tools, model=model, response_format=response_format,
            effort=effort,
        )
        self.results.append(result)
        return result


def _summed_usage(results: Sequence[ChatResult]) -> dict[str, int]:
    """Aggregate token usage across results."""
    prompt = completion = 0
    for result in results:
        usage = result.usage or {}
        prompt += int(usage.get("prompt_tokens", 0) or 0)
        completion += int(usage.get("completion_tokens", 0) or 0)
    return {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": prompt + completion,
    }


def _parse_tool_result(result: str | None) -> Any:
    """Best-effort JSON decode of a tool result (None when not JSON)."""
    if not result:
        return None
    try:
        return json.loads(result)
    except (TypeError, ValueError):
        return None


def summarize_tool_call(
    tool_name: str, arguments: dict[str, Any], result: str | None
) -> str:
    """One human-readable line per tool call for the visible timeline."""
    if tool_name == "search_professors":
        keywords = [
            str(item)
            for item in arguments.get("keywords", []) or []
            if isinstance(item, str)
        ]
        scope = arguments.get("department") or "all departments"
        hits = _parse_tool_result(result)
        names = (
            [str(hit.get("display_name", "?")) for hit in hits]
            if isinstance(hits, list)
            else []
        )
        top = f" (top: {', '.join(names[:2])})" if names else " (no hits)"
        return (
            f"Searched {scope} for '{', '.join(keywords[:4])}': "
            f"{len(names)} hits{top}"
        )
    if tool_name == "get_professor_profile":
        profile = _parse_tool_result(result)
        if isinstance(profile, dict) and "error" not in profile:
            areas = ", ".join((profile.get("research_areas") or [])[:3])
            return (
                f"Checked profile: {profile.get('display_name', '?')}, "
                f"{profile.get('department', '?')}: {areas}"
            )
        return f"Checked profile {arguments.get('professor_id')}: not found"
    if tool_name == "check_availability":
        availability = _parse_tool_result(result)
        if isinstance(availability, dict) and "error" not in availability:
            slots = availability.get("slots") or []
            return (
                f"Availability for professor "
                f"{availability.get('professor_id')}: {len(slots)} open days"
            )
        return f"Availability check for {arguments.get('professor_id')}: not found"
    return f"{tool_name} completed"


def _bridge_tool_log(
    run_id: str, records: list[ToolCallRecord]
) -> Callable[[ToolCallRecord], None]:
    """Log every tool call to ToolCallLog AND the visible timeline."""

    def _log(record: ToolCallRecord) -> None:
        records.append(record)
        log_tool_call_to_db(record)
        label = summarize_tool_call(
            record.tool_name, record.arguments or {}, record.result
        )[:195]
        log_event(
            run_id, "tool_call", label, status=record.status,
            payload={
                "tool": record.tool_name,
                "arguments": record.arguments,
                "result": record.result,
            },
        )

    return _log


def _rank_top3(
    recording: _MatchRecorder,
    gap_block: str,
    context_block: str,
    model: str,
    effort: str | None,
    run_id: str,
    professor_ids: set[int],
    gap_id_set: set[str],
) -> tuple[dict[str, Any], bool]:
    """One ranking call with validation, one retry, order-sort fallback.

    Returns the ranking plus whether scores were sorted-and-flagged. Raises
    ValueError when the ranking is still invalid after the retry.
    """
    ranking: dict[str, Any] = {}
    errors: list[str] = []
    for attempt in (1, 2):
        feedback = (
            ""
            if attempt == 1
            else f"\nYour previous output was INVALID: {'; '.join(errors)}. Fix it."
        )
        raw = complete_json(
            recording,
            [
                {"role": "system", "content": MATCH_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "RANKING PASS: rank the top 3 professors as JSON.\n"
                        f"{SCORE_ANCHORS}\n"
                        f"Gaps (cite these ids):\n{gap_block}\n"
                        f"{context_block}\n"
                        f"{feedback}"
                    ),
                },
            ],
            model=model, schema=RANKING_SCHEMA, name="ProfessorRanking",
            effort=effort,
        )
        ranking = coerce_ranking(raw)
        errors = validate_ranking(ranking, professor_ids, gap_id_set)
        if not errors:
            break
        if attempt == 1:
            log_event(
                run_id, "matching_retry",
                f"Ranking invalid ({errors[0]}); retrying once",
                status="error",
            )
    score_flagged = False
    if errors:
        if only_order_errors(errors):
            score_flagged = True
            ranking["matches"].sort(
                key=lambda item: item["score"], reverse=True
            )
            log_event(
                run_id, "matching_scores_sorted",
                f"Scores out of order after retry; sorted and flagged ({errors[0]})",
                status="error",
            )
        else:
            raise ValueError(f"ranking invalid after retry: {'; '.join(errors)}")
    return ranking, score_flagged


MIN_SNAPSHOT_REUSE = 3


def _attach_profiles(
    candidates: list[dict[str, Any]],
    run_id: str,
    records: list[ToolCallRecord],
) -> list[dict[str, Any]]:
    """Fetch each candidate's profile, logging the reads as tool calls."""
    log_call = _bridge_tool_log(run_id, records)
    tools = build_tool_map()
    for candidate in candidates:
        profile_started = time.perf_counter()
        profile = tools["get_professor_profile"](
            {"professor_id": candidate["professor_id"]}
        )
        log_call(
            ToolCallRecord(
                tool_name="get_professor_profile",
                arguments={"professor_id": candidate["professor_id"]},
                result=json_dumps(profile),
                status="ok",
                error=None,
                duration_ms=(time.perf_counter() - profile_started) * 1000.0,
                run_id=run_id,
            )
        )
        candidate["profile"] = profile
    return candidates


def log_speculative_search(
    run_id: str,
    keywords: list[str],
    field: str | None,
    records: list[ToolCallRecord] | None = None,
) -> list[dict[str, Any]]:
    """Run retrieval now, logging the search as a real tool call.

    Used both by fast matching and by the clarification phase, which
    retrieves while the student answers so the post-answer ranking needs
    no new search.
    """
    search_started = time.perf_counter()
    candidates = retrieve_candidates(keywords, field)
    _bridge_tool_log(run_id, records if records is not None else [])(
        ToolCallRecord(
            tool_name="search_professors",
            arguments={
                "keywords": keywords, "department": field,
                "limit": FAST_CANDIDATE_LIMIT,
            },
            result=json_dumps(candidates),
            status="ok",
            error=None,
            duration_ms=(time.perf_counter() - search_started) * 1000.0,
            run_id=run_id,
        )
    )
    return candidates


def _fast_candidates(
    keywords: list[str],
    field: str | None,
    run_id: str,
    records: list[ToolCallRecord],
) -> list[dict[str, Any]]:
    """Retrieve top candidates, logging each step as a real tool call.

    One search_professors call plus one get_professor_profile call per
    candidate flow through the same bridge as the agentic loop, so the
    timeline shows genuine operations with measured durations.
    """
    candidates = log_speculative_search(run_id, keywords, field, records)
    return _attach_profiles(candidates, run_id, records)


def _snapshot_candidates(
    snapshot: dict[str, Any],
    run_id: str,
    records: list[ToolCallRecord],
) -> list[dict[str, Any]]:
    """Reuse speculative candidates, dropping dead or opted-out ids.

    Falls back to a fresh logged search when fewer than 3 survive, so
    the ranker never starves because the directory changed mid-answer.
    """
    wanted = [
        (int(item["professor_id"]), int(item.get("score", 0)))
        for item in snapshot.get("candidates", []) or []
        if isinstance(item, dict) and "professor_id" in item
    ]
    live: list[dict[str, Any]] = []
    for professor_id, score in wanted:
        user = db.session.get(User, professor_id)
        profile = ProfessorProfile.query.filter_by(user_id=professor_id).first()
        if (
            user is None
            or profile is None
            or user.role != "professor"
            or profile.accepting_new is False
        ):
            continue
        live.append({"professor_id": professor_id, "score": score})
    if len(live) >= MIN_SNAPSHOT_REUSE:
        log_event(
            run_id, "candidates_reused",
            f"Reusing {len(live)} pre-answer candidates (no new search)",
            payload={"count": len(live)},
        )
        return _attach_profiles(live, run_id, records)
    keywords = [str(item) for item in snapshot.get("keywords", []) or []]
    return _fast_candidates(keywords, snapshot.get("field"), run_id, records)


def _candidate_block(candidates: list[dict[str, Any]]) -> str:
    """Full candidate profiles as ranking context (ids the model must use)."""
    lines = []
    for candidate in candidates:
        profile = candidate.get("profile") or {}
        areas = ", ".join((profile.get("research_areas") or [])[:6])
        bio = str(profile.get("bio") or "")[:300]
        rate = profile.get("rate")
        lines.append(
            f"- id {candidate['professor_id']}: "
            f"{profile.get('display_name', '?')} "
            f"({profile.get('department', '?')}; score {candidate['score']})\n"
            f"  areas: {areas}\n"
            f"  rate: {rate if rate is not None else 'on request'} naira\n"
            f"  bio: {bio}"
        )
    return "\n".join(lines) or "(no candidates retrieved)"


def run_matching(
    case: CaseFile,
    run_id: str,
    chat_client: ChatClient,
    model: str,
    effort: str | None,
    source_text: str = "",
    *,
    mode: str = "fast",
    rank_model: str | None = None,
    rank_effort: str | None = None,
    snapshot: dict[str, Any] | None = None,
) -> MatchOutcome:
    """Match professors in fast or agentic mode; persist top 3.

    Fast (default): code retrieval over the top candidates plus one
    ranking call (``rank_model`` or ``model``), with next slots computed
    in code for the final 3. A ``snapshot`` from speculative retrieval
    skips the search (dead/opted-out ids still re-validated). Agentic:
    the 3-turn batched tool loop, with model-provided slots. Assumes a
    Flask app context. Raises on failure so the caller can mark the case.
    """
    if mode not in ("fast", "agentic"):
        raise ValueError(f"MATCH_MODE must be fast|agentic (got {mode!r})")
    diagnosis = case.diagnosis or {}
    gaps = diagnosis.get("gaps", []) or []
    if not gaps:
        raise ValueError("no grounded gaps to match on")
    gap_ids = [f"g{index}" for index, _ in enumerate(gaps, 1)]
    gap_block = "\n".join(
        f"{gid}: [{gap.get('category')}] {gap.get('description')}"
        for gid, gap in zip(gap_ids, gaps)
    )
    log_event(
        run_id, "matching_started",
        f"Matching started ({model}, {mode})",
        payload={"model": model, "mode": mode},
    )
    recording = _MatchRecorder(chat_client)
    started = time.perf_counter()
    records: list[ToolCallRecord] = []
    if mode == "agentic":
        research = (
            "RANKING RESEARCH: find professors for this diagnosis.\n"
            f"Field: {diagnosis.get('field', '?')} | "
            f"Level: {diagnosis.get('level', '?')}\n"
            f"Core problem: {diagnosis.get('core_problem', '')}\n"
            f"Gaps:\n{gap_block}\n"
            f"Keywords: {', '.join(diagnosis.get('expertise_keywords', []) or [])}"
        )
        try:
            final_text = run_tool_loop(
                recording,
                [
                    {"role": "system", "content": MATCH_SYSTEM_PROMPT},
                    {"role": "user", "content": research},
                ],
                matching_tools(),
                build_tool_map(),
                model=model,
                log_tool_call=_bridge_tool_log(run_id, records),
                max_iterations=MATCH_MAX_ITERATIONS,
                max_tool_calls=MATCH_MAX_TOOL_CALLS,
                run_id=run_id,
                effort=effort,
            )
        except ToolBudgetExceeded:
            if not records:
                raise
            final_text = ""
            log_event(
                run_id, "tool_budget_exhausted",
                f"Tool budget reached; ranking from {len(records)} findings",
                payload={"findings": len(records)},
            )
        findings = "\n".join(
            f"- {record.tool_name}({json_dumps(record.arguments)}) "
            f"=> {(record.result or '')[:300]}"
            for record in records
            if record.status == "ok"
        ) or "(no successful tool calls)"
        context_block = (
            f"Research findings:\n{findings}\n"
            f"Agent summary:\n{final_text or '(none; loop hit budget)'}"
        )
        agentic_constraint = (snapshot or {}).get("constraint_block", "")
        if agentic_constraint:
            context_block += f"\n{agentic_constraint}"
        ranking_model, ranking_effort = model, effort
    else:
        if snapshot is not None:
            candidates = _snapshot_candidates(snapshot, run_id, records)
        else:
            keywords = [
                str(item)
                for item in diagnosis.get("expertise_keywords", []) or []
                if item
            ]
            candidates = _fast_candidates(
                keywords, diagnosis.get("field"), run_id, records
            )
        context_block = (
            "Candidates (rank ONLY these ids):\n"
            f"{_candidate_block(candidates)}"
        )
        constraint = (snapshot or {}).get("constraint_block", "")
        if constraint:
            context_block += f"\n{constraint}"
        ranking_model = rank_model or model
        ranking_effort = rank_effort if rank_effort is not None else effort
    professor_ids = {
        row[0] for row in db.session.query(User.id).filter_by(role="professor")
    }
    gap_id_set = set(gap_ids)
    ranking, score_flagged = _rank_top3(
        recording, gap_block, context_block, ranking_model, ranking_effort,
        run_id, professor_ids, gap_id_set,
    )
    if mode == "fast":
        computed = 0
        for match in ranking["matches"]:
            profile = ProfessorProfile.query.filter_by(
                user_id=match["professor_id"]
            ).first()
            slot = first_open_slot(profile) if profile is not None else ""
            if slot:
                match["next_slot"] = slot
                computed += 1
        log_event(
            run_id, "slots_computed",
            f"Next slots computed in code for {computed}/3 finalists",
            payload={"computed": computed},
        )
    log_event(run_id, "matching_validated", "Ranking validated: 3 matches")
    rows = []
    for rank, match in enumerate(ranking["matches"], 1):
        row = MatchResult(
            case_id=case.id,
            professor_id=match["professor_id"],
            rank=rank,
            score=match["score"],
            score_flagged=score_flagged,
            reasons=match["reasons"],
            caveats=match["caveats"],
            next_slot=match["next_slot"],
        )
        db.session.add(row)
        rows.append(row)
    db.session.commit()
    latency = time.perf_counter() - started
    usage = _summed_usage(recording.results)
    quote_rate: float | None = None
    if source_text.strip():
        source = normalize_text(source_text)
        quotes = [
            normalize_text(reason.get("quote", ""))
            for match in ranking["matches"]
            for reason in match.get("reasons", [])
        ]
        checked = [quote for quote in quotes if quote]
        quote_rate = (
            sum(1 for quote in checked if quote in source) / len(checked)
            if checked
            else 1.0
        )
    log_event(
        run_id, "matching_finished",
        f"Matching finished in {latency:.1f}s "
        f"(top: {', '.join(str(m['professor_id']) for m in ranking['matches'])})",
        payload={
            "latency_s": round(latency, 2), "usage": usage,
            "quote_grounding_rate": quote_rate,
        },
    )
    return MatchOutcome(
        matches=rows, latency_s=latency, usage=usage,
        quote_grounding_rate=quote_rate,
    )


def get_case_matches(case_id: int) -> list[MatchResult]:
    """Match rows for a case, ordered by rank."""
    return (
        MatchResult.query.filter_by(case_id=case_id)
        .order_by(MatchResult.rank)
        .all()
    )
