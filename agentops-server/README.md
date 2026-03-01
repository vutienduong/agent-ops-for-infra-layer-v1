# AgentOps Server

MVP backend for ingesting agent events and querying normalized runs.

## Run

```bash
cd agentops-server
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
uvicorn app.main:app --reload
```

## Auth header

Use `X-AgentOps-Key` for authenticated endpoints.

## Dashboard

Open [http://localhost:8000/dashboard](http://localhost:8000/dashboard), paste your API key, and load runs.

## Seed local API key

```bash
cd agentops-server
source .venv/bin/activate
python scripts/seed_api_key.py --project-id proj_demo --api-key dev-agentops-key
```

## Run tests

```bash
cd agentops-server
source .venv/bin/activate
pytest
```
