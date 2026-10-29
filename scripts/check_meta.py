"""Live Meta Model API smoke test (real calls, real credits; never run by pytest).

Usage: ``python -m scripts.check_meta [--audio path/to/file.wav] [--effort EF]``

``--effort`` sets reasoning effort for the chat checks: default (omit the
parameter), minimal, low, medium or high.

Verifies, with one minimal call each:
  (a) META_MODEL_AGENT: a tool-call round trip with a trivial local tool.
  (b) META_MODEL_FAST: a structured-JSON call.
  (c) META_MODEL_AGENT: native PDF file input vs extracted text, using a
      synthetic PDF generated in-memory (DOCX is answered from the docs'
      supported-MIME table, with no live call).
  (d) META_MODEL_TRANSCRIBE: transcribes --audio (DIARIZATION) and reports
      whether speaker labels are returned; skipped without --audio.

Prints model, latency and token usage per call. Never prints secrets.
Exit code 0 when every applicable check passes, 1 otherwise, with the exact
error of each failure. No provider swapping, no workarounds.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from app.services.meta_client import (
    ChatClient,
    ChatResult,
    MetaClientError,
    MetaSettings,
    OpenAICompatChatClient,
    ToolCallRecord,
    complete_json,
    run_tool_loop,
)

PDF_TEXT = "Mentora synthetic check document. The quick brown fox jumps over."
PDF_EXPECTED_PHRASE = "quick brown fox"
TRANSCRIBE_PATH = "/asr/transcribe"  # documented under /docs/speech-to-text


@dataclass
class CheckOutcome:
    """Result of one live check, with printable detail lines."""

    name: str
    passed: bool
    detail: list[str] = field(default_factory=list)


class _RecordingClient:
    """ChatClient wrapper capturing every result for usage reporting."""

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


def _usage_line(results: Sequence[ChatResult]) -> str:
    """Aggregate token usage across results as 'in=X out=Y total=Z'."""
    prompt = completion = 0
    for result in results:
        usage = result.usage or {}
        prompt += int(usage.get("prompt_tokens", 0) or 0)
        completion += int(usage.get("completion_tokens", 0) or 0)
    if prompt == 0 and completion == 0:
        return "usage=n/a"
    return f"usage=in:{prompt} out:{completion} total:{prompt + completion}"


def _check_tool_roundtrip(
    client: ChatClient, model: str, effort: str | None
) -> CheckOutcome:
    """One tool call (add 214 + 186) through run_tool_loop; expect 400."""
    outcome = CheckOutcome(name="(a) agent tool round trip", passed=False)
    if not model:
        outcome.detail.append("META_MODEL_AGENT is not set")
        return outcome
    records: list[ToolCallRecord] = []
    tools = [
        {
            "type": "function",
            "function": {
                "name": "add",
                "description": "Add two integers and return the sum.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "a": {"type": "integer"},
                        "b": {"type": "integer"},
                    },
                    "required": ["a", "b"],
                    "additionalProperties": False,
                },
            },
        }
    ]
    recording = _RecordingClient(client)
    started = time.perf_counter()
    try:
        final = run_tool_loop(
            recording,
            [{"role": "user", "content": "Use the add tool to compute 214 + 186."}],
            tools,
            {"add": lambda args: int(args["a"]) + int(args["b"])},
            model=model,
            log_tool_call=records.append,
            max_iterations=4,
            effort=effort,
        )
    except Exception as exc:
        outcome.detail.append(f"{type(exc).__name__}: {exc}")
        return outcome
    latency = time.perf_counter() - started
    outcome.detail.append(f"model={model} latency={latency:.2f}s {_usage_line(recording.results)}")
    for record in records:
        outcome.detail.append(
            f"tool={record.tool_name} args={json.dumps(record.arguments)} "
            f"status={record.status} result={record.result}"
        )
    outcome.detail.append(f"final={final.strip()[:120]!r}")
    outcome.passed = "400" in final
    if not outcome.passed:
        outcome.detail.append("expected '400' in the final answer")
    return outcome


def _check_structured_json(
    client: ChatClient, model: str, effort: str | None
) -> CheckOutcome:
    """One schema-conforming JSON call on the fast model."""
    outcome = CheckOutcome(name="(b) fast structured JSON", passed=False)
    if not model:
        outcome.detail.append("META_MODEL_FAST is not set")
        return outcome
    recording = _RecordingClient(client)
    started = time.perf_counter()
    try:
        parsed = complete_json(
            recording,
            [{"role": "user", "content": "My regression residuals fan out. Reply per schema."}],
            model=model,
            name="GapHint",
            effort=effort,
            schema={
                "type": "object",
                "properties": {
                    "topic": {"type": "string"},
                    "level": {"type": "string"},
                },
                "required": ["topic", "level"],
                "additionalProperties": False,
            },
        )
    except Exception as exc:
        outcome.detail.append(f"{type(exc).__name__}: {exc}")
        return outcome
    latency = time.perf_counter() - started
    outcome.detail.append(f"model={model} latency={latency:.2f}s {_usage_line(recording.results)}")
    outcome.detail.append(f"parsed={json.dumps(parsed)[:200]}")
    outcome.passed = isinstance(parsed.get("topic"), str) and isinstance(
        parsed.get("level"), str
    )
    if not outcome.passed:
        outcome.detail.append("expected string fields 'topic' and 'level'")
    return outcome


def _synthetic_pdf_bytes(text: str) -> bytes:
    """Build a minimal one-page PDF with computed xref offsets."""
    safe = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    content = f"BT /F1 18 Tf 72 720 Td ({safe}) Tj ET".encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
        b" /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode("latin-1") + body + b"\nendobj\n"
    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("latin-1")
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode("latin-1")
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_at}\n%%EOF\n"
    ).encode("latin-1")
    return bytes(out)


def _check_pdf_input(
    client: ChatClient, model: str, effort: str | None
) -> CheckOutcome:
    """Native PDF file block vs extracted text on the agent model."""
    outcome = CheckOutcome(name="(c) agent PDF input", passed=False)
    if not model:
        outcome.detail.append("META_MODEL_AGENT is not set")
        return outcome
    pdf_data = (
        "data:application/pdf;base64,"
        + base64.b64encode(_synthetic_pdf_bytes(PDF_TEXT)).decode()
    )
    question = "Reply with the animal phrase from this document, nothing else."
    recording = _RecordingClient(client)
    try:
        started = time.perf_counter()
        native = recording.chat(
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": question},
                        {
                            "type": "file",
                            "file": {"filename": "synthetic-check.pdf", "file_data": pdf_data},
                        },
                    ],
                }
            ],
            model=model,
            effort=effort,
        )
        native_latency = time.perf_counter() - started
        started = time.perf_counter()
        extracted = recording.chat(
            [
                {
                    "role": "user",
                    "content": f"{question}\n\nDocument text:\n{PDF_TEXT}",
                }
            ],
            model=model,
            effort=effort,
        )
        extracted_latency = time.perf_counter() - started
    except Exception as exc:
        outcome.detail.append(f"{type(exc).__name__}: {exc}")
        return outcome
    outcome.detail.append(
        f"model={model} native_latency={native_latency:.2f}s "
        f"text_latency={extracted_latency:.2f}s {_usage_line(recording.results)}"
    )
    outcome.detail.append(f"native_reply={native.text.strip()[:160]!r}")
    outcome.detail.append(f"text_reply={extracted.text.strip()[:160]!r}")
    outcome.detail.append(
        "DOCX: absent from the docs' supported-MIME table "
        "(image/audio/video/PDF/text only), so DOCX needs the extracted-text path."
    )
    native_ok = PDF_EXPECTED_PHRASE in native.text.lower()
    text_ok = PDF_EXPECTED_PHRASE in extracted.text.lower()
    outcome.passed = native_ok and text_ok
    if not outcome.passed:
        outcome.detail.append(
            f"expected {PDF_EXPECTED_PHRASE!r} in both replies "
            f"(native={native_ok}, text={text_ok})"
        )
    return outcome


def _find_speaker_labels(node: Any, found: set[str]) -> None:
    """Collect speaker label strings from a nested transcribe response."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key in ("speaker", "speakerLabel", "label") and isinstance(value, str):
                found.add(value)
            else:
                _find_speaker_labels(value, found)
    elif isinstance(node, list):
        for item in node:
            _find_speaker_labels(item, found)


