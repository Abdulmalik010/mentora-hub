"""Session notes: structured drafting plus a citation reviewer.

The notes agent (Wonder, structured output) drafts summary, key points,
concepts, decisions, action items, resources, open questions and a next
session suggestion; every item cites supporting turn indexes. A separate
reviewer call (Spark, cheap entailment check) labels each item supported,
partial or unsupported against the cited turns. Unsupported items are
dropped, partial ones flagged, and the fidelity rate is stored on the
SessionRecord. Unlabeled items and out-of-range citations fail safe to
partial (flagged) rather than vanishing silently.
"""
from __future__ import annotations

from typing import Any

from .meta_client import ChatClient, complete_json

NOTES_SYSTEM_PROMPT = (
    "You are Mentora's session scribe. Turn the transcript into study "
    "notes a student can act on. Write concisely; never invent facts not "
    "in the turns. EVERY item must cite the supporting turn indexes in "
    "'turns' (0-based into the provided turn list). Owners for action "
    "items are 'student' or 'professor'."
)

REVIEW_SYSTEM_PROMPT = (
    "You are Mentora's notes auditor. For each drafted item, check it "
    "against its cited turns only: 'supported' (fully stated), 'partial' "
    "(stated with extra or hedged detail), 'unsupported' (missing or "
    "contradicted). Judge strictly; cite nothing beyond the given turns."
)

NOTES_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "key_points": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "turns": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["text", "turns"],
                "additionalProperties": False,
            },
        },
        "concepts_explained": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "term": {"type": "string"},
                    "explanation": {"type": "string"},
                    "turns": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["term", "explanation", "turns"],
                "additionalProperties": False,
            },
        },
        "decisions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "turns": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["text", "turns"],
                "additionalProperties": False,
            },
        },
        "action_items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "owner": {"type": "string"},
                    "task": {"type": "string"},
                    "due": {"type": "string"},
                    "turns": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["owner", "task", "turns"],
                "additionalProperties": False,
            },
        },
        "resources": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "turns": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["text", "turns"],
                "additionalProperties": False,
            },
        },
        "open_questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "turns": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["text", "turns"],
                "additionalProperties": False,
            },
        },
        "next_session_suggestion": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "turns": {"type": "array", "items": {"type": "integer"}},
            },
            "required": ["text", "turns"],
            "additionalProperties": False,
        },
    },
    "required": [
        "summary", "key_points", "concepts_explained", "decisions",
        "action_items", "resources", "open_questions",
        "next_session_suggestion",
    ],
    "additionalProperties": False,
}

REVIEW_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "verdicts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "section": {"type": "string"},
                    "index": {"type": "integer"},
                    "label": {"type": "string"},
                    "note": {"type": "string"},
                },
                "required": ["section", "index", "label"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["verdicts"],
    "additionalProperties": False,
}

# Reviewable sections: plural lists plus the single next-session suggestion.
REVIEWABLE_SECTIONS: tuple[str, ...] = (
    "key_points",
    "concepts_explained",
    "decisions",
    "action_items",
    "resources",
    "open_questions",
    "next_session_suggestion",
)

_VERDICT_SCORE = {"supported": 1.0, "partial": 0.5, "unsupported": 0.0}


def format_turns_for_prompt(turns: list[dict[str, Any]]) -> str:
    """Numbered turns with speaker names for the drafting prompt."""
    lines = []
    for index, turn in enumerate(turns):
        lines.append(f"[{index}] {turn.get('name', '?')}: {turn.get('text', '')}")
    return "\n".join(lines)


def draft_notes(
    chat_client: ChatClient,
    turns: list[dict[str, Any]],
    model: str,
    effort: str | None,
) -> dict[str, Any]:
    """Draft structured notes from mapped turns (Wonder)."""
    return complete_json(
        chat_client,
        [
            {"role": "system", "content": NOTES_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Session transcript (cite 0-based turn indexes):\n"
                    f"{format_turns_for_prompt(turns)}"
                ),
            },
        ],
        model=model, schema=NOTES_SCHEMA, name="SessionNotes", effort=effort,
    )


