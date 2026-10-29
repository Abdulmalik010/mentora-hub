"""Client for the Meta Model API: retries, structured output, tool loop.

Based on the Meta Model API docs (https://dev.meta.ai/docs): quickstart,
authentication, SDKs, tool calling, structured output, plus the cookbook's
agent-patterns recipes.

Meta publishes no dedicated Python client; the documented path is the OpenAI
SDK pointed at the Meta base URL. This module uses the Chat Completions
protocol (tool calling and ``response_format`` are fully supported there).
No model IDs, endpoints or wire formats are hardcoded: everything comes from
:class:`MetaSettings` (``META_*`` environment variables, see ``.env.example``).
"""
from __future__ import annotations

import json
import logging
import os
import time
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol, TypeVar

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    OpenAI,
    RateLimitError,
)

log = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.meta.ai/v1"
DEFAULT_TIMEOUT_S = 60.0
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_BACKOFF_S = 1.0
DEFAULT_MAX_ITERATIONS = 8

T = TypeVar("T")


class MetaClientError(RuntimeError):
    """Meta API configuration, request or tool-loop failure."""


@dataclass(frozen=True)
class MetaSettings:
    """Connection settings; model IDs always come from the environment."""

    api_key: str
    base_url: str = DEFAULT_BASE_URL
    model_agent: str = ""
    model_fast: str = ""
    model_transcribe: str = ""
    timeout_s: float = DEFAULT_TIMEOUT_S
    max_attempts: int = DEFAULT_MAX_ATTEMPTS

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> MetaSettings:
        """Build settings from env; META_API_KEY preferred, MODEL_API_KEY fallback."""
        env = environ if environ is not None else os.environ
        api_key = env.get("META_API_KEY") or env.get("MODEL_API_KEY", "")
        if not api_key:
            raise MetaClientError("set META_API_KEY (preferred) or MODEL_API_KEY")
        return cls(
            api_key=api_key,
            base_url=env.get("META_BASE_URL") or DEFAULT_BASE_URL,
            model_agent=env.get("META_MODEL_AGENT", ""),
            model_fast=env.get("META_MODEL_FAST", ""),
            model_transcribe=env.get("META_MODEL_TRANSCRIBE", ""),
        )


