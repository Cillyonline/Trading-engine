from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from cilly_trading.engine.order_execution_model import (
    DeterministicExecutionConfig,
    DeterministicExecutionModel,
    Order,
    Position,
)
from cilly_trading.engine.risk import RiskApprovalMissingError, RiskRejectedError
from risk.contracts import RiskDecision


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


def test_order_fill_determinism_repeated_runs_identical() -> None:
    model = DeterministicExecutionModel()
    config = _config()
    snapshot = {"timestamp": "2024-01-02T00:00:00Z", "open": "100"}
    position = Position(quantity=Decimal("0"), avg_price=Decimal("0"))

    orders = [
        Order(id="ord-2", side="BUY", quantity=Decimal("1"), created_snapshot_key="2024-01-01T00:00:00Z", sequence=2),
        Order(id="ord-1", side="BUY", quantity=Decimal("2"), created_snapshot_key="2024-01-01T00:00:00Z", sequence=1),
    ]

    fills_a, position_a = model.execute(
        orders=orders,
        snapshot=snapshot,
        position=position,
        config=config,
        risk_decision=_risk_decision(),
    )
    fills_b, position_b = model.execute(
        orders=orders,
        snapshot=snapshot,
        position=position,
        config=config,
        risk_decision=_risk_decision(),
    )

    assert fills_a == fills_b
    assert position_a == position_b
    assert [fill.order_id for fill in fills_a] == ["ord-1", "ord-2"]


def test_commission_model_is_fixed_and_repeatable() -> None:
    model = DeterministicExecutionModel()
    config = _config()
    snapshot = {"timestamp": "2024-01-02T00:00:00Z", "open": "50"}
    position = Position(quantity=Decimal("0"), avg_price=Decimal("0"))
    orders = [
        Order(id="buy-a", side="BUY", quantity=Decimal("1"), created_snapshot_key="2024-01-01T00:00:00Z", sequence=1),
        Order(id="buy-b", side="BUY", quantity=Decimal("1"), created_snapshot_key="2024-01-01T00:00:00Z", sequence=2),
    ]

    fills_1, _ = model.execute(
        orders=orders,
        snapshot=snapshot,
        position=position,
        config=config,
        risk_decision=_risk_decision(),
    )
    fills_2, _ = model.execute(
        orders=orders,
        snapshot=snapshot,
        position=position,
        config=config,
        risk_decision=_risk_decision(),
    )

    assert [fill.commission for fill in fills_1] == [Decimal("1.25"), Decimal("1.25")]
    assert fills_1 == fills_2


def test_position_lifecycle_buy_increase_sell_reduce_close() -> None:
    model = DeterministicExecutionModel()
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

    fills_buy, position_after_buy = model.execute(
        orders=[first_buy, second_buy],
        snapshot=buy_snapshot,
        position=Position(quantity=Decimal("0"), avg_price=Decimal("0")),
        config=config,
        risk_decision=_risk_decision(),
    )

    assert len(fills_buy) == 2
    assert position_after_buy.quantity == Decimal("4.00000000")
    assert position_after_buy.avg_price == Decimal("100.10000000")

    sell_snapshot = {"timestamp": "2024-01-03T00:00:00Z", "open": "110"}
    reduce_and_close = [
        Order(id="sell-1", side="SELL", quantity=Decimal("1"), created_snapshot_key="2024-01-02T00:00:00Z", sequence=3),
        Order(id="sell-2", side="SELL", quantity=Decimal("3"), created_snapshot_key="2024-01-02T00:00:00Z", sequence=4),
    ]

    fills_sell, position_after_sell = model.execute(
        orders=reduce_and_close,
        snapshot=sell_snapshot,
        position=position_after_buy,
        config=config,
        risk_decision=_risk_decision(),
    )

    assert len(fills_sell) == 2
    assert fills_sell[0].fill_price == Decimal("109.89000000")
    assert position_after_sell.quantity == Decimal("0")
    assert position_after_sell.avg_price == Decimal("0")


