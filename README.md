# AgentOps for Infra Layer (MVP)

Bootstrap MVP for an AgentOps dev tool: SDK-first event tracing with a lightweight SaaS-style backend and dashboard.

## What is implemented

- `agentops-server/`
  - FastAPI backend
  - Ingestion API (`POST /v1/ingest`)
  - Run APIs (`GET /v1/runs`, `GET /v1/runs/{run_id}`)
  - Prompt version APIs (`/v1/prompts`)
  - Cost metrics API (`/v1/metrics/cost`)
  - Replay APIs (`/v1/replays`, MVP stub with synthetic replay run)
  - Minimal dashboard (`GET /dashboard`)
- `agentops-python/`
  - Minimal Python SDK v0.1 (`init`, `track`, `track_run`, `track_span`, `shutdown`)
- `docs/`
  - Architecture guideline: `docs/technical-diagram.md`
  - Execution checklist: `docs/implementation-plan.md`

## Quickstart

### 1. Start backend

```bash
cd agentops-server
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
uvicorn app.main:app --reload
```

### 2. Seed a local project API key

In a second terminal:

```bash
cd agentops-server
source .venv/bin/activate
python scripts/seed_api_key.py --project-id proj_demo --api-key dev-agentops-key
```

### 3. Open dashboard

Open: [http://localhost:8000/dashboard](http://localhost:8000/dashboard)

Paste API key: `dev-agentops-key`

### 4. Send sample events using SDK example

In another terminal:

```bash
cd agentops-python
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
python examples/basic.py
```

Then refresh dashboard and inspect the run timeline.

## Run tests

```bash
cd agentops-server
source .venv/bin/activate
pytest -q
```

## Notes

- Database defaults to local SQLite (`agentops-server/agentops.db`).
- API authentication currently uses project API key via `X-AgentOps-Key`.
- Replay currently creates a synthetic run and mocked LLM span results (provider re-execution is not yet wired).
