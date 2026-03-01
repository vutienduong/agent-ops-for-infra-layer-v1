from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

router = APIRouter(tags=["prompts"])


@router.get("/v1/prompts")
def list_prompts() -> dict[str, str]:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented in this step")
