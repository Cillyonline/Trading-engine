from __future__ import annotations

import math

import pytest
from risk.contracts import RiskEvaluationRequest

from cilly_trading.engine.risk import ThresholdRiskGate


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
