"""Live matching eval: top-1/top-3 accuracy, latency, tokens.

Usage: ``python -m scripts.eval_matching [--limit N]``. Seeds a fresh
database, runs the real Wonder matching agent over eval/matching_cases.json,
and writes docs/eval/matching.md. Never run by pytest. Needs META_API_KEY,
META_MODEL_AGENT and SEED_DEMO_PASSWORD in .env. A full run is 40 Wonder
calls; start with --limit 3.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from app import create_app
from app.extensions import db
from app.models import CaseFile, User
from app.services.matching import MATCH_TIMEOUT_S, run_matching
from app.services.meta_client import MetaSettings, OpenAICompatChatClient
from scripts.seed import seed_database

ROOT = Path(__file__).resolve().parent.parent


@dataclass
class MatchingRep:
    """One eval case with its outcome."""

    case_id: str
    top1: bool
    top3: bool
    ranked_ids: list[int]
    latency_s: float
    prompt_tokens: int
    completion_tokens: int
    error: str = ""


def main(argv: list[str] | None = None) -> int:
    """Run matching over eval cases and write docs/eval/matching.md."""
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description="Live matching eval.")
    parser.add_argument("--limit", type=int, default=0, help="0 = all cases")
    args = parser.parse_args(argv)
    if not os.environ.get("SEED_DEMO_PASSWORD"):
        print("SEED_DEMO_PASSWORD must be set (eval seeds a fresh database)")
        return 1
    cases = json.loads((ROOT / "eval" / "matching_cases.json").read_text(encoding="utf-8"))
    if args.limit > 0:
        cases = cases[: args.limit]
    print(f"matching eval: {len(cases)} live Wonder runs (this takes a while)")

    tmp = tempfile.mkdtemp(prefix="mentora-evalmatch-")
    app = create_app(
        {
            "TESTING": False,
            "SECRET_KEY": "eval-local-only",
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp}/eval.db",
            "UPLOAD_FOLDER": f"{tmp}/uploads",
        }
    )
    with app.app_context():
        db.create_all()
        seed_database()
        student = User.query.filter_by(email="sample-student-01@example.com").one()
        settings = MetaSettings.from_env()
        from dataclasses import replace

        settings = replace(settings, timeout_s=MATCH_TIMEOUT_S)
        client = OpenAICompatChatClient(settings)
        model = settings.model_agent
        effort = settings.effort_agent
        reps: list[MatchingRep] = []
        failed = 0
        for position, entry in enumerate(cases, 1):
            print(f"  {entry['id']} ({position}/{len(cases)}) ...", flush=True)
            case = CaseFile(
                student_id=student.id,
                problem_text="Eval matching case.",
                status="running",
                run_id=f"eval-match-{entry['id']}",
                diagnosis=entry["diagnosis"],
                grounding_rate=1.0,
            )
            db.session.add(case)
            db.session.commit()
            acceptable = set(entry["acceptable_ids"])
            try:
                outcome = run_matching(
                    case, case.run_id, client, model, effort  # type: ignore[arg-type]
                )
                ranked = [row.professor_id for row in outcome.matches]
                reps.append(
                    MatchingRep(
                        case_id=entry["id"],
                        top1=ranked[0] in acceptable,
                        top3=any(pid in acceptable for pid in ranked),
                        ranked_ids=ranked,
                        latency_s=outcome.latency_s,
                        prompt_tokens=outcome.usage.get("prompt_tokens", 0),
                        completion_tokens=outcome.usage.get("completion_tokens", 0),
                    )
                )
                print(f"    ranked={ranked} top1={reps[-1].top1} top3={reps[-1].top3}")
            except Exception as exc:
                failed += 1
                reps.append(
                    MatchingRep(entry["id"], False, False, [], 0.0, 0, 0, error=str(exc))
                )
                print(f"    ERROR: {exc}")
    out = ROOT / "docs" / "eval" / "matching.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Matching eval",
        "",
        f"Top-1/top-3 accuracy over {len(reps)} live Wonder runs.",
        "",
        "| case | top-1 | top-3 | ranked ids | latency | tokens |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for rep in reps:
        lines.append(
            f"| {rep.case_id} | {'yes' if rep.top1 else 'no'} | "
            f"{'yes' if rep.top3 else 'no'} | "
            f"{','.join(str(pid) for pid in rep.ranked_ids) or '-'} | "
            f"{rep.latency_s:.1f}s | {rep.prompt_tokens + rep.completion_tokens} |"
        )
        if rep.error:
            lines.append(f"  error: {rep.error}")
    ok = [rep for rep in reps if not rep.error]
    if ok:
        lines += [
            "",
            f"top-1 accuracy: {sum(r.top1 for r in ok) / len(ok):.0%} "
            f"({sum(r.top1 for r in ok)}/{len(ok)})",
            f"top-3 accuracy: {sum(r.top3 for r in ok) / len(ok):.0%} "
            f"({sum(r.top3 for r in ok)}/{len(ok)})",
        ]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {out} ({failed} failed)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
