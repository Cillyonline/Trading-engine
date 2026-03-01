from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from cilly_trading.engine.order_execution_model import (
    DeterministicExecutionConfig,
    Order,
    Position,
)
from cilly_trading.engine.pipeline.orchestrator import run_pipeline
from risk.contracts import RiskDecision, RiskEvaluationRequest, RiskGate


class _StaticDecisionRiskGate(RiskGate):
    def __init__(self, decision: RiskDecision) -> None:
        self._decision = decision

    def evaluate(self, request: RiskEvaluationRequest) -> RiskDecision:
        return self._decision


def _config(fill_timing: str = "next_snapshot") -> DeterministicExecutionConfig:
    return DeterministicExecutionConfig(
        slippage_bps=10,
        commission_per_order=Decimal("1.25"),
        fill_timing=fill_timing,
    )


def _risk_decision(decision: str = "APPROVED") -> RiskDecision:
    return RiskDecision(
        decision=decision,
        score=10.0,
        max_allowed=100.0,
        reason="test",
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


def _run(
    *,
    orders: list[Order],
    snapshot: dict[str, str],
    position: Position,
    config: DeterministicExecutionConfig,
    decision: str = "APPROVED",
):
    return run_pipeline(
        {"orders": orders, "snapshot": snapshot},
        risk_gate=_StaticDecisionRiskGate(_risk_decision(decision=decision)),
        risk_request=_risk_request(),
        position=position,
        execution_config=config,
    )


def test_order_fill_determinism_repeated_runs_identical() -> None:
    config = _config()
    snapshot = {"timestamp": "2024-01-02T00:00:00Z", "open": "100"}
    position = Position(quantity=Decimal("0"), avg_price=Decimal("0"))

    orders = [
        Order(id="ord-2", side="BUY", quantity=Decimal("1"), created_snapshot_key="2024-01-01T00:00:00Z", sequence=2),
        Order(id="ord-1", side="BUY", quantity=Decimal("2"), created_snapshot_key="2024-01-01T00:00:00Z", sequence=1),
    ]

    result_a = _run(orders=orders, snapshot=snapshot, position=position, config=config)
    result_b = _run(orders=orders, snapshot=snapshot, position=position, config=config)

    assert result_a.fills == result_b.fills
    assert result_a.position == result_b.position
    assert [fill.order_id for fill in result_a.fills] == ["ord-1", "ord-2"]


def test_commission_model_is_fixed_and_repeatable() -> None:
    config = _config()
    snapshot = {"timestamp": "2024-01-02T00:00:00Z", "open": "50"}
    position = Position(quantity=Decimal("0"), avg_price=Decimal("0"))
    orders = [
        Order(id="buy-a", side="BUY", quantity=Decimal("1"), created_snapshot_key="2024-01-01T00:00:00Z", sequence=1),
        Order(id="buy-b", side="BUY", quantity=Decimal("1"), created_snapshot_key="2024-01-01T00:00:00Z", sequence=2),
    ]

    result_1 = _run(orders=orders, snapshot=snapshot, position=position, config=config)
    result_2 = _run(orders=orders, snapshot=snapshot, position=position, config=config)

    assert [fill.commission for fill in result_1.fills] == [Decimal("1.25"), Decimal("1.25")]
    assert result_1.fills == result_2.fills


def test_position_lifecycle_buy_increase_sell_reduce_close() -> None:
    config = _config()

    buy_snapshot = {"timestamp": "2024-01-02T00:00:00Z", "open": "100"}
    first_buy = Order(
        id="buy-1",
        side="BUY",
        quantity=Decimal("2"),
        created_snapshot_key="2024-01-01T00:00:00Z",
        sequence=1,
    )
    second_buy = Order(
        id="buy-2",
        side="BUY",
        quantity=Decimal("2"),
        created_snapshot_key="2024-01-01T00:00:00Z",
        sequence=2,
    )

    buy_result = _run(
        orders=[first_buy, second_buy],
        snapshot=buy_snapshot,
        position=Position(quantity=Decimal("0"), avg_price=Decimal("0")),
        config=config,
    )

    assert len(buy_result.fills) == 2
    assert buy_result.position.quantity == Decimal("4.00000000")
    assert buy_result.position.avg_price == Decimal("100.10000000")

    sell_snapshot = {"timestamp": "2024-01-03T00:00:00Z", "open": "110"}
    reduce_and_close = [
        Order(id="sell-1", side="SELL", quantity=Decimal("1"), created_snapshot_key="2024-01-02T00:00:00Z", sequence=3),
        Order(id="sell-2", side="SELL", quantity=Decimal("3"), created_snapshot_key="2024-01-02T00:00:00Z", sequence=4),
    ]

    sell_result = _run(
        orders=reduce_and_close,
        snapshot=sell_snapshot,
        position=buy_result.position,
        config=config,
    )

    assert len(sell_result.fills) == 2
    assert sell_result.fills[0].fill_price == Decimal("109.89000000")
    assert sell_result.position.quantity == Decimal("0")
    assert sell_result.position.avg_price == Decimal("0")


def test_slippage_applies_by_side_direction() -> None:
    config = _config()
    snapshot = {"timestamp": "2024-01-02T00:00:00Z", "open": "100"}

    buy_result = _run(
        orders=[Order(id="buy", side="BUY", quantity=Decimal("1"), created_snapshot_key="2024-01-01T00:00:00Z", sequence=1)],
        snapshot=snapshot,
        position=Position(quantity=Decimal("0"), avg_price=Decimal("0")),
        config=config,
    )

    sell_result = _run(
        orders=[Order(id="sell", side="SELL", quantity=Decimal("1"), created_snapshot_key="2024-01-01T00:00:00Z", sequence=1)],
        snapshot=snapshot,
        position=Position(quantity=Decimal("1"), avg_price=Decimal("99")),
        config=config,
    )

    assert buy_result.fills[0].fill_price == Decimal("100.10000000")
    assert sell_result.fills[0].fill_price == Decimal("99.90000000")


def test_next_snapshot_fill_timing_enforced() -> None:
    config = _config(fill_timing="next_snapshot")

    order = Order(
        id="next-fill",
        side="BUY",
        quantity=Decimal("1"),
        created_snapshot_key="2024-01-02T00:00:00Z",
        sequence=1,
    )
    start = Position(quantity=Decimal("0"), avg_price=Decimal("0"))

    result_t = _run(
        orders=[order],
        snapshot={"timestamp": "2024-01-02T00:00:00Z", "open": "10"},
        position=start,
        config=config,
    )

    result_t1 = _run(
        orders=[order],
        snapshot={"timestamp": "2024-01-03T00:00:00Z", "open": "11"},
        position=start,
        config=config,
    )

    assert result_t.fills == []
    assert result_t.position == start
    assert len(result_t1.fills) == 1
    assert result_t1.position.quantity == Decimal("1.00000000")


def test_execution_rejected_risk_decision_fails_closed() -> None:
    result = _run(
        orders=[Order(id="buy", side="BUY", quantity=Decimal("1"), created_snapshot_key="2024-01-01T00:00:00Z", sequence=1)],
        snapshot={"timestamp": "2024-01-02T00:00:00Z", "open": "100"},
        position=Position(quantity=Decimal("0"), avg_price=Decimal("0")),
        config=_config(),
        decision="REJECTED",
    )

    assert result.status == "rejected"
    assert result.fills == []


def test_execution_with_malformed_risk_decision_is_rejected() -> None:
    result = _run(
        orders=[Order(id="buy", side="BUY", quantity=Decimal("1"), created_snapshot_key="2024-01-01T00:00:00Z", sequence=1)],
        snapshot={"timestamp": "2024-01-02T00:00:00Z", "open": "100"},
        position=Position(quantity=Decimal("0"), avg_price=Decimal("0")),
        config=_config(),
        decision="MALFORMED",
    )

    assert result.status == "rejected"
    assert result.fills == []
