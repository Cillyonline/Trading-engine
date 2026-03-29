"""Risk gate implementations and execution guardrails.

The module intentionally enforces bounded, non-live risk semantics. These
checks are deterministic guardrails for paper/backtest-style operation and do
not represent live-trading risk readiness.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite
from typing import Any, Mapping, Sequence

from risk.contracts import RiskDecision, RiskEvaluationRequest, RiskGate

from cilly_trading.engine.logging import emit_structured_engine_log
from cilly_trading.engine.telemetry.schema import (
    TelemetryEvent,
    build_telemetry_event,
)

GUARD_TRIGGER_EVENT = "guard.triggered"
GUARD_TRIGGER_PAYLOAD_KEY = "guard_type"
GUARD_TRIGGER_TYPES: frozenset[str] = frozenset(
    {
        "kill_switch",
        "drawdown",
        "daily_loss",
        "emergency",
    }
)

_GUARD_EMISSION_ORDER: tuple[str, ...] = (
    "kill_switch",
    "drawdown",
    "daily_loss",
    "emergency",
)


class RiskApprovalMissingError(ValueError):
    """Raised when execution is attempted without an explicit risk approval."""


class RiskRejectedError(ValueError):
    """Raised when execution is attempted with a non-approved risk decision."""


@dataclass(frozen=True)
class ThresholdRiskGate(RiskGate):
    """Bounded non-live risk gate using a fixed per-request notional threshold."""

    max_notional_usd: float
    rule_version: str = "threshold-v1"

    def evaluate(self, request: RiskEvaluationRequest) -> RiskDecision:
        max_allowed = float(self.max_notional_usd)
        if not isfinite(max_allowed) or max_allowed <= 0.0:
            raise ValueError(
                "ThresholdRiskGate requires max_notional_usd to be finite and > 0 for bounded non-live operation"
            )

        score = float(request.notional_usd)
        if not isfinite(score) or score < 0.0:
            raise ValueError(
                "RiskEvaluationRequest.notional_usd must be finite and >= 0 for bounded non-live operation"
            )

        decision = "APPROVED" if score <= max_allowed else "REJECTED"
        reason = (
            "bounded non-live notional within threshold"
            if decision == "APPROVED"
            else "bounded non-live notional exceeds threshold"
        )
        return RiskDecision(
            decision=decision,
            score=score,
            max_allowed=max_allowed,
            reason=reason,
            timestamp=datetime.now(tz=timezone.utc),
            rule_version=self.rule_version,
        )


def build_guard_trigger_telemetry_event(
    *,
    guard_type: str,
    event_index: int,
    timestamp_utc: str,
    payload: Mapping[str, Any] | None = None,
) -> TelemetryEvent:
    """Build a canonical telemetry event for a single guard trigger."""

    if guard_type not in GUARD_TRIGGER_TYPES:
        raise ValueError(f"unsupported guard trigger type: {guard_type}")
    merged_payload = dict(payload or {})
    merged_payload[GUARD_TRIGGER_PAYLOAD_KEY] = guard_type
    return build_telemetry_event(
        event=GUARD_TRIGGER_EVENT,
        event_index=event_index,
        timestamp_utc=timestamp_utc,
        payload=merged_payload,
    )


def build_guard_trigger_telemetry_events(
    *,
    guard_types: Sequence[str],
    start_event_index: int,
    timestamp_utc: str,
    payload: Mapping[str, Any] | None = None,
) -> tuple[TelemetryEvent, ...]:
    """Build deterministic guard-trigger telemetry events from triggered guard types."""

    requested = frozenset(guard_types)
    invalid = sorted(requested.difference(GUARD_TRIGGER_TYPES))
    if invalid:
        raise ValueError(f"unsupported guard trigger type(s): {','.join(invalid)}")
    ordered_guard_types = tuple(
        guard_type
        for guard_type in _GUARD_EMISSION_ORDER
        if guard_type in requested
    )
    return tuple(
        build_guard_trigger_telemetry_event(
            guard_type=guard_type,
            event_index=start_event_index + index,
            timestamp_utc=timestamp_utc,
            payload=payload,
        )
        for index, guard_type in enumerate(ordered_guard_types)
    )


def resolve_runtime_guard_type(
    *,
    request: RiskEvaluationRequest,
    guard_source: str,
) -> str:
    """Resolve deterministic runtime guard type for orchestrated guard events."""

    if guard_source != "risk_gate":
        return "emergency"
    guard_type = request.metadata.get(GUARD_TRIGGER_PAYLOAD_KEY)
    if guard_type in GUARD_TRIGGER_TYPES:
        return guard_type
    return "emergency"


def enforce_approved_risk_decision(risk_decision: RiskDecision | None) -> RiskDecision:
    """Require an explicit APPROVED risk decision before execution continues."""

    if risk_decision is None:
        _emit_guard_trigger_log(
            guard_type="emergency",
            payload={
                "guard_source": "risk_gate",
                "reason": "risk_decision_missing",
            },
        )
        raise RiskApprovalMissingError(
            "Execution requires explicit risk approval: risk_decision is missing"
        )

    if risk_decision.decision == "APPROVED":
        return risk_decision

    if risk_decision.decision == "REJECTED":
        _emit_guard_trigger_log(
            guard_type="emergency",
            payload={
                "guard_source": "risk_gate",
                "reason": risk_decision.reason,
                "risk_decision": risk_decision.decision,
                "rule_version": risk_decision.rule_version,
            },
        )
        raise RiskRejectedError(
            "Execution blocked by risk gate: risk_decision.decision=REJECTED"
        )

    _emit_guard_trigger_log(
        guard_type="emergency",
        payload={
            "guard_source": "risk_gate",
            "reason": "invalid_risk_decision_value",
            "risk_decision": str(risk_decision.decision),
        },
    )
    raise ValueError(
        "Execution blocked by risk gate: risk_decision.decision must be APPROVED or REJECTED"
    )


def _emit_guard_trigger_log(*, guard_type: str, payload: Mapping[str, Any]) -> None:
    emit_structured_engine_log(
        GUARD_TRIGGER_EVENT,
        payload={
            GUARD_TRIGGER_PAYLOAD_KEY: guard_type,
            **dict(payload),
        },
    )


__all__ = [
    "RiskApprovalMissingError",
    "RiskRejectedError",
    "ThresholdRiskGate",
    "build_guard_trigger_telemetry_event",
    "build_guard_trigger_telemetry_events",
    "enforce_approved_risk_decision",
    "resolve_runtime_guard_type",
]
