from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from cilly_trading.engine.pipeline.orchestrator import (
    DeterministicExecutionConfig,
    Order,
    Position,
    run_pipeline,
)
from cilly_trading.engine.strategy_lifecycle.model import StrategyLifecycleState
from risk.contracts import RiskDecision, RiskEvaluationRequest, RiskGate


class _ProductionLifecycleStore:
    def get_state(self, strategy_id: str) -> StrategyLifecycleState:
        return StrategyLifecycleState.PRODUCTION

    def set_state(self, strategy_id: str, new_state: StrategyLifecycleState) -> None:
        return None


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


def _order(
    *,
    order_id: str,
    side: str,
    quantity: str,
    created_at: str,
    sequence: int,
    position_id: str = "pos-1",
    trade_id: str = "trade-1",
) -> Order:
    return Order(
        order_id=order_id,
        strategy_id="strategy-a",
        symbol="AAPL",
        sequence=sequence,
        side=side,
        order_type="market",
        time_in_force="day",
        status="created",
        quantity=Decimal(quantity),
        created_at=created_at,
        position_id=position_id,
        trade_id=trade_id,
    )


def _position(
    *,
    status: str = "flat",
    opened_at: str = "2024-01-01T00:00:00Z",
    closed_at: str | None = None,
    quantity_opened: str = "0",
    quantity_closed: str = "0",
    net_quantity: str = "0",
    average_entry_price: str = "0",
    average_exit_price: str | None = None,
    realized_pnl: str | None = None,
    order_ids: list[str] | None = None,
    execution_event_ids: list[str] | None = None,
    trade_ids: list[str] | None = None,
) -> Position:
    payload = {
        "position_id": "pos-1",
        "strategy_id": "strategy-a",
        "symbol": "AAPL",
        "direction": "long",
        "status": status,
        "opened_at": opened_at,
        "closed_at": closed_at,
        "quantity_opened": Decimal(quantity_opened),
        "quantity_closed": Decimal(quantity_closed),
        "net_quantity": Decimal(net_quantity),
        "average_entry_price": Decimal(average_entry_price),
        "order_ids": order_ids or [],
        "execution_event_ids": execution_event_ids or [],
        "trade_ids": trade_ids or [],
    }
    if average_exit_price is not None:
        payload["average_exit_price"] = Decimal(average_exit_price)
    if realized_pnl is not None:
        payload["realized_pnl"] = Decimal(realized_pnl)
    return Position.model_validate(payload)


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
        lifecycle_store=_ProductionLifecycleStore(),
        risk_request=_risk_request(),
        position=position,
        execution_config=config,
    )


def test_order_fill_determinism_repeated_runs_identical() -> None:
    config = _config()
    snapshot = {"timestamp": "2024-01-02T00:00:00Z", "open": "100"}
    position = _position()

    orders = [
        _order(order_id="ord-2", side="BUY", quantity="1", created_at="2024-01-01T00:00:00Z", sequence=2),
        _order(order_id="ord-1", side="BUY", quantity="2", created_at="2024-01-01T00:00:00Z", sequence=1),
    ]

    result_a = _run(orders=orders, snapshot=snapshot, position=position, config=config)
    result_b = _run(orders=orders, snapshot=snapshot, position=position, config=config)

    assert result_a.fills == result_b.fills
    assert result_a.position == result_b.position
    assert [event.order_id for event in result_a.fills] == ["ord-1", "ord-2"]


def test_commission_model_is_fixed_and_repeatable() -> None:
    config = _config()
    snapshot = {"timestamp": "2024-01-02T00:00:00Z", "open": "50"}
    position = _position()
    orders = [
        _order(order_id="buy-a", side="BUY", quantity="1", created_at="2024-01-01T00:00:00Z", sequence=1),
        _order(order_id="buy-b", side="BUY", quantity="1", created_at="2024-01-01T00:00:00Z", sequence=2),
    ]

    result_1 = _run(orders=orders, snapshot=snapshot, position=position, config=config)
    result_2 = _run(orders=orders, snapshot=snapshot, position=position, config=config)

    assert [event.commission for event in result_1.fills] == [Decimal("1.25"), Decimal("1.25")]
    assert result_1.fills == result_2.fills


