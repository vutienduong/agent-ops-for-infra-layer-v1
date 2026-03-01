from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class IngestResponse(BaseModel):
    accepted: int
    rejected: int
    duplicates: int = 0
    errors: list[str] = Field(default_factory=list)


class RunSummary(BaseModel):
    id: str
    trace_id: str | None
    name: str | None
    status: str
    started_at: datetime | None
    ended_at: datetime | None
    duration_ms: int | None
    total_prompt_tokens: int
    total_completion_tokens: int
    total_cost_usd: float
    model_summary: dict[str, Any] | None = None
    tags: dict[str, Any] | None = None

    class Config:
        from_attributes = True


class SpanDetail(BaseModel):
    id: str
    parent_span_id: str | None
    type: str
    name: str | None
    status: str
    started_at: datetime | None
    ended_at: datetime | None
    duration_ms: int | None
    model: str | None
    tokens_prompt: int
    tokens_completion: int
    cost_usd: float
    input_json: dict[str, Any] | None = None
    output_json: dict[str, Any] | None = None
    error_json: dict[str, Any] | None = None

    class Config:
        from_attributes = True


class RunDetail(BaseModel):
    run: RunSummary
    spans: list[SpanDetail]


class RunsListResponse(BaseModel):
    items: list[RunSummary]
    next_cursor: str | None = None
