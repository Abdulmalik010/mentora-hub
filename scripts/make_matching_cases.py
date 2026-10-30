"""Generate 40 deterministic matching-eval cases from the seed specs.

Run from the project root: ``python -m scripts.make_matching_cases``.
Writes ``eval/matching_cases.json``. Professor ids are the deterministic
fresh-seed ids (spec order, 1-based); eval_matching.py seeds a fresh database
so the ids always resolve.
"""
from __future__ import annotations

import json
from pathlib import Path

from scripts.seed import PROFESSOR_SPECS

EVAL_DIR = Path(__file__).resolve().parent.parent / "eval"

DEPT_CATEGORY = {
    "Statistics": "statistics",
    "Computer Science": "data",
    "Economics": "methodology",
    "English Literature": "writing",
    "Biology": "data",
    "Chemistry": "methodology",
    "Physics": "data",
    "Mathematics": "statistics",
    "Civil Engineering": "methodology",
    "Electrical Engineering": "data",
    "Law": "literature",
    "Education": "theory",
    "Psychology": "statistics",
    "Business Administration": "methodology",
    "Agricultural Science": "data",
}


def _diagnosis(
    field: str, keywords: list[str], categories: list[str], blurb: str
) -> dict[str, object]:
    """Minimal valid diagnosis shape with one gap per category."""
    gaps = [
        {
            "category": category,
            "description": f"Synthetic {category} gap needing {keywords[0]}.",
            "severity": 3 if index == 0 else 2,
            "evidence": [{"page": 1, "quote": f"synthetic eval quote {index}"}],
        }
        for index, category in enumerate(categories)
    ]
    return {
        "field": field,
        "level": "masters",
        "core_problem": blurb,
        "gaps": gaps,
        "what_student_already_tried": [],
        "questions_for_professor": [],
        "expertise_keywords": keywords,
        "confidence": 0.8,
    }


def build_cases() -> list[dict[str, object]]:
    """One single-specialty case per spec plus 5 cross-specialty mixes."""
    cases: list[dict[str, object]] = []
    total = len(PROFESSOR_SPECS)
    for index, (dept, areas, blurb) in enumerate(PROFESSOR_SPECS, 1):
        category = DEPT_CATEGORY[dept]
        cases.append(
            {
                "id": f"spec-{index:02d}",
                "diagnosis": _diagnosis(
                    dept, list(areas), [category, "writing"], blurb
                ),
                "acceptable_ids": [index],
            }
        )
    for mix in range(5):
        first = (mix * 7) % total
        second = (mix * 11 + 13) % total
        if second == first:
            second = (second + 1) % total
        spec_a, spec_b = PROFESSOR_SPECS[first], PROFESSOR_SPECS[second]
        keywords = list(spec_a[1]) + list(spec_b[1])
        cases.append(
            {
                "id": f"mix-{mix:02d}",
                "diagnosis": _diagnosis(
                    spec_a[0],
                    keywords,
                    [DEPT_CATEGORY[spec_a[0]], DEPT_CATEGORY[spec_b[0]]],
                    f"{spec_a[2]} Also: {spec_b[2]}",
                ),
                "acceptable_ids": sorted([first + 1, second + 1]),
            }
        )
    return cases


def main() -> None:
    """Write eval/matching_cases.json."""
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    cases = build_cases()
    with open(EVAL_DIR / "matching_cases.json", "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(cases, indent=2) + "\n")
    print(f"Wrote {len(cases)} cases to {EVAL_DIR / 'matching_cases.json'}")


if __name__ == "__main__":
    main()