def test_position_lifecycle_buy_increase_sell_reduce_close() -> None:
    config = _config()

    buy_snapshot = {"timestamp": "2024-01-02T00:00:00Z", "open": "100"}
    buy_result = _run(
        orders=[
            _order(order_id="buy-1", side="BUY", quantity="2", created_at="2024-01-01T00:00:00Z", sequence=1),
            _order(order_id="buy-2", side="BUY", quantity="2", created_at="2024-01-01T00:00:00Z", sequence=2),
        ],
        snapshot=buy_snapshot,
        position=_position(),
        config=config,
    )

    assert len(buy_result.fills) == 2
    assert buy_result.position.status == "open"
    assert buy_result.position.net_quantity == Decimal("4.00000000")
    assert buy_result.position.average_entry_price == Decimal("100.10000000")

    sell_snapshot = {"timestamp": "2024-01-03T00:00:00Z", "open": "110"}
    sell_result = _run(
        orders=[
            _order(order_id="sell-1", side="SELL", quantity="1", created_at="2024-01-02T00:00:00Z", sequence=3),
            _order(order_id="sell-2", side="SELL", quantity="3", created_at="2024-01-02T00:00:00Z", sequence=4),
        ],
        snapshot=sell_snapshot,
        position=buy_result.position,
        config=config,
    )

    assert len(sell_result.fills) == 2
    assert sell_result.fills[0].execution_price == Decimal("109.89000000")
    assert sell_result.position.status == "closed"
    assert sell_result.position.net_quantity == Decimal("0")
    assert sell_result.position.average_exit_price == Decimal("109.89000000")


def test_slippage_applies_by_side_direction() -> None:
    config = _config()
    snapshot = {"timestamp": "2024-01-02T00:00:00Z", "open": "100"}

    buy_result = _run(
        orders=[_order(order_id="buy", side="BUY", quantity="1", created_at="2024-01-01T00:00:00Z", sequence=1)],
        snapshot=snapshot,
        position=_position(),
        config=config,
    )

    sell_result = _run(
        orders=[_order(order_id="sell", side="SELL", quantity="1", created_at="2024-01-01T00:00:00Z", sequence=1)],
        snapshot=snapshot,
        position=_position(
            status="open",
            quantity_opened="1",
            net_quantity="1",
            average_entry_price="99",
            trade_ids=["trade-1"],
        ),
        config=config,
    )

    assert buy_result.fills[0].execution_price == Decimal("100.10000000")
    assert sell_result.fills[0].execution_price == Decimal("99.90000000")


def test_next_snapshot_fill_timing_enforced() -> None:
    config = _config(fill_timing="next_snapshot")
    order = _order(
        order_id="next-fill",
        side="BUY",
        quantity="1",
        created_at="2024-01-02T00:00:00Z",
        sequence=1,
    )

    result_t = _run(
        orders=[order],
        snapshot={"timestamp": "2024-01-02T00:00:00Z", "open": "10"},
        position=_position(),
        config=config,
    )

    result_t1 = _run(
        orders=[order],
        snapshot={"timestamp": "2024-01-03T00:00:00Z", "open": "11"},
        position=_position(),
        config=config,
    )

    assert result_t.fills == []
    assert result_t.position.net_quantity == Decimal("0")
    assert len(result_t1.fills) == 1
    assert result_t1.position.net_quantity == Decimal("1.00000000")


def test_execution_rejected_risk_decision_fails_closed() -> None:
    result = _run(
        orders=[_order(order_id="buy", side="BUY", quantity="1", created_at="2024-01-01T00:00:00Z", sequence=1)],
        snapshot={"timestamp": "2024-01-02T00:00:00Z", "open": "100"},
        position=_position(),
        config=_config(),
        decision="REJECTED",
    )

    assert result.status == "rejected"
    assert result.fills == []
