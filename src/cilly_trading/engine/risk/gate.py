"""Risk gate implementations and execution guardrails.

The module intentionally enforces bounded, non-live risk semantics. These
checks are deterministic guardrails for paper/backtest-style operation and do
not represent live-trading risk readiness.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import inspect
from math import isfinite
from typing import Any, Mapping, Sequence

from risk.contracts import RiskDecision, RiskEvaluationRequest, RiskGate

from cilly_trading.engine.logging import emit_structured_engine_log
from cilly_trading.engine.telemetry.schema import (
    TelemetryEvent,
    build_telemetry_event,
)
from cilly_trading.non_live_evaluation_contract import (
    NonLiveEvaluationEvidence,
    RISK_FRAMEWORK_REASON_TO_CANONICAL_REJECTION_REASON,
    normalize_risk_rejection_reason_code,
    resolve_risk_rejection_reason_precedence,
)
from cilly_trading.risk_framework.allocation_rules import RiskLimits as FrameworkRiskLimits
from cilly_trading.risk_framework.contract import (
    RiskEvaluationRequest as FrameworkRiskEvaluationRequest,
    RiskEvaluationResponse as FrameworkRiskEvaluationResponse,
)
from cilly_trading.risk_framework.risk_evaluator import evaluate_risk as evaluate_framework_risk

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

RISK_FRAMEWORK_REASON_CODES: dict[str, str] = {
    "approved: within_risk_limits": "approved:risk_framework_within_limits",
    **dict(RISK_FRAMEWORK_REASON_TO_CANONICAL_REJECTION_REASON),
}
_RISK_DECISION_ACCEPTS_POLICY_EVIDENCE = (
    "policy_evidence" in inspect.signature(RiskDecision).parameters
)
_COVERED_EVIDENCE_SCOPES: frozenset[str] = frozenset(
    {
        "trade",
        "symbol",
        "strategy",
        "portfolio",
        "runtime",
    }
)

_RISK_REASON_TO_EVIDENCE_METADATA: dict[str, tuple[str, str, str]] = {
    "rejected: kill_switch_enabled": ("boundary", "runtime", "kill_switch_enabled"),
    "rejected: stop_loss_evidence_missing": (
        "boundary",
        "trade",
        "stop_loss_evidence_required",
    ),
    "rejected: stop_loss_evidence_invalid": (
        "boundary",
        "trade",
        "stop_loss_evidence_valid",
    ),
    "rejected: position_size_exceeds_stop_loss_budget": (
        "cap",
        "trade",
        "stop_loss_position_size",
    ),
    "rejected: max_trade_risk_exceeded": ("cap", "trade", "max_trade_risk"),
    "rejected: strategy_risk_budget_exceeded": (
        "cap",
        "strategy",
        "strategy_risk_budget",
    ),
    "rejected: symbol_risk_budget_exceeded": ("cap", "symbol", "symbol_risk_budget"),
    "rejected: portfolio_risk_budget_exceeded": (
        "cap",
        "portfolio",
        "portfolio_risk_budget",
    ),
    "rejected: max_position_size_exceeded": ("cap", "trade", "max_position_size"),
    "rejected: max_account_exposure_pct_exceeded": (
        "cap",
        "portfolio",
        "max_account_exposure_pct",
    ),
    "rejected: max_strategy_exposure_pct_exceeded": (
        "cap",
        "strategy",
        "max_strategy_exposure_pct",
    ),
    "rejected: max_symbol_exposure_pct_exceeded": (
        "cap",
        "symbol",
        "max_symbol_exposure_pct",
    ),
}


class RiskEvidenceDisciplineError(ValueError):
    """Raised when bounded risk evidence is missing or contradictory."""


def _safe_pct(numerator: float, denominator: float) -> float | None:
    if denominator == 0.0:
        return None
    return numerator / denominator


def _risk_limit_notional(account_equity: float, limit_pct: float | None) -> float:
    if limit_pct is None:
        return float("inf")
    return abs(account_equity) * limit_pct


def _extract_policy_evidence(
    framework_response: FrameworkRiskEvaluationResponse,
) -> tuple[Any, ...]:
    """Return policy evidence when present; default to empty evidence tuple."""

    evidence = getattr(framework_response, "policy_evidence", ())
    if evidence is None:
        return ()
    if isinstance(evidence, tuple):
        return evidence
    if isinstance(evidence, list):
        return tuple(evidence)
    return ()


def _read_evidence_field(evidence: object, field_name: str) -> object | None:
    if isinstance(evidence, Mapping):
        return evidence.get(field_name)
    return getattr(evidence, field_name, None)


def _collect_covered_rejection_reason_codes(
    policy_evidence: tuple[Any, ...],
) -> tuple[str, ...]:
    rejection_reason_codes: list[str] = []
    for evidence in policy_evidence:
        scope = _read_evidence_field(evidence, "scope")
        if scope not in _COVERED_EVIDENCE_SCOPES:
            continue
        decision = _read_evidence_field(evidence, "decision")
        if decision not in {"approve", "reject"}:
            raise RiskEvidenceDisciplineError(
                "covered risk policy evidence must declare decision='approve' or decision='reject'"
            )
        reason_code = _read_evidence_field(evidence, "reason_code")
        if not isinstance(reason_code, str) or not reason_code:
            raise RiskEvidenceDisciplineError(
                "covered risk policy evidence must include non-empty reason_code"
            )
        if decision == "approve":
            continue
        normalize_risk_rejection_reason_code(reason_code)
        rejection_reason_codes.append(reason_code)
    return tuple(rejection_reason_codes)


def _validate_covered_policy_evidence(policy_evidence: tuple[Any, ...]) -> None:
    for evidence in policy_evidence:
        scope = _read_evidence_field(evidence, "scope")
        if scope not in _COVERED_EVIDENCE_SCOPES:
            continue
        decision = _read_evidence_field(evidence, "decision")
        if decision not in {"approve", "reject"}:
            raise RiskEvidenceDisciplineError(
                "covered risk policy evidence must declare decision='approve' or decision='reject'"
            )
        reason_code = _read_evidence_field(evidence, "reason_code")
        if not isinstance(reason_code, str) or not reason_code:
            raise RiskEvidenceDisciplineError(
                "covered risk policy evidence must include non-empty reason_code"
            )
        if decision == "reject":
            normalize_risk_rejection_reason_code(reason_code)
        elif reason_code.startswith("rejected:"):
            raise RiskEvidenceDisciplineError(
                "covered risk policy evidence contradicts rejection discipline: decision='approve'"
            )


def _first_rejection_evidence_limit(
    policy_evidence: tuple[Any, ...],
    reason_code: str,
) -> float | None:
    for evidence in policy_evidence:
        if _read_evidence_field(evidence, "reason_code") != reason_code:
            continue
        limit_value = _read_evidence_field(evidence, "limit_value")
        if isinstance(limit_value, int | float):
            return float(limit_value)
    return None


def _build_synthetic_rejection_evidence(
    *,
    reason_code: str,
    observed_value: float,
    limit_value: float,
) -> NonLiveEvaluationEvidence:
    metadata = _RISK_REASON_TO_EVIDENCE_METADATA.get(reason_code)
    if metadata is None:
        raise RiskEvidenceDisciplineError(
            f"cannot synthesize bounded risk evidence for unsupported reason code: {reason_code}"
        )
    semantic, scope, rule_code = metadata
    return NonLiveEvaluationEvidence(
        decision="reject",
        semantic=semantic,  # type: ignore[arg-type]
        scope=scope,  # type: ignore[arg-type]
        rule_code=rule_code,
        reason_code=reason_code,
        observed_value=observed_value,
        limit_value=limit_value,
    )


def _build_risk_decision(
    *,
    decision: str,
    score: float,
    max_allowed: float,
    reason: str,
    timestamp: datetime,
    rule_version: str,
    policy_evidence: tuple[Any, ...],
) -> RiskDecision:
    kwargs: dict[str, Any] = {
        "decision": decision,
        "score": score,
        "max_allowed": max_allowed,
        "reason": reason,
        "timestamp": timestamp,
        "rule_version": rule_version,
    }
    if _RISK_DECISION_ACCEPTS_POLICY_EVIDENCE:
        kwargs["policy_evidence"] = policy_evidence
    return RiskDecision(**kwargs)


def adapt_risk_framework_response_to_risk_decision(
    *,
    framework_request: FrameworkRiskEvaluationRequest,
    framework_response: FrameworkRiskEvaluationResponse,
    limits: FrameworkRiskLimits,
    strategy_exposure: float,
    symbol_exposure: float,
    rule_version: str,
    evaluated_at: datetime | None = None,
) -> RiskDecision:
    """Map deterministic risk-framework outcomes into execution risk decisions."""

    normalized_equity = abs(framework_request.account_equity)
    normalized_proposed = abs(framework_request.proposed_position_size)
    normalized_strategy = abs(strategy_exposure)
    normalized_symbol = abs(symbol_exposure)
    policy_evidence = _extract_policy_evidence(framework_response)

    reason = framework_response.reason
    if reason == "approved: within_risk_limits":
        _validate_covered_policy_evidence(policy_evidence)
        if _collect_covered_rejection_reason_codes(policy_evidence):
            raise RiskEvidenceDisciplineError(
                "approved risk decision contains covered rejection evidence rows"
            )
        decision = "APPROVED"
        score = float(framework_response.risk_score)
        max_allowed = float(limits.max_account_exposure_pct)
        decision_reason = RISK_FRAMEWORK_REASON_CODES[reason]
    else:
        decision = "REJECTED"
        try:
            normalize_risk_rejection_reason_code(reason)
        except ValueError as exc:
            raise ValueError(
                f"unsupported risk-framework reason for execution mapping: {framework_response.reason}"
            ) from exc
        _validate_covered_policy_evidence(policy_evidence)
        evidence_reason_codes = _collect_covered_rejection_reason_codes(policy_evidence)
        if not evidence_reason_codes:
            evidence_reason_codes = (reason,)
        try:
            precedence_candidates = [reason, *evidence_reason_codes]
            decision_reason = resolve_risk_rejection_reason_precedence(precedence_candidates)
        except ValueError as exc:
            raise ValueError(
                f"unsupported risk-framework reason for execution mapping: {framework_response.reason}"
            ) from exc
        if reason == "rejected: kill_switch_enabled":
            score = float("inf")
            max_allowed = 0.0
        elif reason == "rejected: max_position_size_exceeded":
            score = float(normalized_proposed)
            max_allowed = float(limits.max_position_size)
        elif reason == "rejected: stop_loss_evidence_missing":
            score = float("inf")
            max_allowed = 0.0
        elif reason == "rejected: stop_loss_evidence_invalid":
            score = float("inf")
            max_allowed = 0.0
        elif reason == "rejected: position_size_exceeds_stop_loss_budget":
            score = float(normalized_proposed)
            max_allowed = _first_rejection_evidence_limit(policy_evidence, reason) or 0.0
        elif reason == "rejected: max_trade_risk_exceeded":
            score = float(framework_response.risk_score)
            max_allowed = _risk_limit_notional(
                normalized_equity,
                limits.max_trade_risk_pct,
            )
        elif reason == "rejected: strategy_risk_budget_exceeded":
            score = float(framework_response.risk_score)
            max_allowed = _risk_limit_notional(
                normalized_equity,
                limits.max_strategy_risk_pct,
            )
        elif reason == "rejected: symbol_risk_budget_exceeded":
            score = float(framework_response.risk_score)
            max_allowed = _risk_limit_notional(
                normalized_equity,
                limits.max_symbol_risk_pct,
            )
        elif reason == "rejected: portfolio_risk_budget_exceeded":
            score = float(framework_response.risk_score)
            max_allowed = _risk_limit_notional(
                normalized_equity,
                limits.max_portfolio_risk_pct,
            )
        elif reason == "rejected: max_account_exposure_pct_exceeded":
            score = float(framework_response.risk_score)
            max_allowed = float(limits.max_account_exposure_pct)
        elif reason == "rejected: max_strategy_exposure_pct_exceeded":
            _pct = _safe_pct(normalized_strategy + normalized_proposed, normalized_equity)
            score = _pct if _pct is not None else 0.0
            max_allowed = float(limits.max_strategy_exposure_pct)
        elif reason == "rejected: max_symbol_exposure_pct_exceeded":
            _pct = _safe_pct(normalized_symbol + normalized_proposed, normalized_equity)
            score = _pct if _pct is not None else 0.0
            max_allowed = float(limits.max_symbol_exposure_pct)
        else:  # pragma: no cover - guarded by reason map above
            raise ValueError(f"unsupported risk-framework reason: {reason}")
        if not _collect_covered_rejection_reason_codes(policy_evidence):
            policy_evidence = (
                _build_synthetic_rejection_evidence(
                    reason_code=reason,
                    observed_value=score,
                    limit_value=max_allowed,
                ),
            )

    if framework_response.approved != (decision == "APPROVED"):
        raise ValueError("risk-framework approval flag conflicts with mapped execution decision")

    timestamp = evaluated_at or datetime.now(tz=timezone.utc)
    if (
        timestamp.tzinfo is None
        or timestamp.utcoffset() is None
        or timestamp.utcoffset() != timezone.utc.utcoffset(timestamp)
    ):
        raise ValueError("evaluated_at must be timezone-aware and in UTC")

    return _build_risk_decision(
        decision=decision,
        score=score,
        max_allowed=max_allowed,
        reason=decision_reason,
        timestamp=timestamp,
        rule_version=rule_version,
        policy_evidence=policy_evidence,
    )


def evaluate_risk_framework_execution_decision(
    *,
    request_id: str,
    strategy_id: str,
    symbol: str,
    proposed_position_size: float,
    account_equity: float,
    current_exposure: float,
    strategy_exposure: float,
    symbol_exposure: float,
    limits: FrameworkRiskLimits,
    entry_price: float | None = None,
    stop_loss_price: float | None = None,
    strategy_risk_used: float = 0.0,
    symbol_risk_used: float = 0.0,
    portfolio_risk_used: float = 0.0,
    require_bounded_risk_evidence: bool = False,
    rule_version: str = "risk-framework-v1",
    config: Mapping[str, object] | None = None,
    evaluated_at: datetime | None = None,
) -> RiskDecision:
    """Evaluate canonical risk-framework limits and return RiskDecision contract."""

    framework_request = FrameworkRiskEvaluationRequest(
        strategy_id=strategy_id,
        symbol=symbol,
        proposed_position_size=proposed_position_size,
        account_equity=account_equity,
        current_exposure=current_exposure,
        entry_price=entry_price,
        stop_loss_price=stop_loss_price,
        strategy_risk_used=strategy_risk_used,
        symbol_risk_used=symbol_risk_used,
        portfolio_risk_used=portfolio_risk_used,
        require_bounded_risk_evidence=require_bounded_risk_evidence,
    )
    framework_response = evaluate_framework_risk(
        framework_request,
        limits=limits,
        strategy_exposure=strategy_exposure,
        symbol_exposure=symbol_exposure,
        config=dict(config) if config is not None else None,
    )
    return adapt_risk_framework_response_to_risk_decision(
        framework_request=framework_request,
        framework_response=framework_response,
        limits=limits,
        strategy_exposure=strategy_exposure,
        symbol_exposure=symbol_exposure,
        rule_version=rule_version,
        evaluated_at=evaluated_at,
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

        threshold_limits = FrameworkRiskLimits(
            max_account_exposure_pct=1.0,
            max_position_size=max_allowed,
            max_strategy_exposure_pct=1.0,
            max_symbol_exposure_pct=1.0,
        )
        return evaluate_risk_framework_execution_decision(
            request_id=request.request_id,
            strategy_id=request.strategy_id,
            symbol=request.symbol,
            proposed_position_size=score,
            account_equity=max_allowed,
            current_exposure=0.0,
            strategy_exposure=0.0,
            symbol_exposure=0.0,
            limits=threshold_limits,
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
    "RISK_FRAMEWORK_REASON_CODES",
    "RiskEvidenceDisciplineError",
    "RiskApprovalMissingError",
    "RiskRejectedError",
    "ThresholdRiskGate",
    "adapt_risk_framework_response_to_risk_decision",
    "build_guard_trigger_telemetry_event",
    "build_guard_trigger_telemetry_events",
    "enforce_approved_risk_decision",
    "evaluate_risk_framework_execution_decision",
    "resolve_runtime_guard_type",
]
