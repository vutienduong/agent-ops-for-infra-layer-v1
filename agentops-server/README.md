# AgentOps Server

MVP backend for ingesting agent events and querying normalized runs.

## Run

```bash
cd agentops-server
python -m venv .venv
source .venv/bin/activate
pip install -e .
uvicorn app.main:app --reload
```

## Auth header

Use `X-AgentOps-Key` for authenticated endpoints.
