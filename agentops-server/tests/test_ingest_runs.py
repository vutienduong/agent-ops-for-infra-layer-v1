from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.auth import hash_api_key
from app.core.db import SessionLocal, engine, init_db
from app.main import app
from app.models.tables import ApiKey, Project


def _seed_project_and_key(api_key: str = "test-key") -> None:
    db = SessionLocal()
    try:
        project = db.get(Project, "proj_test")
        if project is None:
            db.add(Project(id="proj_test", name="Test Project"))

        key_hash = hash_api_key(api_key)
        existing_key = db.scalar(select(ApiKey).where(ApiKey.key_hash == key_hash))
        if existing_key is None:
            db.add(ApiKey(project_id="proj_test", key_hash=key_hash, name="test"))

        db.commit()
    finally:
        db.close()


def _reset_db() -> None:
    db_path = Path(__file__).resolve().parents[1] / "agentops.db"
    engine.dispose()
    if db_path.exists():
        db_path.unlink()
    init_db()


def test_ingest_and_query_runs() -> None:
    _reset_db()
    _seed_project_and_key("test-key")

    client = TestClient(app)
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    events = [
        {
            "schema_version": "1.0",
            "event_id": "evt1",
            "event_type": "run_started",
            "timestamp": now,
            "sdk": {"name": "agentops-python", "version": "0.1.0"},
            "context": {"trace_id": "trace1", "run_id": "run1", "span_id": None},
            "payload": {"name": "demo", "input": {"inline": {"q": "hello"}, "truncated": False}},
        },
        {
            "schema_version": "1.0",
            "event_id": "evt2",
            "event_type": "span_started",
            "timestamp": now,
            "sdk": {"name": "agentops-python", "version": "0.1.0"},
            "context": {"trace_id": "trace1", "run_id": "run1", "span_id": "span1"},
            "payload": {
                "parent_span_id": None,
                "type": "llm",
                "name": "call",
                "attributes": {"provider": "openai", "model": "gpt-4.1-mini"},
                "input": {"inline": {"messages": [{"role": "user", "content": "hello"}]}, "truncated": False},
            },
        },
        {
            "schema_version": "1.0",
            "event_id": "evt3",
            "event_type": "span_finished",
            "timestamp": now,
            "sdk": {"name": "agentops-python", "version": "0.1.0"},
            "context": {"trace_id": "trace1", "run_id": "run1", "span_id": "span1"},
            "payload": {
                "status": "success",
                "timing": {"started_at": now, "ended_at": now},
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
                "cost": {"currency": "USD", "value": 0.01},
                "output": {"inline": {"text": "result"}, "truncated": False},
                "error": None,
            },
        },
        {
            "schema_version": "1.0",
            "event_id": "evt4",
            "event_type": "run_finished",
            "timestamp": now,
            "sdk": {"name": "agentops-python", "version": "0.1.0"},
            "context": {"trace_id": "trace1", "run_id": "run1", "span_id": None},
            "payload": {
                "status": "success",
                "timing": {"started_at": now, "ended_at": now},
                "summary": {
                    "total_prompt_tokens": 10,
                    "total_completion_tokens": 5,
                    "total_cost_usd": 0.01,
                    "models": ["gpt-4.1-mini"],
                },
                "output": {"inline": {"result": "done"}, "truncated": False},
            },
        },
    ]

    headers = {"X-AgentOps-Key": "test-key"}

    ingest_resp = client.post("/v1/ingest", json=events, headers=headers)
    assert ingest_resp.status_code == 200
    assert ingest_resp.json()["accepted"] == 4

    duplicate_resp = client.post("/v1/ingest", json=events, headers=headers)
    assert duplicate_resp.status_code == 200
    assert duplicate_resp.json()["duplicates"] == 4

    runs_resp = client.get("/v1/runs", headers=headers)
    assert runs_resp.status_code == 200
    runs_payload = runs_resp.json()
    assert len(runs_payload["items"]) == 1
    assert runs_payload["items"][0]["id"] == "run1"

    detail_resp = client.get("/v1/runs/run1", headers=headers)
    assert detail_resp.status_code == 200
    detail_payload = detail_resp.json()
    assert detail_payload["run"]["status"] == "success"
    assert len(detail_payload["spans"]) == 1

    prompt_resp = client.post(
        "/v1/prompts",
        json={"key": "invoice.summary", "version": "1", "content": "Summarize invoice {{invoice_id}}"},
        headers=headers,
    )
    assert prompt_resp.status_code == 201
    prompt_id = prompt_resp.json()["id"]

    list_prompts_resp = client.get("/v1/prompts?key=invoice.summary", headers=headers)
    assert list_prompts_resp.status_code == 200
    assert len(list_prompts_resp.json()["items"]) == 1

    get_prompt_resp = client.get(f"/v1/prompts/{prompt_id}", headers=headers)
    assert get_prompt_resp.status_code == 200
    assert get_prompt_resp.json()["key"] == "invoice.summary"

    cost_day_resp = client.get("/v1/metrics/cost?group_by=day", headers=headers)
    assert cost_day_resp.status_code == 200
    assert len(cost_day_resp.json()["items"]) >= 1

    cost_model_resp = client.get("/v1/metrics/cost?group_by=model", headers=headers)
    assert cost_model_resp.status_code == 200
    assert any(item["group"] == "gpt-4.1-mini" for item in cost_model_resp.json()["items"])

    replay_resp = client.post(
        "/v1/replays",
        json={"source_run_id": "run1", "mode": "llm_only", "overrides": {"model": "gpt-4.1"}},
        headers=headers,
    )
    assert replay_resp.status_code == 201
    replay_payload = replay_resp.json()
    assert replay_payload["status"] == "completed"
    assert replay_payload["new_run_id"] is not None

    replay_status_resp = client.get(f"/v1/replays/{replay_payload['id']}", headers=headers)
    assert replay_status_resp.status_code == 200

    new_run_resp = client.get(f"/v1/runs/{replay_payload['new_run_id']}", headers=headers)
    assert new_run_resp.status_code == 200
    assert new_run_resp.json()["run"]["status"] == "success"

    dashboard_resp = client.get("/dashboard")
    assert dashboard_resp.status_code == 200
    assert "AgentOps MVP Dashboard" in dashboard_resp.text
