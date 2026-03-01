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
- [ ] Create `agentops-server` project structure
- [ ] Add FastAPI app entrypoint and router wiring
- [ ] Add configuration and DB session management
- [ ] Add SQLAlchemy models and indexes for:
  - [ ] `projects`
  - [ ] `api_keys`
  - [ ] `raw_events` with idempotency uniqueness `(project_id, event_id)`
  - [ ] `runs`
  - [ ] `spans`
- [ ] Implement API key auth (`X-AgentOps-Key`)
- [ ] Implement `POST /v1/ingest` with:
  - [ ] batch JSON ingest
  - [ ] validation for minimal envelope fields
  - [ ] append-only write into `raw_events`
  - [ ] accepted/rejected counts

### Phase 2: Derived run model and query APIs
- [ ] Implement normalizer service from raw events to `runs`/`spans`
- [ ] Trigger normalizer for affected runs after ingest (MVP inline)
- [ ] Implement `GET /v1/runs`
- [ ] Implement `GET /v1/runs/{run_id}`

### Phase 3+: placeholders for next execution cycles
- [ ] Prompt version APIs
- [ ] Replay APIs (llm-only)
- [ ] Cost metrics endpoint
- [ ] Python SDK v0.1
- [ ] Basic dashboard UI

## Acceptance criteria for this execution
1. Service starts with `uvicorn app.main:app`.
2. Authenticated ingest accepts valid events and deduplicates retries by `event_id`.
3. Listing runs returns normalized run summaries.
4. Run detail returns spans timeline.

## Notes
- Server derives `project_id` from API key and does not trust `project.id` in event payload.
- In this iteration, normalization is synchronous post-ingest for simplicity.
