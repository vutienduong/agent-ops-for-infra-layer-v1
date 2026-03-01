from __future__ import annotations

import hashlib

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.tables import ApiKey, Project


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def get_project_from_api_key(
    x_agentops_key: str | None = Header(default=None, alias="X-AgentOps-Key"),
    db: Session = Depends(get_db),
) -> Project:
    if not x_agentops_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key")

    key_hash = hash_api_key(x_agentops_key)
    api_key = db.scalar(select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.revoked_at.is_(None)))

    if api_key is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    project = db.get(Project, api_key.project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Project not found")

    return project
