from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class IngestResponse(BaseModel):
    accepted: int
    rejected: int
    duplicates: int = 0
    errors: list[str] = Field(default_factory=list)


class RunSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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

class SpanDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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

class RunDetail(BaseModel):
    run: RunSummary
    spans: list[SpanDetail]


class RunsListResponse(BaseModel):
    items: list[RunSummary]
    next_cursor: str | None = None


class PromptVersionCreate(BaseModel):
    key: str
    version: str
    content: str | None = None
    content_ref: str | None = None
    meta: dict[str, Any] | None = None


class PromptVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    key: str
    version: str
    content: str | None = None
    content_ref: str | None = None
    meta: dict[str, Any] | None = None
    created_at: datetime


class PromptVersionsListResponse(BaseModel):
    items: list[PromptVersionRead]


class CostMetricItem(BaseModel):
    group: str
    total_cost_usd: float
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0


class CostMetricsResponse(BaseModel):
    items: list[CostMetricItem]


class ReplayCreate(BaseModel):
    source_run_id: str
    mode: str = "llm_only"
    overrides: dict[str, Any] | None = None


class ReplayRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: str
    new_run_id: str | None
    mode: str
    overrides: dict[str, Any] | None = None
    status: str
    created_at: datetime
