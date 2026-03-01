from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal

import pytest

import cilly_trading.engine.pipeline.orchestrator as orchestrator
from cilly_trading.engine.pipeline.orchestrator import run_pipeline
from cilly_trading.engine.strategy_lifecycle.model import StrategyLifecycleState
from risk.contracts import RiskDecision, RiskEvaluationRequest, RiskGate


@dataclass(frozen=True)
class Order:
    id: str
    side: Literal["BUY", "SELL"]
    quantity: Decimal
    created_snapshot_key: str
    sequence: int


@dataclass(frozen=True)
class Position:
    quantity: Decimal
    avg_price: Decimal


@dataclass(frozen=True)
class DeterministicExecutionConfig:
    slippage_bps: int
    commission_per_order: Decimal
    price_scale: Decimal = Decimal("0.00000001")
    money_scale: Decimal = Decimal("0.01")
    quantity_scale: Decimal = Decimal("0.00000001")
    fill_timing: Literal["next_snapshot", "same_snapshot"] = "next_snapshot"


class _StaticLifecycleStore:
    def __init__(self, state: StrategyLifecycleState) -> None:
        self._state = state

    def get_state(self, strategy_id: str) -> StrategyLifecycleState:
        return self._state

    def set_state(self, strategy_id: str, new_state: StrategyLifecycleState) -> None:
        self._state = new_state


class _ApprovedRiskGate(RiskGate):
    def evaluate(self, request: RiskEvaluationRequest) -> RiskDecision:
        return RiskDecision(
            decision="APPROVED",
            score=10.0,
            max_allowed=100.0,
            reason="risk gate test",
            timestamp=datetime.now(tz=timezone.utc),
            rule_version="test-v1",
        )


def _risk_request() -> RiskEvaluationRequest:
    return RiskEvaluationRequest(
        request_id="req-1",
        strategy_id="strategy-a",
        symbol="AAPL",
        notional_usd=100.0,
        metadata={"source": "test"},
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


def _single_buy_order() -> Order:
    return Order(
        id="buy-1",
        side="BUY",
        quantity=Decimal("1"),
        created_snapshot_key="2024-01-01T00:00:00Z",
        sequence=1,
    )


def test_production_strategy_executes_when_risk_approved() -> None:
    snapshot, position, config = _execution_inputs()

    result = run_pipeline(
        {"orders": [_single_buy_order()], "snapshot": snapshot},
        risk_gate=_ApprovedRiskGate(),
        lifecycle_store=_StaticLifecycleStore(StrategyLifecycleState.PRODUCTION),
        risk_request=_risk_request(),
        position=position,
        execution_config=config,
    )

    assert result.status == "executed"


@pytest.mark.parametrize(
    "state",
    [
        StrategyLifecycleState.DRAFT,
        StrategyLifecycleState.EVALUATION,
        StrategyLifecycleState.DEPRECATED,
    ],
)
def test_non_production_strategies_are_rejected_and_never_execute(
    monkeypatch: pytest.MonkeyPatch,
    state: StrategyLifecycleState,
) -> None:
    snapshot, position, config = _execution_inputs()

    def _fail_if_called(**kwargs):
        raise AssertionError("execution must not be called for non-production strategies")

    monkeypatch.setattr(orchestrator, "_execute_order", _fail_if_called)

    result = run_pipeline(
        {"orders": [_single_buy_order()], "snapshot": snapshot},
        risk_gate=_ApprovedRiskGate(),
        lifecycle_store=_StaticLifecycleStore(state),
        risk_request=_risk_request(),
        position=position,
        execution_config=config,
    )

    assert result.status == "rejected"
    assert result.fills == []
