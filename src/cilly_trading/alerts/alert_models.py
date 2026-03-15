"""Deterministic alert event models and creation utilities.

Alert events are stable, structured envelopes that represent signal, strategy,
and runtime events before any routing or notification delivery occurs.

Schema contract:
- `schema_version`: alert schema version for downstream consumers.
- `event_id`: deterministic SHA-256 digest derived from the canonical event payload.
- `event_type`: stable domain event name such as `signal.generated`.
- `source_type`: origin category for the event (`signal`, `strategy`, `runtime`).
- `source_id`: deterministic identifier of the originating entity or process.
- `severity`: bounded alert severity level.
- `occurred_at`: ISO-8601 timestamp of the originating event.
- `symbol`: optional trading symbol when the event is market-specific.
- `strategy`: optional strategy identifier when available.
- `correlation_id`: optional deterministic correlation identifier.
- `payload`: structured event attributes used by downstream routing.
"""

from __future__ import annotations

import json
from datetime import datetime
from hashlib import sha256
from typing import Any, Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator

from cilly_trading.models import compute_signal_id


ALERT_EVENT_SCHEMA_VERSION = "1.0"

AlertSeverity = Literal["info", "warning", "critical"]
AlertSourceType = Literal["signal", "strategy", "runtime"]


def _normalize_payload(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value

    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key in sorted(value.keys(), key=str):
            if not isinstance(key, str):
                raise TypeError("alert payload keys must be strings")
            normalized[key] = _normalize_payload(value[key])
        return normalized

    if isinstance(value, (list, tuple)):
        return [_normalize_payload(item) for item in value]

    raise TypeError(f"unsupported alert payload type: {type(value).__name__}")


def _event_identity_payload(
    *,
    event_type: str,
    source_type: AlertSourceType,
    source_id: str,
    severity: AlertSeverity,
    occurred_at: str,
    symbol: str | None,
    strategy: str | None,
    correlation_id: str | None,
    payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    identity_payload: dict[str, Any] = {
        "schema_version": ALERT_EVENT_SCHEMA_VERSION,
        "event_type": event_type,
        "source_type": source_type,
        "source_id": source_id,
        "severity": severity,
        "occurred_at": occurred_at,
    }

    if symbol is not None:
        identity_payload["symbol"] = symbol
    if strategy is not None:
        identity_payload["strategy"] = strategy
    if correlation_id is not None:
        identity_payload["correlation_id"] = correlation_id
    if payload is not None:
        identity_payload["payload"] = _normalize_payload(payload)

    return identity_payload


def compute_alert_event_id(
    *,
    event_type: str,
    source_type: AlertSourceType,
    source_id: str,
    severity: AlertSeverity,
    occurred_at: str,
    symbol: str | None = None,
    strategy: str | None = None,
    correlation_id: str | None = None,
    payload: Mapping[str, Any] | None = None,
) -> str:
    identity_payload = _event_identity_payload(
        event_type=event_type,
        source_type=source_type,
        source_id=source_id,
        severity=severity,
        occurred_at=occurred_at,
        symbol=symbol,
        strategy=strategy,
        correlation_id=correlation_id,
        payload=payload,
    )
    serialized = json.dumps(
        identity_payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    digest = sha256(serialized.encode("utf-8")).hexdigest()
    return f"alert_{digest}"


class AlertEvent(BaseModel):
    schema_version: Literal["1.0"] = ALERT_EVENT_SCHEMA_VERSION
    event_id: str
    event_type: str = Field(min_length=1)
    source_type: AlertSourceType
    source_id: str = Field(min_length=1)
    severity: AlertSeverity
    occurred_at: str = Field(min_length=1)
    symbol: str | None = None
    strategy: str | None = None
    correlation_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid", frozen=True)

    @field_validator("occurred_at")
    @classmethod
    def validate_occurred_at(cls, value: str) -> str:
        if "T" not in value:
            raise ValueError("occurred_at must be an ISO-8601 timestamp string")

        normalized = value.replace("Z", "+00:00")
        try:
            datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise ValueError("occurred_at must be an ISO-8601 timestamp string") from exc
        return value


def create_alert_event(
    *,
    event_type: str,
    source_type: AlertSourceType,
    source_id: str,
    severity: AlertSeverity,
    occurred_at: str,
    symbol: str | None = None,
    strategy: str | None = None,
    correlation_id: str | None = None,
    payload: Mapping[str, Any] | None = None,
) -> AlertEvent:
    normalized_payload = _normalize_payload(payload or {})
    event_id = compute_alert_event_id(
        event_type=event_type,
        source_type=source_type,
        source_id=source_id,
        severity=severity,
        occurred_at=occurred_at,
        symbol=symbol,
        strategy=strategy,
        correlation_id=correlation_id,
        payload=normalized_payload,
    )
    return AlertEvent(
        event_id=event_id,
        event_type=event_type,
        source_type=source_type,
        source_id=source_id,
        severity=severity,
        occurred_at=occurred_at,
        symbol=symbol,
        strategy=strategy,
        correlation_id=correlation_id,
        payload=normalized_payload,
    )


def signal_to_alert_event(
    signal: Mapping[str, Any],
    *,
    event_type: str = "signal.generated",
    severity: AlertSeverity = "info",
    correlation_id: str | None = None,
    payload: Mapping[str, Any] | None = None,
) -> AlertEvent:
    timestamp = signal.get("timestamp")
    if not timestamp:
        raise ValueError("signal timestamp is required")

    source_id = str(signal.get("signal_id") or compute_signal_id(signal))
    signal_payload = {
        "data_source": signal.get("data_source"),
        "direction": signal.get("direction"),
        "market_type": signal.get("market_type"),
        "reasons": signal.get("reasons", []),
        "score": signal.get("score"),
        "stage": signal.get("stage"),
        "timeframe": signal.get("timeframe"),
    }
    if "confirmation_rule" in signal:
        signal_payload["confirmation_rule"] = signal.get("confirmation_rule")
    if "entry_zone" in signal:
        signal_payload["entry_zone"] = signal.get("entry_zone")
    if payload:
        signal_payload.update(payload)

    return create_alert_event(
        event_type=event_type,
        source_type="signal",
        source_id=source_id,
        severity=severity,
        occurred_at=str(timestamp),
        symbol=_optional_str(signal.get("symbol")),
        strategy=_optional_str(signal.get("strategy")),
        correlation_id=correlation_id,
        payload=signal_payload,
    )


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


__all__ = [
    "ALERT_EVENT_SCHEMA_VERSION",
    "AlertEvent",
    "AlertSeverity",
    "AlertSourceType",
    "compute_alert_event_id",
    "create_alert_event",
    "signal_to_alert_event",
]
