from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_project_from_api_key
from app.core.db import get_db
from app.models.schemas import ReplayCreate, ReplayRead
from app.models.tables import Project, Replay, Run
from app.services.replay_runner import run_llm_only_replay_stub

router = APIRouter(tags=["replays"])


@router.post("/v1/replays", response_model=ReplayRead, status_code=status.HTTP_201_CREATED)
def create_replay(
    body: ReplayCreate,
    project: Project = Depends(get_project_from_api_key),
    db: Session = Depends(get_db),
) -> ReplayRead:
    if body.mode != "llm_only":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only llm_only mode is supported in MVP")

    source_run = db.get(Run, body.source_run_id)
    if source_run is None or source_run.project_id != project.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source run not found")

    replay = Replay(
        project_id=project.id,
        run_id=source_run.id,
        mode=body.mode,
        overrides=body.overrides,
        status="queued",
    )
    db.add(replay)
    db.flush()

    replay = run_llm_only_replay_stub(db, replay)
    db.commit()
    db.refresh(replay)

    return ReplayRead.model_validate(replay)


@router.get("/v1/replays/{replay_id}", response_model=ReplayRead)
def get_replay(
    replay_id: str,
    project: Project = Depends(get_project_from_api_key),
    db: Session = Depends(get_db),
) -> ReplayRead:
    replay = db.get(Replay, replay_id)
    if replay is None or replay.project_id != project.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Replay not found")

    return ReplayRead.model_validate(replay)
