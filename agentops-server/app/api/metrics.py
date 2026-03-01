from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import get_project_from_api_key
from app.core.db import get_db
from app.models.schemas import CostMetricItem, CostMetricsResponse
from app.models.tables import Project, Run, Span

router = APIRouter(tags=["metrics"])


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@router.get("/v1/metrics/cost", response_model=CostMetricsResponse)
def cost_metrics(
    from_ts: str | None = Query(default=None, alias="from"),
    to_ts: str | None = Query(default=None, alias="to"),
    group_by: str = Query(default="day"),
    project: Project = Depends(get_project_from_api_key),
    db: Session = Depends(get_db),
) -> CostMetricsResponse:
    valid_groups = {"day", "model", "run_name"}
    if group_by not in valid_groups:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"group_by must be one of {sorted(valid_groups)}")

    from_dt = _parse_datetime(from_ts)
    to_dt = _parse_datetime(to_ts)

    items: list[CostMetricItem] = []
    if group_by == "day":
        stmt = (
            select(
                func.date(Run.started_at).label("group"),
                func.coalesce(func.sum(Run.total_cost_usd), 0.0).label("total_cost_usd"),
                func.coalesce(func.sum(Run.total_prompt_tokens), 0).label("total_prompt_tokens"),
                func.coalesce(func.sum(Run.total_completion_tokens), 0).label("total_completion_tokens"),
            )
            .where(Run.project_id == project.id)
            .group_by(func.date(Run.started_at))
            .order_by(func.date(Run.started_at).asc())
        )
        if from_dt:
            stmt = stmt.where(Run.started_at >= from_dt)
        if to_dt:
            stmt = stmt.where(Run.started_at <= to_dt)

        rows = db.execute(stmt).all()
        for row in rows:
            items.append(
                CostMetricItem(
                    group=str(row.group),
                    total_cost_usd=float(row.total_cost_usd or 0.0),
                    total_prompt_tokens=int(row.total_prompt_tokens or 0),
                    total_completion_tokens=int(row.total_completion_tokens or 0),
                )
            )

    elif group_by == "model":
        stmt = (
            select(
                func.coalesce(Span.model, "unknown").label("group"),
                func.coalesce(func.sum(Span.cost_usd), 0.0).label("total_cost_usd"),
                func.coalesce(func.sum(Span.tokens_prompt), 0).label("total_prompt_tokens"),
                func.coalesce(func.sum(Span.tokens_completion), 0).label("total_completion_tokens"),
            )
            .where(Span.project_id == project.id, Span.type == "llm")
            .group_by(func.coalesce(Span.model, "unknown"))
            .order_by(func.coalesce(func.sum(Span.cost_usd), 0.0).desc())
        )
        if from_dt:
            stmt = stmt.where(Span.started_at >= from_dt)
        if to_dt:
            stmt = stmt.where(Span.started_at <= to_dt)

        rows = db.execute(stmt).all()
        for row in rows:
            items.append(
                CostMetricItem(
                    group=str(row.group),
                    total_cost_usd=float(row.total_cost_usd or 0.0),
                    total_prompt_tokens=int(row.total_prompt_tokens or 0),
                    total_completion_tokens=int(row.total_completion_tokens or 0),
                )
            )

    else:  # run_name
        stmt = (
            select(
                func.coalesce(Run.name, "unknown").label("group"),
                func.coalesce(func.sum(Run.total_cost_usd), 0.0).label("total_cost_usd"),
                func.coalesce(func.sum(Run.total_prompt_tokens), 0).label("total_prompt_tokens"),
                func.coalesce(func.sum(Run.total_completion_tokens), 0).label("total_completion_tokens"),
            )
            .where(Run.project_id == project.id)
            .group_by(func.coalesce(Run.name, "unknown"))
            .order_by(func.coalesce(func.sum(Run.total_cost_usd), 0.0).desc())
        )
        if from_dt:
            stmt = stmt.where(Run.started_at >= from_dt)
        if to_dt:
            stmt = stmt.where(Run.started_at <= to_dt)

        rows = db.execute(stmt).all()
        for row in rows:
            items.append(
                CostMetricItem(
                    group=str(row.group),
                    total_cost_usd=float(row.total_cost_usd or 0.0),
                    total_prompt_tokens=int(row.total_prompt_tokens or 0),
                    total_completion_tokens=int(row.total_completion_tokens or 0),
                )
            )

    return CostMetricsResponse(items=items)
