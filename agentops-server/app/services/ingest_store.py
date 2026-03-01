from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.tables import RawEvent

VALID_EVENT_TYPES = {"run_started", "span_started", "span_finished", "run_finished"}


@dataclass
class IngestResult:
    accepted: int = 0
    rejected: int = 0
    duplicates: int = 0
    errors: list[str] = field(default_factory=list)
    run_ids: set[str] = field(default_factory=set)


def _parse_iso8601(timestamp: str) -> datetime:
    if timestamp.endswith("Z"):
        timestamp = timestamp[:-1] + "+00:00"
    parsed = datetime.fromisoformat(timestamp)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _validate_event(event: dict[str, Any]) -> tuple[bool, str | None]:
    required = ["event_id", "event_type", "timestamp", "context", "payload"]
    missing = [field for field in required if field not in event]
    if missing:
        return False, f"Missing required fields: {', '.join(missing)}"

    event_type = event.get("event_type")
    if event_type not in VALID_EVENT_TYPES:
        return False, f"Unsupported event_type: {event_type}"

    context = event.get("context") or {}
    if not context.get("run_id"):
        return False, "Missing context.run_id"

    return True, None


def ingest_events(db: Session, *, project_id: str, events: list[dict[str, Any]]) -> IngestResult:
    result = IngestResult()

    for idx, event in enumerate(events):
        if not isinstance(event, dict):
            result.rejected += 1
            result.errors.append(f"event[{idx}] must be object")
            continue

        is_valid, error = _validate_event(event)
        if not is_valid:
            result.rejected += 1
            result.errors.append(f"event[{idx}] invalid: {error}")
            continue

        context = event.get("context") or {}
        sdk = event.get("sdk") or {}
        run_id = context.get("run_id")

        try:
            event_ts = _parse_iso8601(str(event["timestamp"]))
        except ValueError:
            result.rejected += 1
            result.errors.append(f"event[{idx}] invalid timestamp")
            continue

        row = RawEvent(
            project_id=project_id,
            event_id=str(event["event_id"]),
            event_type=str(event["event_type"]),
            event_ts=event_ts,
            run_id=run_id,
            span_id=context.get("span_id"),
            trace_id=context.get("trace_id"),
            payload_json=event.get("payload") or {},
            sdk_name=sdk.get("name"),
            sdk_version=sdk.get("version"),
        )

        try:
            with db.begin_nested():
                db.add(row)
                db.flush()
            result.accepted += 1
            result.run_ids.add(run_id)
        except IntegrityError:
            result.duplicates += 1

    return result
