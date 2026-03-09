"""Canonical telemetry event schema and deterministic serialization."""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Mapping

TELEMETRY_SCHEMA_VERSION = "cilly.engine.telemetry.v1"

# Canonical event names by required domain:
# - analysis runs
# - signal generation
# - order submission
# - guard triggers
# - provider failover
CANONICAL_TELEMETRY_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "analysis_run.started",
        "analysis_run.completed",
        "signal.generated",
        "order_submission.attempt",
        "order_submission.executed",
        "guard.triggered",
        "provider_failover.attempt_failed",
        "provider_failover.exhausted",
        "provider_failover.recovered",
    }
)


@dataclass(frozen=True)
class TelemetryEvent:
    """Canonical telemetry event."""

    schema_version: str
    component: str
    event: str
    event_index: int
    timestamp_utc: str
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "component": self.component,
            "event": self.event,
            "event_index": self.event_index,
            "payload": self.payload,
            "schema_version": self.schema_version,
            "timestamp_utc": self.timestamp_utc,
        }


def build_telemetry_event(
    *,
    event: str,
    event_index: int,
    timestamp_utc: str,
    payload: Mapping[str, Any] | None = None,
) -> TelemetryEvent:
    """Build and validate a canonical telemetry event."""

    if event not in CANONICAL_TELEMETRY_EVENT_TYPES:
        raise ValueError(f"unsupported telemetry event type: {event}")
    if not isinstance(event_index, int) or event_index < 0:
        raise ValueError("event_index must be a non-negative integer")
    if not isinstance(timestamp_utc, str) or not timestamp_utc.strip():
        raise ValueError("timestamp_utc must be a non-empty string")

    canonical_payload = _normalize_mapping(payload or {})
    return TelemetryEvent(
        schema_version=TELEMETRY_SCHEMA_VERSION,
        component="engine",
        event=event,
        event_index=event_index,
        timestamp_utc=timestamp_utc,
        payload=canonical_payload,
    )


def serialize_telemetry_event(event: TelemetryEvent) -> str:
    """Serialize a telemetry event in deterministic canonical JSON format."""

    return json.dumps(
        event.to_dict(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def _normalize_mapping(mapping: Mapping[str, Any]) -> dict[str, Any]:
    return {
        str(key): _normalize_value(value)
        for key, value in sorted(mapping.items(), key=lambda item: str(item[0]))
    }


def _normalize_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Mapping):
        return _normalize_mapping(value)
    if isinstance(value, (list, tuple)):
        return [_normalize_value(item) for item in value]
    return str(value)
