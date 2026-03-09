from __future__ import annotations

from decimal import Decimal

import pytest

from cilly_trading.engine.telemetry import (
    CANONICAL_TELEMETRY_EVENT_TYPES,
    TELEMETRY_SCHEMA_VERSION,
    build_telemetry_event,
    serialize_telemetry_event,
)


def test_schema_validation_rejects_unknown_event_type() -> None:
    with pytest.raises(ValueError, match="unsupported telemetry event type"):
        build_telemetry_event(
            event="unknown.event",
            event_index=0,
            timestamp_utc="2026-01-01T00:00:00Z",
            payload={},
        )


def test_schema_validation_rejects_invalid_event_index() -> None:
    with pytest.raises(ValueError, match="event_index must be a non-negative integer"):
        build_telemetry_event(
            event="analysis_run.started",
            event_index=-1,
            timestamp_utc="2026-01-01T00:00:00Z",
            payload={},
        )


def test_serialization_is_deterministic_for_identical_events() -> None:
    first = build_telemetry_event(
        event="analysis_run.started",
        event_index=7,
        timestamp_utc="2026-02-01T00:00:00Z",
        payload={
            "list_payload": [Decimal("1.25"), {"z": 3, "a": 1}],
            "z_key": "later",
            "a_key": "first",
        },
    )
    second = build_telemetry_event(
        event="analysis_run.started",
        event_index=7,
        timestamp_utc="2026-02-01T00:00:00Z",
        payload={
            "z_key": "later",
            "a_key": "first",
            "list_payload": [Decimal("1.25"), {"a": 1, "z": 3}],
        },
    )

    assert first.payload == second.payload
    assert serialize_telemetry_event(first) == serialize_telemetry_event(second)
    assert serialize_telemetry_event(first) == (
        '{"component":"engine","event":"analysis_run.started","event_index":7,'
        '"payload":{"a_key":"first","list_payload":["1.25",{"a":1,"z":3}],"z_key":"later"},'
        '"schema_version":"cilly.engine.telemetry.v1","timestamp_utc":"2026-02-01T00:00:00Z"}'
    )


def test_event_type_coverage_contains_required_domains() -> None:
    required = {
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
    assert required.issubset(CANONICAL_TELEMETRY_EVENT_TYPES)


def test_schema_version_is_stable() -> None:
    event = build_telemetry_event(
        event="signal.generated",
        event_index=1,
        timestamp_utc="2026-02-01T00:00:01Z",
        payload={"signal_id": "sig-1"},
    )
    assert event.schema_version == TELEMETRY_SCHEMA_VERSION
    assert TELEMETRY_SCHEMA_VERSION == "cilly.engine.telemetry.v1"
