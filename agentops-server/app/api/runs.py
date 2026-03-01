from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.auth import get_project_from_api_key
from app.core.db import get_db
from app.models.schemas import RunDetail, RunSummary, RunsListResponse, SpanDetail
from app.models.tables import Project, Run, Span

router = APIRouter(tags=["runs"])


@router.get("/v1/runs", response_model=RunsListResponse)
def list_runs(
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = Query(default=None),
    project: Project = Depends(get_project_from_api_key),
    db: Session = Depends(get_db),
) -> RunsListResponse:
    stmt = (
        select(Run)
        .where(Run.project_id == project.id)
        .order_by(desc(Run.started_at), desc(Run.id))
        .limit(limit + 1)
    )

    if cursor:
        cursor_run = db.get(Run, cursor)
        if cursor_run and cursor_run.project_id == project.id:
            if cursor_run.started_at is not None:
                stmt = stmt.where(
                    (Run.started_at < cursor_run.started_at)
                    | ((Run.started_at == cursor_run.started_at) & (Run.id < cursor_run.id))
                )
            else:
                stmt = stmt.where(Run.id < cursor_run.id)

    rows = db.scalars(stmt).all()

    next_cursor = None
    if len(rows) > limit:
        next_cursor = rows[limit - 1].id
        rows = rows[:limit]

    return RunsListResponse(items=[RunSummary.model_validate(row) for row in rows], next_cursor=next_cursor)


@router.get("/v1/runs/{run_id}", response_model=RunDetail)
def get_run(
    run_id: str,
    project: Project = Depends(get_project_from_api_key),
    db: Session = Depends(get_db),
) -> RunDetail:
    run = db.get(Run, run_id)
    if run is None or run.project_id != project.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    spans = db.scalars(
        select(Span).where(Span.project_id == project.id, Span.run_id == run.id).order_by(Span.started_at.asc(), Span.id.asc())
    ).all()

    return RunDetail(
        run=RunSummary.model_validate(run),
        spans=[SpanDetail.model_validate(span) for span in spans],
    )
