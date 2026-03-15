from __future__ import annotations

import pytest
from pydantic import ValidationError

from cilly_trading.alerts import (
    ALERT_EVENT_SCHEMA_VERSION,
    AlertEvent,
    compute_alert_event_id,
    create_alert_event,
    signal_to_alert_event,
)
from cilly_trading.models import compute_signal_id


def _signal_fixture() -> dict[str, object]:
    return {
        "symbol": "AAPL",
        "strategy": "rsi2",
        "direction": "long",
        "score": 0.87,
        "timestamp": "2024-01-01T10:30:00Z",
        "stage": "entry_confirmed",
        "entry_zone": {"from_": 101.0, "to": 102.5},
        "confirmation_rule": "rsi_cross",
        "timeframe": "D1",
        "market_type": "stock",
        "data_source": "yahoo",
        "reasons": [
            {
                "reason_id": "sr_1",
                "reason_type": "INDICATOR_THRESHOLD",
                "signal_id": "signal-1",
                "rule_ref": {"rule_id": "rule-1", "rule_version": "1.0.0"},
                "data_refs": [
                    {
                        "data_type": "INDICATOR_VALUE",
                        "data_id": "rsi-14",
                        "value": 27.5,
                        "timestamp": "2024-01-01T10:30:00Z",
                    }
                ],
                "ordering_key": 1,
            }
        ],
    }


def test_alert_event_id_is_deterministic_and_order_invariant() -> None:
    first = compute_alert_event_id(
        event_type="signal.generated",
        source_type="signal",
        source_id="signal-1",
        severity="info",
        occurred_at="2024-01-01T10:30:00Z",
        symbol="AAPL",
        strategy="rsi2",
        payload={"b": 2, "a": {"d": 4, "c": 3}},
    )
    second = compute_alert_event_id(
        event_type="signal.generated",
        source_type="signal",
        source_id="signal-1",
        severity="info",
        occurred_at="2024-01-01T10:30:00Z",
        symbol="AAPL",
        strategy="rsi2",
        payload={"a": {"c": 3, "d": 4}, "b": 2},
    )

    assert first == second


def test_alert_event_id_changes_when_identity_changes() -> None:
    baseline = compute_alert_event_id(
        event_type="signal.generated",
        source_type="signal",
        source_id="signal-1",
        severity="info",
        occurred_at="2024-01-01T10:30:00Z",
    )
    changed = compute_alert_event_id(
        event_type="signal.generated",
        source_type="signal",
        source_id="signal-1",
        severity="critical",
        occurred_at="2024-01-01T10:30:00Z",
    )

    assert baseline != changed


def test_create_alert_event_builds_schema_stable_model() -> None:
    event = create_alert_event(
        event_type="runtime.guard_triggered",
        source_type="runtime",
        source_id="guard-17",
        severity="warning",
        occurred_at="2024-01-01T10:30:00Z",
        payload={"guard": "position_limit", "triggered": True},
    )

    assert event.schema_version == ALERT_EVENT_SCHEMA_VERSION
    assert event.event_id.startswith("alert_")
    assert event.payload == {"guard": "position_limit", "triggered": True}


def test_alert_event_schema_rejects_additional_fields() -> None:
    with pytest.raises(ValidationError):
        AlertEvent.model_validate(
            {
                "schema_version": "1.0",
                "event_id": "alert_1",
                "event_type": "signal.generated",
                "source_type": "signal",
                "source_id": "signal-1",
                "severity": "info",
                "occurred_at": "2024-01-01T10:30:00Z",
                "payload": {},
                "unexpected": True,
            }
        )


def test_alert_event_accepts_iso8601_occurred_at() -> None:
    event = create_alert_event(
        event_type="runtime.guard_triggered",
        source_type="runtime",
        source_id="guard-17",
        severity="warning",
        occurred_at="2024-01-01T10:30:00Z",
        payload={},
    )

    assert event.occurred_at == "2024-01-01T10:30:00Z"


def test_alert_event_rejects_invalid_occurred_at() -> None:
    with pytest.raises(ValidationError, match="occurred_at"):
        create_alert_event(
            event_type="runtime.guard_triggered",
            source_type="runtime",
            source_id="guard-17",
            severity="warning",
            occurred_at="not-a-timestamp",
            payload={},
        )


def test_signal_to_alert_event_uses_existing_signal_id() -> None:
    signal = _signal_fixture()
    signal["signal_id"] = "signal-existing"

    event = signal_to_alert_event(signal)

    assert event.source_type == "signal"
    assert event.source_id == "signal-existing"
    assert event.symbol == "AAPL"
    assert event.strategy == "rsi2"
    assert event.payload["stage"] == "entry_confirmed"
    assert event.payload["reasons"] == signal["reasons"]


def test_signal_to_alert_event_computes_signal_id_when_missing() -> None:
    signal = _signal_fixture()

    event = signal_to_alert_event(signal)

    assert event.source_id == compute_signal_id(signal)


def test_signal_to_alert_event_requires_timestamp() -> None:
    signal = _signal_fixture()
    signal.pop("timestamp")

    with pytest.raises(ValueError, match="timestamp"):
        signal_to_alert_event(signal)
