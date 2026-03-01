from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

import cilly_trading.engine.order_execution_model as order_execution_model
from cilly_trading.engine.order_execution_model import (
    DeterministicExecutionConfig,
    Order,
    Position,
)
from cilly_trading.engine.pipeline.orchestrator import run_pipeline
from risk.contracts import RiskDecision, RiskEvaluationRequest, RiskGate


class _TrackingRiskGate(RiskGate):
    def __init__(self, decision: RiskDecision, events: list[str]) -> None:
        self._decision = decision
        self._events = events

    def evaluate(self, request: RiskEvaluationRequest) -> RiskDecision:
        self._events.append("risk")
        return self._decision


def _approved_or_rejected_decision(decision: str) -> RiskDecision:
    return RiskDecision(
        decision=decision,
        score=10.0,
        max_allowed=100.0,
        reason="risk gate test",
        timestamp=datetime.now(tz=timezone.utc),
        rule_version="test-v1",
    )


def _single_buy_order() -> Order:
    return Order(
        id="buy-1",
        side="BUY",
        quantity=Decimal("1"),
        created_snapshot_key="2024-01-01T00:00:00Z",
        sequence=1,
    )


def _execution_inputs() -> tuple[dict[str, str], Position, DeterministicExecutionConfig]:
    snapshot = {"timestamp": "2024-01-02T00:00:00Z", "open": "100"}
    position = Position(quantity=Decimal("0"), avg_price=Decimal("0"))
    config = DeterministicExecutionConfig(
        slippage_bps=10,
        commission_per_order=Decimal("1.25"),
        fill_timing="next_snapshot",
    )
    return snapshot, position, config


def _risk_request() -> RiskEvaluationRequest:
    return RiskEvaluationRequest(
        request_id="req-1",
        strategy_id="strategy-a",
        symbol="AAPL",
        notional_usd=100.0,
        metadata={"source": "test"},
    )


def test_execute_via_orchestrator_succeeds_and_orders_risk_before_execution(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []
    snapshot, position, config = _execution_inputs()

    gate = _TrackingRiskGate(_approved_or_rejected_decision("APPROVED"), events)

    original = order_execution_model._DeterministicExecutionModel._execute

    def _tracked_execute(self, **kwargs):
        events.append("execution")
        return original(self, **kwargs)

    monkeypatch.setattr(order_execution_model._DeterministicExecutionModel, "_execute", _tracked_execute)

    result = run_pipeline(
        {"orders": [_single_buy_order()], "snapshot": snapshot},
        risk_gate=gate,
        risk_request=_risk_request(),
        position=position,
        execution_config=config,
    )

    assert result.status == "executed"
    assert len(result.fills) == 1
    assert events == ["risk", "execution"]


def test_direct_execution_call_is_forbidden_outside_orchestrator() -> None:
    snapshot, position, config = _execution_inputs()
    execute_order = getattr(order_execution_model, "_execute_order")

    with pytest.raises(
        RuntimeError,
        match="restricted to cilly_trading.engine.pipeline.orchestrator",
    ):
        execute_order(
            orders=[_single_buy_order()],
            snapshot=snapshot,
            position=position,
            config=config,
            risk_decision=_approved_or_rejected_decision("APPROVED"),
        )
