"""Smoke tests: factory boots, models import, seed counts, tool loop.

The tool-loop tests use a fake chat client: no network, no API key.
"""
from __future__ import annotations

from typing import Any

import pytest
from flask import Flask

from app import create_app
from app.extensions import db
from app.models import ProfessorProfile, StudentProfile, ToolCallLog, User
from app.services.meta_client import (
    ChatResult,
    MetaClientError,
    ToolCallRecord,
    ToolCallRequest,
    run_tool_loop,
)
from scripts.seed import seed_database


@pytest.fixture
def app(tmp_path):  # type: ignore[no-untyped-def]
    """App with a throwaway file database (SQLite ``:memory:`` is per-connection)."""
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path}/test.db",
        }
    )
    ctx = app.app_context()
    ctx.push()
    db.create_all()
    yield app
    db.session.remove()
    db.drop_all()
    ctx.pop()


def test_app_factory_boots_and_health_routes(app: Flask) -> None:
    """Factory boots; app and blueprint health routes answer 200."""
    client = app.test_client()
    assert client.get("/health").status_code == 200
    for prefix in ("auth", "professors", "bookings", "agent"):
        response = client.get(f"/{prefix}/health")
        assert response.status_code == 200
        assert response.get_json() == {"status": "ok", "blueprint": prefix}


def test_models_import_and_tables_exist(app: Flask) -> None:
    """All ten scaffold models are importable and have tables."""
    import app.models  # noqa: F401

    assert set(db.metadata.tables) == {
        "users",
        "professor_profiles",
        "student_profiles",
        "documents",
        "case_files",
        "bookings",
        "session_records",
        "memory_notes",
        "tool_call_logs",
    }
    assert User.query.count() == 0


def test_seed_yields_12_professors_and_3_students(app: Flask) -> None:
    """Seed produces 12 professors across 4 departments and 3 students."""
    counts = seed_database()
    assert counts == {"professors": 12, "students": 3}
    assert User.query.filter_by(role="professor").count() == 12
    assert User.query.filter_by(role="student").count() == 3
    assert ProfessorProfile.query.count() == 12
    assert StudentProfile.query.count() == 3
    departments = {
        row[0] for row in db.session.query(ProfessorProfile.department).distinct()
    }
    assert departments == {
        "Statistics",
        "Computer Science",
        "Economics",
        "English Literature",
    }
    assert User.query.filter_by(is_sample=False).count() == 0


def test_seed_is_idempotent(app: Flask) -> None:
    """A second seed run creates nothing new."""
    first = seed_database()
    second = seed_database()
    assert first == second == {"professors": 12, "students": 3}
    assert ProfessorProfile.query.count() == 12


class FakeChatClient:
    """Scripted chat client: tool call(s) first, then a final answer."""

    def __init__(self, tool_names: list[str], final_text: str = "done") -> None:
        self._tool_names = tool_names
        self._final_text = final_text
        self.calls = 0

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: Any = None,
        *,
        model: str,
        response_format: dict[str, Any] | None = None,
    ) -> ChatResult:
        """Return the next scripted response; fail loudly without a model."""
        assert model, "tool loop must pass a model"
        self.calls += 1
        if self.calls <= len(self._tool_names):
            name = self._tool_names[self.calls - 1]
            call_id = f"call_{self.calls}"
            return ChatResult(
                text="",
                tool_calls=(
                    ToolCallRequest(id=call_id, name=name, arguments={"q": "x"}),
                ),
                raw_assistant_message={"role": "assistant", "content": ""},
            )
        return ChatResult(text=self._final_text)


def test_tool_loop_runs_tool_and_returns_answer() -> None:
    """Happy path: one tool call executes, its result feeds the final answer."""
    seen_messages: list[list[dict[str, Any]]] = []

    class RecordingFake(FakeChatClient):
        def chat(self, messages, tools=None, **kwargs):  # type: ignore[no-untyped-def]
            seen_messages.append([dict(m) for m in messages])
            return super().chat(messages, tools, **kwargs)

    records: list[ToolCallRecord] = []
    answer = run_tool_loop(
        RecordingFake(["search_professors"]),
        [{"role": "user", "content": "find help"}],
        tools=[{"type": "function", "name": "search_professors"}],
        execute_tool={"search_professors": lambda args: [{"name": "Sample"}]},
        model="fake-model",
        log_tool_call=records.append,
    )
    assert answer == "done"
    assert len(records) == 1
    assert records[0].tool_name == "search_professors"
    assert records[0].status == "ok"
    assert records[0].run_id
    tool_messages = [m for m in seen_messages[-1] if m["role"] == "tool"]
    assert tool_messages and "Sample" in tool_messages[0]["content"]


def test_tool_loop_logs_to_db_by_default(app: Flask) -> None:
    """Without a logger override, calls land in ToolCallLog rows."""
    answer = run_tool_loop(
        FakeChatClient(["echo"]),
        [{"role": "user", "content": "hi"}],
        tools=[{"type": "function", "name": "echo"}],
        execute_tool={"echo": lambda args: args},
        model="fake-model",
    )
    assert answer == "done"
    rows = ToolCallLog.query.all()
    assert len(rows) == 1
    assert rows[0].tool_name == "echo"
    assert rows[0].status == "ok"
    assert rows[0].arguments == {"q": "x"}


def test_tool_loop_marks_unknown_tool_as_error() -> None:
    """Unknown tools become logged errors, not crashes."""
    records: list[ToolCallRecord] = []
    answer = run_tool_loop(
        FakeChatClient(["missing_tool"]),
        [{"role": "user", "content": "hi"}],
        tools=[],
        execute_tool={},
        model="fake-model",
        log_tool_call=records.append,
    )
    assert answer == "done"
    assert records[0].status == "error"
    assert "unknown tool" in (records[0].error or "")


def test_tool_loop_enforces_max_iterations() -> None:
    """A model that never stops calling tools hits max_iterations."""

    class StubbornFake(FakeChatClient):
        def chat(self, messages, tools=None, **kwargs):  # type: ignore[no-untyped-def]
            self.calls += 1
            return ChatResult(
                text="",
                tool_calls=(
                    ToolCallRequest(
                        id=f"call_{self.calls}", name="noop", arguments={}
                    ),
                ),
                raw_assistant_message={"role": "assistant", "content": ""},
            )

    with pytest.raises(MetaClientError, match="max_iterations"):
        run_tool_loop(
            StubbornFake([]),
            [{"role": "user", "content": "hi"}],
            tools=[],
            execute_tool={"noop": lambda args: "ok"},
            model="fake-model",
            log_tool_call=lambda record: None,
            max_iterations=3,
        )
