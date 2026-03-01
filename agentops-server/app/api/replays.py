from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

router = APIRouter(tags=["replays"])


@router.post("/v1/replays")
def create_replay() -> dict[str, str]:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented in this step")