def review_notes(
    chat_client: ChatClient,
    draft: dict[str, Any],
    turns: list[dict[str, Any]],
    model: str,
    effort: str | None,
) -> dict[str, Any]:
    """Label each drafted item against its cited turns (Spark)."""
    return complete_json(
        chat_client,
        [
            {"role": "system", "content": REVIEW_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Draft to audit (JSON):\n"
                    f"{_compact_json(draft)}\n\n"
                    "Transcript:\n"
                    f"{format_turns_for_prompt(turns)}"
                ),
            },
        ],
        model=model, schema=REVIEW_SCHEMA, name="NotesReview", effort=effort,
    )


def _compact_json(data: dict[str, Any]) -> str:
    """Deterministic short JSON for prompts."""
    import json

    return json.dumps(data, sort_keys=True, ensure_ascii=False)


def _iter_items(draft: dict[str, Any]) -> list[tuple[str, int, dict[str, Any]]]:
    """Reviewable items as (section, index, payload) triples."""
    items: list[tuple[str, int, dict[str, Any]]] = []
    for section in REVIEWABLE_SECTIONS:
        payload = draft.get(section)
        if section == "next_session_suggestion":
            if isinstance(payload, dict):
                items.append((section, 0, payload))
            continue
        if isinstance(payload, list):
            for index, item in enumerate(payload):
                if isinstance(item, dict):
                    items.append((section, index, item))
    return items


def apply_review(
    draft: dict[str, Any], verdicts_raw: dict[str, Any], turn_count: int
) -> tuple[dict[str, Any], float]:
    """Drop unsupported items, flag partial ones, score fidelity.

    Unknown labels and missing verdicts fail safe to partial (flagged);
    out-of-range or empty turn citations force unsupported (dropped).
    Fidelity is mean item score (supported 1, partial 0.5); 1.0 when the
    draft holds no reviewable items.
    """
    verdicts: dict[tuple[str, int], dict[str, Any]] = {}
    raw_list = verdicts_raw.get("verdicts", [])
    if isinstance(raw_list, list):
        for verdict in raw_list:
            if not isinstance(verdict, dict):
                continue
            section = str(verdict.get("section", ""))
            index = verdict.get("index")
            if section in REVIEWABLE_SECTIONS and isinstance(index, int):
                verdicts[(section, index)] = verdict
    final: dict[str, Any] = {"summary": draft.get("summary", "")}
    scores: list[float] = []
    for section, index, item in _iter_items(draft):
        refs = item.get("turns", [])
        valid_refs = (
            isinstance(refs, list)
            and len(refs) > 0
            and all(
                isinstance(ref, int) and 0 <= ref < turn_count for ref in refs
            )
        )
        verdict = verdicts.get((section, index), {})
        label = str(verdict.get("label", "partial"))
        if label not in _VERDICT_SCORE:
            label = "partial"
        if not valid_refs:
            label = "unsupported"
        scores.append(_VERDICT_SCORE[label])
        if label == "unsupported":
            continue
        kept = dict(item)
        if label == "partial":
            kept["partial"] = True
            kept["partial_note"] = str(
                verdict.get("note", "")
                or "partly supported by the cited turns"
            )[:300]
        if section == "next_session_suggestion":
            final[section] = kept
        else:
            final.setdefault(section, []).append(kept)
    for section in REVIEWABLE_SECTIONS:
        if section != "next_session_suggestion":
            final.setdefault(section, [])
    fidelity = sum(scores) / len(scores) if scores else 1.0
    return final, round(fidelity, 3)


def memory_note_content(final_notes: dict[str, Any], when: str) -> str:
    """Concise progress facts for the student's memory (not used in briefs)."""
    actions = final_notes.get("action_items", []) or []
    mine = [item for item in actions if str(item.get("owner", "")).lower() == "student"]
    lines = [f"Session {when}: {str(final_notes.get('summary', ''))[:280]}"]
    if mine:
        lines.append("Student actions: " + "; ".join(
            str(item.get("task", ""))[:120] for item in mine[:5]
        ))
    suggestion = final_notes.get("next_session_suggestion")
    if isinstance(suggestion, dict) and suggestion.get("text"):
        lines.append(f"Next: {str(suggestion['text'])[:200]}")
    return "\n".join(lines)
