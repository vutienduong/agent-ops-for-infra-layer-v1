from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

router = APIRouter(tags=["metrics"])


@router.get("/v1/metrics/cost")
def cost_metrics() -> dict[str, str]:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented in this step")