def _check_transcribe(settings: MetaSettings, audio: Path | None) -> CheckOutcome:
    """Transcribe --audio with DIARIZATION; report speaker labels."""
    outcome = CheckOutcome(name="(d) voice transcribe", passed=False)
    if audio is None:
        outcome.passed = True
        outcome.detail.append("skipped (no --audio given)")
        return outcome
    model = settings.model_transcribe
    if not model:
        outcome.detail.append("META_MODEL_TRANSCRIBE is not set")
        return outcome
    if not audio.is_file():
        outcome.detail.append(f"audio file not found: {audio}")
        return outcome
    if audio.suffix.lower() != ".wav":
        outcome.detail.append(f"only .wav is supported by this check, got {audio.suffix}")
        return outcome
    import httpx

    url = settings.base_url.rstrip("/") + TRANSCRIBE_PATH
    session_id = f"mentora-check-{uuid.uuid4().hex[:8]}"
    request_part = json.dumps(
        {"mode": "DIARIZATION", "model": model, "audioEncoding": "WAV"}
    )
    started = time.perf_counter()
    try:
        response = httpx.post(
            url,
            params={"sessionId": session_id},
            files={
                "request": ("request", request_part, "application/json"),
                "audio": (audio.name, audio.read_bytes(), "audio/wav"),
            },
            headers={"Authorization": f"Bearer {settings.api_key}"},
            timeout=120.0,
        )
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        outcome.detail.append(f"{type(exc).__name__}: {exc}")
        return outcome
    latency = time.perf_counter() - started
    turns = data.get("turns", []) if isinstance(data, dict) else []
    labels: set[str] = set()
    _find_speaker_labels(data, labels)
    outcome.detail.append(f"model={model} latency={latency:.2f}s usage=n/a (audio)")
    outcome.detail.append(f"turns={len(turns)} speaker_labels={sorted(labels) or 'none'}")
    first_text = ""
    if turns and isinstance(turns[0], dict):
        first_text = str(turns[0].get("transcript", ""))[:200]
    outcome.detail.append(f"first_transcript={first_text!r}")
    outcome.passed = len(turns) > 0
    if not outcome.passed:
        outcome.detail.append("expected at least one turn in the response")
    return outcome


