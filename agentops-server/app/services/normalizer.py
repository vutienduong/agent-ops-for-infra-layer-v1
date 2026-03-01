from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tables import RawEvent, Run, Span


def _parse_iso8601(timestamp: str | None) -> datetime | None:
    if not timestamp:
        return None
    if timestamp.endswith("Z"):
        timestamp = timestamp[:-1] + "+00:00"
    parsed = datetime.fromisoformat(timestamp)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _duration_ms(started_at: datetime | None, ended_at: datetime | None) -> int | None:
    if not started_at or not ended_at:
        return None
    return max(0, int((ended_at - started_at).total_seconds() * 1000))


def normalize_runs(db: Session, *, project_id: str, run_ids: set[str]) -> None:
    for run_id in run_ids:
        events = db.scalars(
            select(RawEvent)
            .where(RawEvent.project_id == project_id, RawEvent.run_id == run_id)
            .order_by(RawEvent.event_ts.asc(), RawEvent.received_at.asc())
        ).all()

        if not events:
            continue

        run_state: dict[str, Any] = {
            "id": run_id,
            "project_id": project_id,
            "trace_id": None,
            "name": None,
            "status": "running",
            "started_at": None,
            "ended_at": None,
            "input_json": None,
            "output_json": None,
            "tags": None,
            "models": set(),
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "total_cost_usd": 0.0,
        }
        span_states: dict[str, dict[str, Any]] = defaultdict(dict)

        for ev in events:
            payload = ev.payload_json or {}
            run_state["trace_id"] = run_state["trace_id"] or ev.trace_id

            if ev.event_type == "run_started":
                run_state["name"] = payload.get("name") or run_state["name"]
                run_state["status"] = "running"
                run_state["started_at"] = run_state["started_at"] or ev.event_ts
                run_state["input_json"] = payload.get("input", {}).get("inline")
                run_state["tags"] = payload.get("tags")

            elif ev.event_type == "span_started":
                if not ev.span_id:
                    continue
                attributes = payload.get("attributes") or {}
                span = span_states[ev.span_id]
                span.update(
                    {
                        "id": ev.span_id,
                        "run_id": run_id,
                        "project_id": project_id,
                        "parent_span_id": payload.get("parent_span_id"),
                        "type": payload.get("type", "custom"),
                        "name": payload.get("name"),
                        "status": span.get("status", "running"),
                        "started_at": span.get("started_at") or ev.event_ts,
                        "model": attributes.get("model"),
                        "input_json": (payload.get("input") or {}).get("inline"),
                    }
                )
                if attributes.get("model"):
                    run_state["models"].add(attributes["model"])

            elif ev.event_type == "span_finished":
                if not ev.span_id:
                    continue
                span = span_states[ev.span_id]
                timing = payload.get("timing") or {}
                usage = payload.get("usage") or {}
                cost = payload.get("cost") or {}
                started_at = _parse_iso8601(timing.get("started_at")) or span.get("started_at")
                ended_at = _parse_iso8601(timing.get("ended_at")) or ev.event_ts

                span.update(
                    {
                        "id": ev.span_id,
                        "run_id": run_id,
                        "project_id": project_id,
                        "status": payload.get("status", "success"),
                        "started_at": started_at,
                        "ended_at": ended_at,
                        "duration_ms": _duration_ms(started_at, ended_at),
                        "tokens_prompt": int(usage.get("prompt_tokens") or 0),
                        "tokens_completion": int(usage.get("completion_tokens") or 0),
                        "cost_usd": float(cost.get("value") or 0.0),
                        "output_json": (payload.get("output") or {}).get("inline"),
                        "error_json": payload.get("error"),
                    }
                )

                run_state["total_prompt_tokens"] += span["tokens_prompt"]
                run_state["total_completion_tokens"] += span["tokens_completion"]
                run_state["total_cost_usd"] += span["cost_usd"]

            elif ev.event_type == "run_finished":
                timing = payload.get("timing") or {}
                summary = payload.get("summary") or {}
                run_state["status"] = payload.get("status", run_state["status"])
                run_state["started_at"] = _parse_iso8601(timing.get("started_at")) or run_state["started_at"]
                run_state["ended_at"] = _parse_iso8601(timing.get("ended_at")) or ev.event_ts
                run_state["output_json"] = (payload.get("output") or {}).get("inline")

                if summary:
                    run_state["total_prompt_tokens"] = int(
                        summary.get("total_prompt_tokens") or run_state["total_prompt_tokens"]
                    )
                    run_state["total_completion_tokens"] = int(
                        summary.get("total_completion_tokens") or run_state["total_completion_tokens"]
                    )
                    run_state["total_cost_usd"] = float(summary.get("total_cost_usd") or run_state["total_cost_usd"])
                    for model in summary.get("models") or []:
                        run_state["models"].add(model)

        run_state["duration_ms"] = _duration_ms(run_state["started_at"], run_state["ended_at"])
        run_state["model_summary"] = {"models": sorted(run_state["models"])}

        db_run = db.get(Run, run_id)
        if db_run is None:
            db_run = Run(id=run_id, project_id=project_id)
            db.add(db_run)

        db_run.trace_id = run_state["trace_id"]
        db_run.name = run_state["name"]
        db_run.status = run_state["status"]
        db_run.started_at = run_state["started_at"]
        db_run.ended_at = run_state["ended_at"]
        db_run.duration_ms = run_state["duration_ms"]
        db_run.input_json = run_state["input_json"]
        db_run.output_json = run_state["output_json"]
        db_run.total_prompt_tokens = run_state["total_prompt_tokens"]
        db_run.total_completion_tokens = run_state["total_completion_tokens"]
        db_run.total_cost_usd = run_state["total_cost_usd"]
        db_run.model_summary = run_state["model_summary"]
        db_run.tags = run_state["tags"]

        for span_id, span_data in span_states.items():
            if not span_data:
                continue
            db_span = db.get(Span, span_id)
            if db_span is None:
                db_span = Span(id=span_id, run_id=run_id, project_id=project_id, type=span_data.get("type", "custom"))
                db.add(db_span)

            db_span.parent_span_id = span_data.get("parent_span_id")
            db_span.type = span_data.get("type", "custom")
            db_span.name = span_data.get("name")
            db_span.status = span_data.get("status", "running")
            db_span.started_at = span_data.get("started_at")
            db_span.ended_at = span_data.get("ended_at")
            db_span.duration_ms = span_data.get("duration_ms")
            db_span.model = span_data.get("model")
            db_span.tokens_prompt = int(span_data.get("tokens_prompt") or 0)
            db_span.tokens_completion = int(span_data.get("tokens_completion") or 0)
            db_span.cost_usd = float(span_data.get("cost_usd") or 0.0)
            db_span.input_json = span_data.get("input_json")
            db_span.output_json = span_data.get("output_json")
            db_span.error_json = span_data.get("error_json")

    db.flush()
