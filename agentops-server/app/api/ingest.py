from __future__ import annotations

import gzip
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.auth import get_project_from_api_key
from app.core.db import get_db
from app.models.schemas import IngestResponse
from app.models.tables import Project
from app.services.ingest_store import ingest_events
from app.services.normalizer import normalize_runs

router = APIRouter(tags=["ingest"])


def _parse_json_events(body: bytes, content_type: str | None) -> list[dict[str, Any]]:
    raw_content_type = (content_type or "").lower()

    if "application/x-ndjson" in raw_content_type:
        events = []
        for line in body.decode("utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            parsed = json.loads(line)
            if not isinstance(parsed, dict):
                raise ValueError("NDJSON line must be JSON object")
            events.append(parsed)
        return events

    payload = json.loads(body.decode("utf-8"))
    if isinstance(payload, list):
        if all(isinstance(item, dict) for item in payload):
            return payload
        raise ValueError("JSON array must contain only objects")

    if isinstance(payload, dict):
        if isinstance(payload.get("events"), list):
            events = payload["events"]
            if all(isinstance(item, dict) for item in events):
                return events
            raise ValueError("events must contain only objects")
        return [payload]

    raise ValueError("Unsupported JSON payload")


@router.post("/v1/ingest", response_model=IngestResponse)
async def ingest(
    request: Request,
    project: Project = Depends(get_project_from_api_key),
    db: Session = Depends(get_db),
) -> IngestResponse:
    body = await request.body()
    content_encoding = (request.headers.get("Content-Encoding") or "").lower()

    if content_encoding == "gzip":
        try:
            body = gzip.decompress(body)
        except OSError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid gzip body") from exc

    try:
        events = _parse_json_events(body, request.headers.get("Content-Type"))
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if not events:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty events payload")

    result = ingest_events(db, project_id=project.id, events=events)

    if result.run_ids:
        normalize_runs(db, project_id=project.id, run_ids=result.run_ids)

    db.commit()

    return IngestResponse(
        accepted=result.accepted,
        rejected=result.rejected,
        duplicates=result.duplicates,
        errors=result.errors,
    )