@dataclass(frozen=True)
class ToolCallRequest:
    """One normalized tool call requested by the model."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ChatResult:
    """Normalized chat response: final text plus any requested tool calls."""

    text: str
    tool_calls: tuple[ToolCallRequest, ...] = ()
    raw_assistant_message: dict[str, Any] | None = None
    usage: dict[str, Any] | None = None


@dataclass(frozen=True)
class ToolCallRecord:
    """One executed tool call, ready to persist to ``ToolCallLog``."""

    tool_name: str
    arguments: dict[str, Any]
    result: str | None
    status: str  # "ok" | "error"
    error: str | None = None
    duration_ms: float | None = None
    run_id: str | None = None


class ChatClient(Protocol):
    """Minimal chat interface; SDK adapter in prod, fakes in tests."""

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: Sequence[dict[str, Any]] | None = None,
        *,
        model: str,
        response_format: dict[str, Any] | None = None,
    ) -> ChatResult:
        """Send messages and return the normalized response."""
        ...


def _is_retriable(exc: Exception) -> bool:
    """True for rate limits, transport/timeout failures and 5xx responses."""
    if isinstance(exc, (RateLimitError, APIConnectionError, APITimeoutError)):
        return True
    if isinstance(exc, APIStatusError):
        return exc.status_code is not None and exc.status_code >= 500
    return False


def with_retries(
    func: Callable[[], T],
    *,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    backoff_s: float = DEFAULT_BACKOFF_S,
    sleep: Callable[[float], None] = time.sleep,
    description: str = "Meta API request",
) -> T:
    """Run ``func`` with exponential-backoff retries on transient API errors."""
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return func()
        except Exception as exc:
            last_error = exc
            if attempt >= max_attempts or not _is_retriable(exc):
                raise
            delay = backoff_s * 2 ** (attempt - 1)
            log.warning(
                "%s failed (attempt %d/%d): %s; retrying in %.1fs",
                description,
                attempt,
                max_attempts,
                exc,
                delay,
            )
            sleep(delay)
    assert last_error is not None  # loop always raises before falling through
    raise last_error


class OpenAICompatChatClient:
    """ChatClient over the OpenAI SDK pointed at the Meta base URL."""

    def __init__(self, settings: MetaSettings) -> None:
        self._settings = settings
        self._client = OpenAI(
            api_key=settings.api_key,
            base_url=settings.base_url,
            timeout=settings.timeout_s,
            max_retries=0,  # retries handled by with_retries, not stacked
        )

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: Sequence[dict[str, Any]] | None = None,
        *,
        model: str,
        response_format: dict[str, Any] | None = None,
    ) -> ChatResult:
        """Call Chat Completions with retries; normalize to ChatResult."""
        if not model:
            raise MetaClientError("no model configured (set META_MODEL_*)")

        def _call():  # type: ignore[no-untyped-def]
            return self._client.chat.completions.create(
                model=model,
                messages=messages,  # type: ignore[arg-type]
                tools=list(tools) if tools else None,  # type: ignore[arg-type]
                response_format=response_format,  # type: ignore[arg-type]
            )

        response = with_retries(_call, max_attempts=self._settings.max_attempts)
        message = response.choices[0].message
        calls: list[ToolCallRequest] = []
        for call in message.tool_calls or []:
            try:
                arguments = json.loads(call.function.arguments or "{}")
            except json.JSONDecodeError as exc:
                raise MetaClientError(
                    f"unparseable tool arguments for {call.function.name!r}: {exc}"
                ) from exc
            calls.append(
                ToolCallRequest(
                    id=call.id, name=call.function.name, arguments=arguments
                )
            )
        raw: dict[str, Any] = {"role": "assistant", "content": message.content or ""}
        if message.tool_calls:
            raw["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.function.name,
                        "arguments": call.function.arguments,
                    },
                }
                for call in message.tool_calls
            ]
        usage = response.usage
        return ChatResult(
            text=message.content or "",
            tool_calls=tuple(calls),
            raw_assistant_message=raw,
            usage=usage.model_dump() if usage is not None else None,
        )


def complete_json(
    client: ChatClient,
    messages: list[dict[str, Any]],
    *,
    model: str,
    schema: dict[str, Any],
    name: str,
) -> dict[str, Any]:
    """Request schema-conforming JSON via response_format; return parsed dict."""
    result = client.chat(
        messages,
        model=model,
        response_format={
            "type": "json_schema",
            "json_schema": {"name": name, "schema": schema},
        },
    )
    try:
        parsed = json.loads(result.text)
    except json.JSONDecodeError as exc:
        raise MetaClientError(
            f"model did not return valid JSON for {name!r}: {exc}"
        ) from exc
    if not isinstance(parsed, dict):
        raise MetaClientError(f"expected a JSON object for {name!r}")
    return parsed


def log_tool_call_to_db(record: ToolCallRecord) -> None:
    """Persist one tool-call record to ToolCallLog (needs app context)."""
    from app.extensions import db
    from app.models import ToolCallLog

    db.session.add(
        ToolCallLog(
            run_id=record.run_id,
            tool_name=record.tool_name,
            arguments=record.arguments,
            result=record.result,
            status=record.status,
            error=record.error,
            duration_ms=record.duration_ms,
        )
    )
    db.session.commit()


def run_tool_loop(
    client: ChatClient,
    messages: list[dict[str, Any]],
    tools: Sequence[dict[str, Any]] | None,
    execute_tool: Mapping[str, Callable[[dict[str, Any]], Any]],
    *,
    model: str,
    log_tool_call: Callable[[ToolCallRecord], None] | None = None,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    run_id: str | None = None,
) -> str:
    """Run a model/tools loop until a final answer or ``max_iterations``.

    Every tool call is logged via ``log_tool_call`` (default: ToolCallLog
    rows). Unknown tools and tool exceptions become error results for the
    model and are logged with ``status="error"`` instead of aborting.
    """
    logger = log_tool_call or log_tool_call_to_db
    active_run_id = run_id or uuid.uuid4().hex
    working = list(messages)
    for _ in range(max_iterations):
        result = client.chat(working, tools, model=model)
        if not result.tool_calls:
            return result.text
        working.append(
            result.raw_assistant_message
            or {"role": "assistant", "content": result.text}
        )
        for call in result.tool_calls:
            started = time.monotonic()
            func = execute_tool.get(call.name)
            if func is None:
                output: Any = None
                status, error = "error", f"unknown tool: {call.name!r}"
            else:
                try:
                    output = func(call.arguments)
                    status, error = "ok", None
                except Exception as exc:
                    output, status = None, "error"
                    error = f"{type(exc).__name__}: {exc}"
            duration_ms = (time.monotonic() - started) * 1000.0
            if status == "error":
                content = json.dumps({"error": error})
            elif isinstance(output, str):
                content = output
            else:
                content = json.dumps(output, default=str)
            logger(
                ToolCallRecord(
                    tool_name=call.name,
                    arguments=call.arguments,
                    result=content,
                    status=status,
                    error=error,
                    duration_ms=duration_ms,
                    run_id=active_run_id,
                )
            )
            working.append(
                {"role": "tool", "tool_call_id": call.id, "content": content}
            )
    raise MetaClientError(f"tool loop exceeded max_iterations={max_iterations}")


class MetaClient:
    """Convenience facade binding settings to a chat client."""

    def __init__(
        self,
        settings: MetaSettings | None = None,
        chat_client: ChatClient | None = None,
    ) -> None:
        self.settings = settings or MetaSettings.from_env()
        self._chat = chat_client or OpenAICompatChatClient(self.settings)

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> MetaClient:
        """Build a client from ``META_*`` environment variables."""
        return cls(MetaSettings.from_env(environ))

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: Sequence[dict[str, Any]] | None = None,
        *,
        model: str | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> ChatResult:
        """Chat with the agent model unless another is given."""
        return self._chat.chat(
            messages,
            tools,
            model=model or self.settings.model_agent,
            response_format=response_format,
        )

    def complete_json(
        self,
        messages: list[dict[str, Any]],
        *,
        schema: dict[str, Any],
        name: str,
        model: str | None = None,
    ) -> dict[str, Any]:
        """Schema-conforming JSON via the agent model unless another is given."""
        return complete_json(
            self._chat, messages, model=model or self.settings.model_agent,
            schema=schema, name=name,
        )

    def run_tool_loop(
        self,
        messages: list[dict[str, Any]],
        tools: Sequence[dict[str, Any]] | None,
        execute_tool: Mapping[str, Callable[[dict[str, Any]], Any]],
        *,
        model: str | None = None,
        log_tool_call: Callable[[ToolCallRecord], None] | None = None,
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
        run_id: str | None = None,
    ) -> str:
        """Tool loop via the agent model unless another is given."""
        return run_tool_loop(
            self._chat,
            messages,
            tools,
            execute_tool,
            model=model or self.settings.model_agent,
            log_tool_call=log_tool_call,
            max_iterations=max_iterations,
            run_id=run_id,
        )