def main(argv: Sequence[str] | None = None) -> int:
    """Run every applicable live check; return 0 only if all pass."""
    load_dotenv()
    parser = argparse.ArgumentParser(description="Live Meta Model API smoke test.")
    parser.add_argument("--audio", type=Path, default=None, help="WAV file to transcribe")
    parser.add_argument(
        "--effort",
        default="default",
        choices=("default", "minimal", "low", "medium", "high"),
        help="reasoning effort for the chat checks (default omits the parameter)",
    )
    args = parser.parse_args(argv)
    effort = None if args.effort == "default" else args.effort

    try:
        settings = MetaSettings.from_env()
    except MetaClientError as exc:
        print(f"setup FAILED: {exc}")
        return 1
    key_source = "META_API_KEY" if os.environ.get("META_API_KEY") else "MODEL_API_KEY"
    print(f"key_source={key_source} base_url={settings.base_url} effort={args.effort}")

    client = OpenAICompatChatClient(settings)
    outcomes = [
        _check_tool_roundtrip(client, settings.model_agent, effort),
        _check_structured_json(client, settings.model_fast, effort),
        _check_pdf_input(client, settings.model_agent, effort),
        _check_transcribe(settings, args.audio),
    ]
    failed = 0
    for outcome in outcomes:
        status = "PASS" if outcome.passed else "FAIL"
        if not outcome.passed:
            failed += 1
        print(f"[{status}] {outcome.name}")
        for line in outcome.detail:
            print(f"    {line}")
    print(f"RESULT: {'PASS' if failed == 0 else 'FAIL'} ({len(outcomes) - failed}/{len(outcomes)})")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