def test_slippage_applies_by_side_direction() -> None:
    model = DeterministicExecutionModel()
    config = _config()
    snapshot = {"timestamp": "2024-01-02T00:00:00Z", "open": "100"}

    buy_fills, _ = model.execute(
        orders=[Order(id="buy", side="BUY", quantity=Decimal("1"), created_snapshot_key="2024-01-01T00:00:00Z", sequence=1)],
        snapshot=snapshot,
        position=Position(quantity=Decimal("0"), avg_price=Decimal("0")),
        config=config,
        risk_decision=_risk_decision(),
    )

    sell_fills, _ = model.execute(
        orders=[Order(id="sell", side="SELL", quantity=Decimal("1"), created_snapshot_key="2024-01-01T00:00:00Z", sequence=1)],
        snapshot=snapshot,
        position=Position(quantity=Decimal("1"), avg_price=Decimal("99")),
        config=config,
        risk_decision=_risk_decision(),
    )

    assert buy_fills[0].fill_price == Decimal("100.10000000")
    assert sell_fills[0].fill_price == Decimal("99.90000000")


def test_next_snapshot_fill_timing_enforced() -> None:
    model = DeterministicExecutionModel()
    config = _config(fill_timing="next_snapshot")

    order = Order(
        id="next-fill",
        side="BUY",
        quantity=Decimal("1"),
        created_snapshot_key="2024-01-02T00:00:00Z",
        sequence=1,
    )
    start = Position(quantity=Decimal("0"), avg_price=Decimal("0"))

    fills_t, position_t = model.execute(
        orders=[order],
        snapshot={"timestamp": "2024-01-02T00:00:00Z", "open": "10"},
        position=start,
        config=config,
        risk_decision=_risk_decision(),
    )

    fills_t1, position_t1 = model.execute(
        orders=[order],
        snapshot={"timestamp": "2024-01-03T00:00:00Z", "open": "11"},
        position=start,
        config=config,
        risk_decision=_risk_decision(),
    )

    assert fills_t == []
    assert position_t == start
    assert len(fills_t1) == 1
    assert position_t1.quantity == Decimal("1.00000000")


def test_execution_without_risk_approval_fails() -> None:
    model = DeterministicExecutionModel()

    with pytest.raises(RiskApprovalMissingError, match="risk approval"):
        model.execute(
            orders=[Order(id="buy", side="BUY", quantity=Decimal("1"), created_snapshot_key="2024-01-01T00:00:00Z", sequence=1)],
            snapshot={"timestamp": "2024-01-02T00:00:00Z", "open": "100"},
            position=Position(quantity=Decimal("0"), avg_price=Decimal("0")),
            config=_config(),
            risk_decision=None,
        )


def test_execution_rejected_risk_decision_fails() -> None:
    model = DeterministicExecutionModel()

    with pytest.raises(RiskRejectedError, match="REJECTED"):
        model.execute(
            orders=[Order(id="buy", side="BUY", quantity=Decimal("1"), created_snapshot_key="2024-01-01T00:00:00Z", sequence=1)],
            snapshot={"timestamp": "2024-01-02T00:00:00Z", "open": "100"},
            position=Position(quantity=Decimal("0"), avg_price=Decimal("0")),
            config=_config(),
            risk_decision=_risk_decision(decision="REJECTED"),
        )


def test_execution_with_malformed_risk_decision_fails() -> None:
    model = DeterministicExecutionModel()

    with pytest.raises(ValueError, match="must be APPROVED or REJECTED"):
        model.execute(
            orders=[Order(id="buy", side="BUY", quantity=Decimal("1"), created_snapshot_key="2024-01-01T00:00:00Z", sequence=1)],
            snapshot={"timestamp": "2024-01-02T00:00:00Z", "open": "100"},
            position=Position(quantity=Decimal("0"), avg_price=Decimal("0")),
            config=_config(),
            risk_decision=_risk_decision(decision="MALFORMED"),
        )
