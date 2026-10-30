"""Clarifying questions: one round between diagnosis and matching.

After diagnosis, a cheap structured call asks 0-3 questions whose answers
would change the match (budget, deadline, preferred times, session goal).
Answers become constraints: budget filters hard (relaxed with an
explanation when empty), preferred times boost ranking, goal and deadline
join the ranking prompt. Free-text answers are always allowed.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from ..extensions import db
from ..models import ClarificationQA, ProfessorProfile
from .diagnosis import log_event
from .meta_client import ChatClient, complete_json
from .slots import availability_windows

QUESTION_KEYS = ("budget", "deadline", "times", "goal")
QUESTION_TYPES = ("choice", "text")
MAX_QUESTIONS = 3
TIMES_BOOST = 2

CLARIFY_SYSTEM_PROMPT = (
    "You are Mentora's intake assistant. Read the diagnosis and ask at most "
    "3 short clarifying questions, ONLY where the answer would change which "
    "professor to recommend. Allowed topics, each at most once: budget (max "
    "naira per session), deadline (when the session must happen), times "
    "(preferred days/times), goal (what the student wants from the session). "
    "Prefer zero questions when the diagnosis already determines the match. "
    "Use type 'choice' with 3-4 concrete options whenever possible; use "
    "'text' only for the session goal. Every question needs a one-line "
    "'why' naming the gap ids it serves."
)

QUESTIONS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                    "type": {"type": "string"},
                    "question": {"type": "string"},
                    "options": {
                        "type": "array", "items": {"type": "string"},
                    },
                    "why": {"type": "string"},
                    "gap_ids": {
                        "type": "array", "items": {"type": "string"},
                    },
                },
                "required": [
                    "key", "type", "question", "options", "why", "gap_ids",
                ],
                "additionalProperties": False,
            },
        },
    },
    "required": ["questions"],
    "additionalProperties": False,
}

# Chip label (normalized) to (weekday names, hour range) for the times boost.
TIMES_PREFERENCES: dict[str, tuple[frozenset[str], tuple[int, int]]] = {
    "weekday mornings": (
        frozenset({"Monday", "Tuesday", "Wednesday", "Thursday", "Friday"}),
        (8, 12),
    ),
    "weekday afternoons": (
        frozenset({"Monday", "Tuesday", "Wednesday", "Thursday", "Friday"}),
        (12, 17),
    ),
    "weekday evenings": (
        frozenset({"Monday", "Tuesday", "Wednesday", "Thursday", "Friday"}),
        (17, 21),
    ),
    "weekends": (frozenset({"Saturday", "Sunday"}), (8, 20)),
}

_BUDGET_NUMBER = re.compile(r"(\d[\d,]*)\s*([kKmM]?)")
_NO_LIMIT = ("no limit", "flexible", "any", "none", "skip")


def validate_questions(
    raw: dict[str, Any], gap_id_set: set[str]
) -> list[dict[str, Any]]:
    """Keep the valid questions (at most 3); drop anything malformed."""
    valid: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    for item in raw.get("questions", []) or []:
        if len(valid) >= MAX_QUESTIONS:
            break
        if not isinstance(item, dict):
            continue
        key = str(item.get("key", ""))
        qtype = str(item.get("type", ""))
        question = str(item.get("question", "")).strip()
        if (
            key not in QUESTION_KEYS
            or qtype not in QUESTION_TYPES
            or not question
            or key in seen_keys
        ):
            continue
        options = [
            str(option).strip()
            for option in item.get("options", []) or []
            if str(option).strip()
        ]
        if qtype == "choice" and not 3 <= len(options) <= 4:
            continue
        gap_ids = [
            str(gid) for gid in item.get("gap_ids", []) or [] if gid in gap_id_set
        ]
        seen_keys.add(key)
        valid.append(
            {
                "key": key,
                "type": qtype,
                "question": question[:500],
                "options": options[:4],
                "why": str(item.get("why", ""))[:500],
                "gap_ids": gap_ids,
            }
        )
    return valid


def generate_questions(
    chat_client: ChatClient,
    diagnosis: dict[str, Any],
    gap_ids: list[str],
    model: str,
    effort: str | None,
) -> list[dict[str, Any]]:
    """Ask the model for 0-3 validated clarifying questions."""
    gaps = diagnosis.get("gaps", []) or []
    gap_block = "\n".join(
        f"{gid}: [{gap.get('category')}] {gap.get('description')}"
        for gid, gap in zip(gap_ids, gaps)
    )
    raw = complete_json(
        chat_client,
        [
            {"role": "system", "content": CLARIFY_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Diagnosis to clarify:\n"
                    f"Field: {diagnosis.get('field', '?')} | "
                    f"Level: {diagnosis.get('level', '?')}\n"
                    f"Core problem: {diagnosis.get('core_problem', '')}\n"
                    f"Gaps:\n{gap_block}\n"
                    f"Keywords: "
                    f"{', '.join(diagnosis.get('expertise_keywords', []) or [])}"
                ),
            },
        ],
        model=model, schema=QUESTIONS_SCHEMA, name="ClarifyingQuestions",
        effort=effort,
    )
    return validate_questions(raw, set(gap_ids))


def persist_questions(
    case_id: int, questions: list[dict[str, Any]]
) -> list[ClarificationQA]:
    """Store generated questions as unanswered rows (caller commits)."""
    rows = [
        ClarificationQA(
            case_id=case_id,
            question_key=item["key"],
            question=item["question"],
            qtype=item["type"],
            options=item["options"],
            why=item["why"],
            gap_ids=item["gap_ids"],
        )
        for item in questions
    ]
    db.session.add_all(rows)
    return rows


def load_answers(case_id: int) -> dict[str, str]:
    """Answered questions as {key: answer} (skips stay absent)."""
    rows = ClarificationQA.query.filter_by(case_id=case_id).all()
    return {
        row.question_key: row.answer
        for row in rows
        if row.answer and row.answer.strip()
    }


def parse_budget_cap(answer: str) -> int | None:
    """Naira cap from a budget answer; None means no limit."""
    text = answer.strip().lower().replace("₦", "").replace("naira", "")
    if not text or any(word in text for word in _NO_LIMIT):
        return None
    match = _BUDGET_NUMBER.search(text)
    if not match:
        return None
    amount = int(match.group(1).replace(",", ""))
    suffix = match.group(2).lower()
    if suffix == "k":
        amount *= 1_000
    elif suffix == "m":
        amount *= 1_000_000
    return amount if amount > 0 else None


def times_overlap(availability: dict[str, Any] | None, answer: str) -> bool:
    """True when the weekly pattern overlaps the preferred times answer."""
    preference = TIMES_PREFERENCES.get(answer.strip().lower())
    if preference is None:
        return False
    days, (start_hour, end_hour) = preference
    wanted = set((availability or {}).get("days", []) or [])
    if not (wanted & set(days)):
        return False
    return any(
        opens.hour < end_hour and closes.hour > start_hour
        for opens, closes in availability_windows(availability)
    )


@dataclass
class ConstrainedCandidates:
    """Candidates after answers, plus display strings and prompt block."""

    candidates: list[dict[str, Any]]
    filters_applied: list[str]
    relaxed: list[str]
    prompt_block: str


def apply_answer_constraints(
    candidates: list[dict[str, Any]], answers: dict[str, str]
) -> ConstrainedCandidates:
    """Filter/boost candidates from answers; budget relaxes when empty.

    Budget (whole naira) drops candidates above the cap — free/unknown
    rates always pass — but restores everyone with an explanation when
    nothing fits. Preferred times boost overlapping candidates. The goal
    and deadline join the ranking prompt verbatim.
    """
    filters_applied: list[str] = []
    relaxed: list[str] = []
    prompt_lines: list[str] = []
    remaining = list(candidates)
    budget_answer = (answers.get("budget") or "").strip()
    cap = parse_budget_cap(budget_answer) if budget_answer else None
    if cap is not None:
        affordable = [
            hit
            for hit in remaining
            if hit.get("rate") is None or float(hit["rate"]) <= cap
        ]
        label = f"Budget ≤ ₦{cap:,}/session"
        if affordable:
            remaining = affordable
            filters_applied.append(label)
        else:
            relaxed.append(
                f"{label} relaxed: no candidates fit, showing all."
            )
    elif budget_answer:
        prompt_lines.append(f"Student budget note: {budget_answer}.")
    times_answer = (answers.get("times") or "").strip()
    if times_answer:
        profiles = {
            hit["professor_id"]: ProfessorProfile.query.filter_by(
                user_id=hit["professor_id"]
            ).first()
            for hit in remaining
        }
        boosted = [
            hit["professor_id"]
            for hit in remaining
            if (profile := profiles.get(hit["professor_id"])) is not None
            and profile.availability
            and times_overlap(profile.availability, times_answer)
        ]
        if boosted:
            for hit in remaining:
                if hit["professor_id"] in boosted:
                    hit["score"] = int(hit.get("score", 0)) + TIMES_BOOST
            remaining.sort(key=lambda hit: (-hit["score"], hit["professor_id"]))
            filters_applied.append(f"Preferred times: {times_answer}")
        prompt_lines.append(
            f"Student prefers {times_answer}; prefer overlapping availability."
        )
    goal_answer = (answers.get("goal") or "").strip()
    if goal_answer:
        prompt_lines.append(f"Student's session goal: {goal_answer}.")
        filters_applied.append("Session goal considered in ranking")
    deadline_answer = (answers.get("deadline") or "").strip()
    if deadline_answer:
        prompt_lines.append(f"Student needs a session: {deadline_answer}.")
        filters_applied.append(f"Deadline: {deadline_answer}")
    prompt_block = (
        "Student constraints from clarifying answers:\n" + "\n".join(prompt_lines)
        if prompt_lines
        else ""
    )
    return ConstrainedCandidates(
        candidates=remaining,
        filters_applied=filters_applied,
        relaxed=relaxed,
        prompt_block=prompt_block,
    )


def log_questions_ready(run_id: str, count: int) -> None:
    """Timeline event marking the pause for student answers."""
    log_event(
        run_id, "questions_ready",
        f"Mentora needs {count} quick answer{'s' if count != 1 else ''} "
        "before matching",
        payload={"count": count},
    )
