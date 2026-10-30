"""Live notes eval: action-item recall, fidelity rate, latency.

Usage: ``python -m scripts.eval_notes [--reps N] [--audio PATH]``. Runs the
real transcribe -> draft -> review chain over the sample clip and scores the
finalized action items against samples/audio/expected_notes.json. Writes
docs/eval/notes.md. Never run by pytest. Needs META_API_KEY + META_MODEL_*
in .env. Each rep spends one ASR call plus two chat calls.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from app.services.diagnosis import normalize_text
from app.services.meta_client import MetaSettings, OpenAICompatChatClient
from app.services.notes import apply_review, draft_notes, review_notes
from app.services.sessions import default_speaker_map
from app.services.transcription import transcribe_wav

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_AUDIO = ROOT / "samples" / "audio" / "session_sample_16k.wav"
EXPECTED = ROOT / "samples" / "audio" / "expected_notes.json"


@dataclass
class NotesRep:
    """One eval repetition with its metrics."""

    rep: int
    recall: float
    fidelity: float
    transcribe_s: float
    draft_s: float
    review_s: float
    turns: int
    items_found: int
    items_expected: int
    error: str = ""


def _item_found(expected: dict[str, Any], items: list[dict[str, Any]]) -> bool:
    """An expected item hits when one finalized item holds all its keywords."""
    keywords = [normalize_text(word) for word in expected.get("keywords", [])]
    for item in items:
        task = normalize_text(str(item.get("task", "")))
        if task and all(word in task for word in keywords):
            return True
    return False


def run_once(rep: int, audio: Path, expected_items: list[dict[str, Any]]) -> NotesRep:
    """Transcribe, draft, review with real models; score action-item recall."""
    settings = MetaSettings.from_env()
    if not settings.model_transcribe:
        raise RuntimeError("META_MODEL_TRANSCRIBE is not set")
    if not settings.model_agent or not settings.model_fast:
        raise RuntimeError("META_MODEL_AGENT and META_MODEL_FAST are required")
    started = time.perf_counter()
    transcript = transcribe_wav(
        audio,
        model=settings.model_transcribe,
        api_key=settings.api_key,
        base_url=settings.base_url,
        language_bias=["English"],
        keywords=[],  # no case diagnosis in the eval; nothing to leak in
    )
    transcribe_s = time.perf_counter() - started
    mapping = default_speaker_map(transcript.turns)
    turns = [
        {
            "speaker": turn.speaker,
            "name": mapping.get(turn.speaker, turn.speaker),
            "start_ms": turn.start_ms,
            "end_ms": turn.end_ms,
            "text": turn.text,
        }
        for turn in transcript.turns
    ]
    client = OpenAICompatChatClient(settings)
    started = time.perf_counter()
    draft = draft_notes(client, turns, settings.model_agent, settings.effort_agent)
    draft_s = time.perf_counter() - started
    started = time.perf_counter()
    verdicts = review_notes(
        client, draft, turns, settings.model_fast, settings.effort_fast
    )
    review_s = time.perf_counter() - started
    final_notes, fidelity = apply_review(draft, verdicts, len(turns))
    items = final_notes.get("action_items", []) or []
    found = sum(1 for want in expected_items if _item_found(want, items))
    return NotesRep(
        rep=rep,
        recall=found / len(expected_items) if expected_items else 1.0,
        fidelity=fidelity,
        transcribe_s=transcribe_s,
        draft_s=draft_s,
        review_s=review_s,
        turns=len(turns),
        items_found=found,
        items_expected=len(expected_items),
    )


def write_report(path: Path, audio_name: str, reps: list[NotesRep]) -> None:
    """Write the markdown report with per-rep rows and means."""
    lines = [
        "# Notes eval",
        "",
        f"Action-item recall against samples/audio/expected_notes.json over live",
        f"runs of {audio_name} (transcribe + draft + review; finalized items only).",
        "Recall = expected item whose keywords all appear in one finalized",
        "action item. Fidelity = reviewer mean (supported 1, partial 0.5).",
        "",
        "| rep | recall | fidelity | transcribe | draft | review | total | turns | items |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for rep in reps:
        total = rep.transcribe_s + rep.draft_s + rep.review_s
        lines.append(
            f"| {rep.rep} | {rep.recall:.0%} | {rep.fidelity:.0%} | "
            f"{rep.transcribe_s:.1f}s | {rep.draft_s:.1f}s | {rep.review_s:.1f}s | "
            f"{total:.1f}s | {rep.turns} | {rep.items_found}/{rep.items_expected} |"
        )
        if rep.error:
            lines.append(f"  error: {rep.error}")
    group = [rep for rep in reps if not rep.error]
    if group:
        mean = lambda values: sum(values) / len(values)  # noqa: E731
        lines += [
            "",
            "## Means",
            "",
            f"- recall {mean([r.recall for r in group]):.0%}, "
            f"fidelity {mean([r.fidelity for r in group]):.0%}, "
            f"transcribe {mean([r.transcribe_s for r in group]):.1f}s, "
            f"draft {mean([r.draft_s for r in group]):.1f}s, "
            f"review {mean([r.review_s for r in group]):.1f}s",
        ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    """Run the eval reps and write docs/eval/notes.md."""
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description="Live notes eval.")
    parser.add_argument("--reps", type=int, default=3)
    parser.add_argument("--audio", type=Path, default=DEFAULT_AUDIO)
    args = parser.parse_args(argv)
    if not args.audio.exists():
        print(f"missing audio: {args.audio}", file=sys.stderr)
        return 1
    if not EXPECTED.exists():
        print(f"missing expected notes: {EXPECTED}", file=sys.stderr)
        return 1
    expected = json.loads(EXPECTED.read_text(encoding="utf-8"))
    key = args.audio.name
    if key not in expected:
        print(f"no expected entry for {key} in {EXPECTED}", file=sys.stderr)
        return 1
    expected_items = expected[key]["action_items"]
    print(f"notes eval: {args.reps} live reps over {key} (spends API credit)")
    reps: list[NotesRep] = []
    failed = 0
    for rep in range(1, args.reps + 1):
        print(f"  rep {rep}/{args.reps} ...", flush=True)
        try:
            result = run_once(rep, args.audio, expected_items)
        except Exception as exc:
            result = NotesRep(rep, 0.0, 0.0, 0.0, 0.0, 0.0, 0, 0, len(expected_items), error=str(exc))
        reps.append(result)
        if result.error:
            failed += 1
            print(f"    ERROR: {result.error}")
        else:
            total = result.transcribe_s + result.draft_s + result.review_s
            print(
                f"    recall={result.recall:.0%} fidelity={result.fidelity:.0%} "
                f"total={total:.1f}s turns={result.turns}"
            )
    out = ROOT / "docs" / "eval" / "notes.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    write_report(out, key, reps)
    print(f"wrote {out} ({failed} failed)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
