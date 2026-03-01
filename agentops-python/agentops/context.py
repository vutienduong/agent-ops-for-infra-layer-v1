from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from functools import wraps
from typing import Any

from ._ids import new_ulid
from .client import AgentOpsClient, ClientConfig


_current_client: AgentOpsClient | None = None
_current_run_id: ContextVar[str | None] = ContextVar("agentops_current_run_id", default=None)
_current_trace_id: ContextVar[str | None] = ContextVar("agentops_current_trace_id", default=None)
_current_span_stack: ContextVar[list[str]] = ContextVar("agentops_current_span_stack", default=[])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def init(*, api_key: str, endpoint: str = "http://localhost:8000", environment: str = "dev") -> None:
    global _current_client
    if _current_client is not None:
        _current_client.close()
    _current_client = AgentOpsClient(
        ClientConfig(
            api_key=api_key,
            endpoint=endpoint,
            environment=environment,
        )
    )


def flush() -> None:
    if _current_client:
        _current_client.flush()


def shutdown() -> None:
    global _current_client
    if _current_client:
        _current_client.close()
        _current_client = None


def _require_client() -> AgentOpsClient:
    if _current_client is None:
        raise RuntimeError("agentops.init(api_key=...) must be called before tracking")
    return _current_client


class SpanHandle:
    def __init__(self) -> None:
        self.output: dict[str, Any] | None = None
        self.error: dict[str, Any] | None = None
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.cost_usd = 0.0

    def set_output(self, output: dict[str, Any]) -> None:
        self.output = output

    def set_error(self, error: dict[str, Any]) -> None:
        self.error = error

    def set_usage(self, *, prompt_tokens: int, completion_tokens: int, cost_usd: float = 0.0) -> None:
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.cost_usd = cost_usd


@contextmanager
def track_run(name: str, *, input_data: dict[str, Any] | None = None, tags: dict[str, Any] | None = None):
    client = _require_client()
    run_id = new_ulid()
    trace_id = f"trace_{run_id}"
    started_at = _now_iso()

    token_run = _current_run_id.set(run_id)
    token_trace = _current_trace_id.set(trace_id)

    client.emit(
        {
            "schema_version": "1.0",
            "event_id": new_ulid(),
            "event_type": "run_started",
            "timestamp": started_at,
            "sdk": {"name": "agentops-python", "version": "0.1.0"},
            "context": {"trace_id": trace_id, "run_id": run_id, "span_id": None},
            "payload": {
                "name": name,
                "tags": tags or {},
                "input": {"inline": input_data or {}, "truncated": False},
            },
        }
    )

    status = "success"
    output: dict[str, Any] | None = None
    error_payload: dict[str, Any] | None = None

    try:
        yield
    except Exception as exc:  # noqa: BLE001
        status = "fail"
        error_payload = {"type": type(exc).__name__, "message": str(exc)}
        raise
    finally:
        ended_at = _now_iso()
        payload: dict[str, Any] = {
            "status": status,
            "timing": {"started_at": started_at, "ended_at": ended_at},
            "summary": {
                "total_prompt_tokens": 0,
                "total_completion_tokens": 0,
                "total_cost_usd": 0.0,
                "models": [],
            },
            "output": {"inline": output or {}, "truncated": False},
        }
        if error_payload:
            payload["error"] = error_payload

        client.emit(
            {
                "schema_version": "1.0",
                "event_id": new_ulid(),
                "event_type": "run_finished",
                "timestamp": ended_at,
                "sdk": {"name": "agentops-python", "version": "0.1.0"},
                "context": {"trace_id": trace_id, "run_id": run_id, "span_id": None},
                "payload": payload,
            }
        )
        _current_run_id.reset(token_run)
        _current_trace_id.reset(token_trace)


@contextmanager
def track_span(
    span_type: str,
    name: str,
    *,
    input_data: dict[str, Any] | None = None,
    attributes: dict[str, Any] | None = None,
):
    client = _require_client()
    run_id = _current_run_id.get()
    trace_id = _current_trace_id.get()
    if not run_id or not trace_id:
        raise RuntimeError("track_span must run inside track_run")

    span_id = new_ulid()
    stack = list(_current_span_stack.get())
    parent_span_id = stack[-1] if stack else None
    stack.append(span_id)
    token_stack = _current_span_stack.set(stack)

    started_at = _now_iso()

    client.emit(
        {
            "schema_version": "1.0",
            "event_id": new_ulid(),
            "event_type": "span_started",
            "timestamp": started_at,
            "sdk": {"name": "agentops-python", "version": "0.1.0"},
            "context": {"trace_id": trace_id, "run_id": run_id, "span_id": span_id},
            "payload": {
                "parent_span_id": parent_span_id,
                "type": span_type,
                "name": name,
                "attributes": attributes or {},
                "input": {"inline": input_data or {}, "truncated": False},
            },
        }
    )

    handle = SpanHandle()
    status = "success"

    try:
        yield handle
    except Exception as exc:  # noqa: BLE001
        status = "fail"
        handle.set_error({"type": type(exc).__name__, "message": str(exc)})
        raise
    finally:
        ended_at = _now_iso()
        client.emit(
            {
                "schema_version": "1.0",
                "event_id": new_ulid(),
                "event_type": "span_finished",
                "timestamp": ended_at,
                "sdk": {"name": "agentops-python", "version": "0.1.0"},
                "context": {"trace_id": trace_id, "run_id": run_id, "span_id": span_id},
                "payload": {
                    "status": status,
                    "timing": {"started_at": started_at, "ended_at": ended_at},
                    "usage": {
                        "prompt_tokens": handle.prompt_tokens,
                        "completion_tokens": handle.completion_tokens,
                    },
                    "cost": {"currency": "USD", "value": handle.cost_usd},
                    "output": {"inline": handle.output or {}, "truncated": False},
                    "error": handle.error,
                },
            }
        )

        stack = list(_current_span_stack.get())
        if stack:
            stack.pop()
        _current_span_stack.reset(token_stack)


def track(name: str):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with track_run(name=name):
                return func(*args, **kwargs)

        return wrapper

    return decorator
