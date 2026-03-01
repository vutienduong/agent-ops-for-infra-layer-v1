from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.auth import get_project_from_api_key
from app.core.db import get_db
from app.models.schemas import PromptVersionCreate, PromptVersionRead, PromptVersionsListResponse
from app.models.tables import Project, PromptVersion

router = APIRouter(tags=["prompts"])


@router.post("/v1/prompts", response_model=PromptVersionRead, status_code=status.HTTP_201_CREATED)
def create_prompt_version(
    body: PromptVersionCreate,
    project: Project = Depends(get_project_from_api_key),
    db: Session = Depends(get_db),
) -> PromptVersionRead:
    if not body.content and not body.content_ref:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either content or content_ref must be provided",
        )

    row = PromptVersion(
        project_id=project.id,
        key=body.key,
        version=body.version,
        content=body.content,
        content_ref=body.content_ref,
        meta=body.meta,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return PromptVersionRead.model_validate(row)


@router.get("/v1/prompts", response_model=PromptVersionsListResponse)
def list_prompts(
    key: str | None = Query(default=None),
    project: Project = Depends(get_project_from_api_key),
    db: Session = Depends(get_db),
) -> PromptVersionsListResponse:
    stmt = select(PromptVersion).where(PromptVersion.project_id == project.id)
    if key:
        stmt = stmt.where(PromptVersion.key == key)
    stmt = stmt.order_by(PromptVersion.key.asc(), desc(PromptVersion.created_at))

    rows = db.scalars(stmt).all()
    return PromptVersionsListResponse(items=[PromptVersionRead.model_validate(row) for row in rows])


@router.get("/v1/prompts/{prompt_id}", response_model=PromptVersionRead)
def get_prompt(
    prompt_id: str,
    project: Project = Depends(get_project_from_api_key),
    db: Session = Depends(get_db),
) -> PromptVersionRead:
    row = db.get(PromptVersion, prompt_id)
    if row is None or row.project_id != project.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt version not found")
    return PromptVersionRead.model_validate(row)
