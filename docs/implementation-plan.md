# AgentOps MVP Implementation Plan

Status date: 2026-03-01

## Goal
Implement the bootstrap MVP from `docs/technical-diagram.md` with an execution order that yields working end-to-end tracing quickly.

## Scope for this execution
- Phase 1: server skeleton + core data plane
- Phase 2: run normalization + run query APIs
- Partial setup for later phases (worker/replay/prompts placeholders)

## Task Breakdown

### Phase 0: Planning and task tracking
- [x] Convert architecture guideline into execution plan
- [x] Define concrete deliverables for each phase

### Phase 1: Data plane foundation
- [x] Create `agentops-server` project structure
- [x] Add FastAPI app entrypoint and router wiring
- [x] Add configuration and DB session management
- [x] Add SQLAlchemy models and indexes for:
  - [x] `projects`
  - [x] `api_keys`
  - [x] `raw_events` with idempotency uniqueness `(project_id, event_id)`
  - [x] `runs`
  - [x] `spans`
- [x] Implement API key auth (`X-AgentOps-Key`)
- [x] Implement `POST /v1/ingest` with:
  - [x] batch JSON ingest
  - [x] validation for minimal envelope fields
  - [x] append-only write into `raw_events`
  - [x] accepted/rejected counts

### Phase 2: Derived run model and query APIs
- [x] Implement normalizer service from raw events to `runs`/`spans`
- [x] Trigger normalizer for affected runs after ingest (MVP inline)
- [x] Implement `GET /v1/runs`
- [x] Implement `GET /v1/runs/{run_id}`

### Phase 3+: placeholders for next execution cycles
- [x] Prompt version APIs
- [x] Replay APIs (llm-only stub, mocked provider execution)
- [x] Cost metrics endpoint
- [x] Python SDK v0.1 (core run/span tracking + ingest flush)
- [x] Basic dashboard UI

## Acceptance criteria for this execution
1. [x] Service starts with `uvicorn app.main:app`.
2. [x] Authenticated ingest accepts valid events and deduplicates retries by `event_id`.
3. [x] Listing runs returns normalized run summaries.
4. [x] Run detail returns spans timeline.

## Notes
- Server derives `project_id` from API key and does not trust `project.id` in event payload.
- In this iteration, normalization is synchronous post-ingest for simplicity.
