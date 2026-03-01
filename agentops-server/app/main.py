from __future__ import annotations

from fastapi import FastAPI

from app.api.ingest import router as ingest_router
from app.api.metrics import router as metrics_router
from app.api.prompts import router as prompts_router
from app.api.replays import router as replays_router
from app.api.runs import router as runs_router
from app.core.config import settings
from app.core.db import init_db


app = FastAPI(title=settings.app_name)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(ingest_router)
app.include_router(runs_router)
app.include_router(prompts_router)
app.include_router(replays_router)
app.include_router(metrics_router)
