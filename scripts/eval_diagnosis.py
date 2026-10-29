"""Live diagnosis eval: planted-flaw recall, grounding, latency, tokens.

Usage: ``python -m scripts.eval_diagnosis [--mode both|parallel|single]
[--reps N]``. Runs the real pipeline over the sample excerpts and compares
found gaps with samples/expected.json. Writes docs/eval/diagnosis.md.
Never run by pytest. Needs META_API_KEY + META_MODEL_* in .env.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from flask import Flask

from app import create_app
from app.extensions import db
from app.models import CaseFile, Document, RunEvent, User
from app.services.diagnosis import normalize_text, run_case_pipeline

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ["thesis_excerpt_stats.pdf", "thesis_excerpt_methods.docx"]


@dataclass
class DiagnosisRep:
    """One eval repetition with its metrics."""

    sample: str
    mode: str
    rep: int
    strict_recall: float
    category_recall: float
    grounding_rate: float | None
    latency_s: float
    prompt_tokens: int
    completion_tokens: int
    gaps_found: int
    error: str = ""


def _temp_app(tmp: str):  # type: ignore[no-untyped-def]
    """App on a throwaway database for one eval repetition."""
    return create_app(
        {
            "TESTING": False,
            "SECRET_KEY": "eval-local-only",
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp}/eval.db",
            "UPLOAD_FOLDER": f"{tmp}/uploads",
        }
    )


def _flaw_found(
    flaw: dict[str, str], gaps: list[dict[str, Any]]
) -> tuple[bool, bool]:
    """Strict (quote cited) and category-level recall for one flaw."""
    quote = normalize_text(flaw["quote"])
    category_hit = any(gap.get("category") == flaw["category"] for gap in gaps)
    strict_hit = False
    for gap in gaps:
        haystacks = [normalize_text(gap.get("description", ""))]
        haystacks += [
            normalize_text(item.get("quote", ""))
            for item in gap.get("evidence", []) or []
        ]
        if any(quote in haystack for haystack in haystacks):
            strict_hit = True
    return strict_hit, category_hit


def _usage_for_run(run_id: str) -> tuple[int, int]:
    """Sum prompt/completion tokens from this run's event payloads."""
    prompt = completion = 0
    rows = RunEvent.query.filter_by(run_id=run_id).all()
    for row in rows:
        usage = (row.payload or {}).get("usage", {}) or {}
        prompt += int(usage.get("prompt_tokens", 0) or 0)
        completion += int(usage.get("completion_tokens", 0) or 0)
    return prompt, completion


def run_once(app: Flask, sample: str, mode: str, rep: int, flaws: list[dict[str, str]]) -> DiagnosisRep:
    """Run real diagnosis once (matching stubbed) and score expected flaws."""
    from unittest.mock import patch

    with app.app_context():
        db.create_all()
        user = User(display_name="Eval", email=f"eval-{rep}@example.com", role="student")
        db.session.add(user)
        db.session.flush()
        stored = ROOT / "samples" / sample
        document = Document(
            student_id=user.id, file_path=str(stored), extracted_text=""
        )
        db.session.add(document)
        db.session.flush()
        run_id = f"eval-{mode}-{rep}"
        case = CaseFile(
            student_id=user.id, document_id=document.id,
            problem_text="Evaluate my chapter and find every flaw.",
            status="running", run_id=run_id,
        )
        db.session.add(case)
        db.session.commit()
        case_id = case.id
    app.config["DIAGNOSIS_MODE"] = mode
    started = time.perf_counter()
    with patch("app.services.diagnosis._run_matching_phase", lambda *args: None):
        run_case_pipeline(app, case_id, run_id)
    latency = time.perf_counter() - started
    with app.app_context():
        case = db.session.get(CaseFile, case_id)
        if case is None or case.status != "done":
            return DiagnosisRep(sample, mode, rep, 0.0, 0.0, None, latency, 0, 0, 0, error="run failed")
        gaps = (case.diagnosis or {}).get("gaps", []) or []
        strict = sum(_flaw_found(flaw, gaps)[0] for flaw in flaws)
        category = sum(_flaw_found(flaw, gaps)[1] for flaw in flaws)
        prompt, completion = _usage_for_run(run_id)
        return DiagnosisRep(
            sample, mode, rep,
            strict_recall=strict / len(flaws),
            category_recall=category / len(flaws),
            grounding_rate=case.grounding_rate,
            latency_s=latency,
            prompt_tokens=prompt,
            completion_tokens=completion,
            gaps_found=len(gaps),
        )


