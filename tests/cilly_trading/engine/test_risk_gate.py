from __future__ import annotations

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
