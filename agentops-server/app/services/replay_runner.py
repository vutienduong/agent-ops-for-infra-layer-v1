from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.ulid import new_id
from app.models.tables import Replay, Run, Span


def run_llm_only_replay_stub(db: Session, replay: Replay) -> Replay:
    source_run = db.get(Run, replay.run_id)
    if source_run is None:
        replay.status = "failed"
        db.flush()
        return replay

    new_run_id = replay.new_run_id or new_id("run")
    now = datetime.now(timezone.utc)

    new_run = db.get(Run, new_run_id)
    if new_run is None:
        new_run = Run(id=new_run_id, project_id=source_run.project_id)
        db.add(new_run)

    new_run.trace_id = f"{source_run.trace_id or source_run.id}:replay:{replay.id}"
    new_run.name = f"{source_run.name or source_run.id} [replay]"
    new_run.status = "success"
    new_run.started_at = now
    new_run.ended_at = now
    new_run.duration_ms = 0
    new_run.input_json = source_run.input_json
    new_run.output_json = {
        "note": "Stub llm_only replay. LLM calls are not re-executed in this build.",
        "source_run_id": source_run.id,
        "overrides": replay.overrides or {},
    }
    new_run.total_prompt_tokens = 0
    new_run.total_completion_tokens = 0
    new_run.total_cost_usd = 0.0
    new_run.model_summary = source_run.model_summary
    new_run.tags = {
        "replay_of": source_run.id,
        "mode": replay.mode,
    }

    llm_spans = db.scalars(
        select(Span).where(Span.run_id == source_run.id, Span.project_id == source_run.project_id, Span.type == "llm").order_by(
            Span.started_at.asc(),
            Span.id.asc(),
        )
    ).all()

    for source_span in llm_spans:
        replay_span = Span(
            id=new_id("spn"),
            run_id=new_run_id,
            project_id=source_run.project_id,
            parent_span_id=None,
            type="llm",
            name=source_span.name,
            status="skipped",
            started_at=now,
            ended_at=now,
            duration_ms=0,
            model=(replay.overrides or {}).get("model") or source_span.model,
            tokens_prompt=0,
            tokens_completion=0,
            cost_usd=0.0,
            input_json=source_span.input_json,
            output_json={
                "note": "Skipped provider execution in replay stub.",
                "source_span_id": source_span.id,
            },
            error_json=None,
        )
        db.add(replay_span)

    replay.new_run_id = new_run_id
    replay.status = "completed"
    db.flush()
    return replay