def write_report(path: Path, reps: list[DiagnosisRep]) -> None:
    """Write the markdown report with per-rep rows and mode means."""
    lines = [
        "# Diagnosis eval",
        "",
        "Planted-flaw recall against samples/expected.json over live runs.",
        "Strict recall = expected quote cited in a gap; category recall = flaw",
        "category present among gaps.",
        "",
        "| sample | mode | rep | strict | category | grounding | latency | tokens | gaps |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for rep in reps:
        grounding = f"{rep.grounding_rate:.0%}" if rep.grounding_rate is not None else "n/a"
        lines.append(
            f"| {rep.sample} | {rep.mode} | {rep.rep} | {rep.strict_recall:.0%} | "
            f"{rep.category_recall:.0%} | {grounding} | {rep.latency_s:.1f}s | "
            f"{rep.prompt_tokens + rep.completion_tokens} | {rep.gaps_found} |"
        )
        if rep.error:
            lines.append(f"  error: {rep.error}")
    lines += ["", "## Means by mode", ""]
    for mode in ("parallel", "single"):
        group = [rep for rep in reps if rep.mode == mode and not rep.error]
        if not group:
            continue
        mean = lambda values: sum(values) / len(values)  # noqa: E731
        lines.append(
            f"- {mode}: strict {mean([r.strict_recall for r in group]):.0%}, "
            f"category {mean([r.category_recall for r in group]):.0%}, "
            f"latency {mean([r.latency_s for r in group]):.1f}s, "
            f"tokens {mean([r.prompt_tokens + r.completion_tokens for r in group]):.0f}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    """Run the eval matrix and write docs/eval/diagnosis.md."""
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description="Live diagnosis eval.")
    parser.add_argument("--mode", default="both", choices=("both", "parallel", "single"))
    parser.add_argument("--reps", type=int, default=3)
    args = parser.parse_args(argv)
    modes = ("parallel", "single") if args.mode == "both" else (args.mode,)
    expected = json.loads((ROOT / "samples" / "expected.json").read_text(encoding="utf-8"))
    total = len(SAMPLES) * len(modes) * args.reps
    print(f"diagnosis eval: {total} live runs (this takes a while)")
    reps: list[DiagnosisRep] = []
    failed = 0
    for sample in SAMPLES:
        flaws = expected[sample]["flaws"]
        for mode in modes:
            for rep in range(1, args.reps + 1):
                print(f"  {sample} {mode} rep {rep}/{args.reps} ...", flush=True)
                tmp = tempfile.mkdtemp(prefix="mentora-eval-")
                app = _temp_app(tmp)
                try:
                    result = run_once(app, sample, mode, rep, flaws)
                except Exception as exc:
                    result = DiagnosisRep(sample, mode, rep, 0, 0, None, 0, 0, 0, 0, error=str(exc))
                reps.append(result)
                if result.error:
                    failed += 1
                    print(f"    ERROR: {result.error}")
                else:
                    print(
                        f"    strict={result.strict_recall:.0%} "
                        f"category={result.category_recall:.0%} "
                        f"latency={result.latency_s:.1f}s"
                    )
    out = ROOT / "docs" / "eval" / "diagnosis.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    write_report(out, reps)
    print(f"wrote {out} ({failed} failed)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
