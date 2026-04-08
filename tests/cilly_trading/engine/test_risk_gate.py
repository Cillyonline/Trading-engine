from __future__ import annotations

import math
from datetime import datetime, timezone

import pytest
from risk.contracts import RiskEvaluationRequest

from cilly_trading.engine.risk import (
    ThresholdRiskGate,
    adapt_risk_framework_response_to_risk_decision,
    evaluate_risk_framework_execution_decision,
)
from cilly_trading.risk_framework.allocation_rules import RiskLimits
from cilly_trading.risk_framework.contract import (
    RiskEvaluationRequest as FrameworkRiskEvaluationRequest,
    RiskEvaluationResponse as FrameworkRiskEvaluationResponse,
)


def test_threshold_risk_gate_returns_approved_for_within_threshold() -> None:
    gate = ThresholdRiskGate(max_notional_usd=1000.0)

    decision = gate.evaluate(
        RiskEvaluationRequest(
            request_id="req-1",
            strategy_id="strat-a",
            symbol="AAPL",
            notional_usd=750.0,
            metadata={},
        )
    )

    assert decision.decision == "APPROVED"


def test_threshold_risk_gate_returns_rejected_for_above_threshold() -> None:
    gate = ThresholdRiskGate(max_notional_usd=1000.0)

    decision = gate.evaluate(
        RiskEvaluationRequest(
            request_id="req-2",
            strategy_id="strat-a",
            symbol="AAPL",
            notional_usd=1500.0,
            metadata={},
        )
    )

    assert decision.decision == "REJECTED"


@pytest.mark.parametrize("max_notional", [0.0, -1.0, math.inf, math.nan])
def test_threshold_risk_gate_rejects_unbounded_threshold(max_notional: float) -> None:
    gate = ThresholdRiskGate(max_notional_usd=max_notional)

    with pytest.raises(ValueError, match="max_notional_usd"):
        gate.evaluate(
            RiskEvaluationRequest(
                request_id="req-bad-threshold",
                strategy_id="strat-a",
                symbol="AAPL",
                notional_usd=100.0,
                metadata={},
            )
        )


@pytest.mark.parametrize("notional", [-1.0, math.inf, math.nan])
def test_threshold_risk_gate_rejects_unbounded_notional(notional: float) -> None:
    gate = ThresholdRiskGate(max_notional_usd=1000.0)

    with pytest.raises(ValueError, match="notional_usd"):
        gate.evaluate(
            RiskEvaluationRequest(
                request_id="req-bad-notional",
                strategy_id="strat-a",
                symbol="AAPL",
                notional_usd=notional,
                metadata={},
            )
        )


def _framework_limits() -> RiskLimits:
    return RiskLimits(
        max_account_exposure_pct=0.80,
        max_position_size=500.0,
        max_strategy_exposure_pct=0.30,
        max_symbol_exposure_pct=0.20,
    )


def _framework_request() -> FrameworkRiskEvaluationRequest:
    return FrameworkRiskEvaluationRequest(
        strategy_id="strategy-a",
        symbol="AAPL",
        proposed_position_size=400.0,
        account_equity=2000.0,
        current_exposure=800.0,
    )


@pytest.mark.parametrize(
    ("framework_reason", "approved", "risk_score", "expected_decision", "expected_reason"),
    [
        (
            "approved: within_risk_limits",
            True,
            0.60,
            "APPROVED",
            "approved:risk_framework_within_limits",
        ),
        (
            "rejected: kill_switch_enabled",
            False,
            float("inf"),
            "REJECTED",
            "rejected:risk_framework_kill_switch_enabled",
        ),
        (
            "rejected: max_position_size_exceeded",
            False,
            0.60,
            "REJECTED",
            "rejected:risk_framework_max_position_size_exceeded",
        ),
        (
            "rejected: max_account_exposure_pct_exceeded",
            False,
            0.90,
            "REJECTED",
            "rejected:risk_framework_max_account_exposure_pct_exceeded",
        ),
        (
            "rejected: max_strategy_exposure_pct_exceeded",
            False,
            0.60,
            "REJECTED",
            "rejected:risk_framework_max_strategy_exposure_pct_exceeded",
        ),
        (
            "rejected: max_symbol_exposure_pct_exceeded",
            False,
            0.60,
            "REJECTED",
            "rejected:risk_framework_max_symbol_exposure_pct_exceeded",
        ),
    ],
)
def test_adapter_maps_risk_framework_reason_codes_deterministically(
    framework_reason: str,
    approved: bool,
    risk_score: float,
    expected_decision: str,
    expected_reason: str,
) -> None:
    decision = adapt_risk_framework_response_to_risk_decision(
        framework_request=_framework_request(),
        framework_response=FrameworkRiskEvaluationResponse(
            approved=approved,
            reason=framework_reason,
            adjusted_position_size=0.0,
            risk_score=risk_score,
        ),
        limits=_framework_limits(),
        strategy_exposure=200.0,
        symbol_exposure=100.0,
        rule_version="adapter-v1",
        evaluated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    assert decision.decision == expected_decision
    assert decision.reason == expected_reason
    assert decision.rule_version == "adapter-v1"
    assert decision.timestamp == datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_adapter_rejects_unknown_reason_code() -> None:
    with pytest.raises(ValueError, match="unsupported risk-framework reason"):
        adapt_risk_framework_response_to_risk_decision(
            framework_request=_framework_request(),
            framework_response=FrameworkRiskEvaluationResponse(
                approved=False,
                reason="rejected: unknown_rule",
                adjusted_position_size=0.0,
                risk_score=0.0,
            ),
            limits=_framework_limits(),
            strategy_exposure=0.0,
            symbol_exposure=0.0,
            rule_version="adapter-v1",
            evaluated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )


def test_evaluate_risk_framework_execution_decision_is_deterministic_for_equal_inputs() -> None:
    first = evaluate_risk_framework_execution_decision(
        request_id="req-1",
        strategy_id="strategy-a",
        symbol="AAPL",
        proposed_position_size=400.0,
        account_equity=2000.0,
        current_exposure=800.0,
        strategy_exposure=200.0,
        symbol_exposure=0.0,
        limits=_framework_limits(),
        rule_version="adapter-v1",
        evaluated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    second = evaluate_risk_framework_execution_decision(
        request_id="req-1",
        strategy_id="strategy-a",
        symbol="AAPL",
        proposed_position_size=400.0,
        account_equity=2000.0,
        current_exposure=800.0,
        strategy_exposure=200.0,
        symbol_exposure=0.0,
        limits=_framework_limits(),
        rule_version="adapter-v1",
        evaluated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    assert first == second
    assert first.decision == "APPROVED"
    assert first.reason == "approved:risk_framework_within_limits"
