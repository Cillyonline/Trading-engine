from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from cilly_trading.models import (
    ExecutionEvent,
    Order,
    Position,
    Trade,
    compute_execution_event_id,
    validate_trading_core_relationships,
)
from cilly_trading.repositories.execution_core_sqlite import (
    SqliteCanonicalExecutionRepository,
)


def _repo(tmp_path: Path) -> SqliteCanonicalExecutionRepository:
    return SqliteCanonicalExecutionRepository(db_path=tmp_path / "core-execution.db")


def _order(order_id: str, *, sequence: int = 1, created_at: str = "2025-01-01T09:00:00Z") -> Order:
    return Order.model_validate(
        {
            "order_id": order_id,
            "strategy_id": "strategy-a",
            "symbol": "AAPL",
            "sequence": sequence,
            "side": "BUY",
            "order_type": "market",
            "time_in_force": "day",
            "status": "filled",
            "quantity": Decimal("1"),
            "filled_quantity": Decimal("1"),
            "created_at": created_at,
            "average_fill_price": Decimal("100.00"),
            "last_execution_event_id": "evt-placeholder",
            "position_id": "pos-1",
            "trade_id": "trade-1",
        }
    )


def _event(
    event_id: str,
    order_id: str,
    *,
    sequence: int,
    occurred_at: str,
) -> ExecutionEvent:
    return ExecutionEvent.model_validate(
        {
            "event_id": event_id,
            "order_id": order_id,
            "strategy_id": "strategy-a",
            "symbol": "AAPL",
            "side": "BUY",
            "event_type": "filled",
            "occurred_at": occurred_at,
            "sequence": sequence,
            "execution_quantity": Decimal("1"),
            "execution_price": Decimal("100.00"),
            "commission": Decimal("1.00"),
            "position_id": "pos-1",
            "trade_id": "trade-1",
        }
    )


def _trade(*, execution_event_ids: list[str]) -> Trade:
    return Trade.model_validate(
        {
            "trade_id": "trade-1",
            "position_id": "pos-1",
            "strategy_id": "strategy-a",
            "symbol": "AAPL",
            "direction": "long",
            "status": "closed",
            "opened_at": "2025-01-01T09:00:00Z",
            "closed_at": "2025-01-02T09:00:00Z",
            "quantity_opened": Decimal("1"),
            "quantity_closed": Decimal("1"),
            "average_entry_price": Decimal("100.00"),
            "average_exit_price": Decimal("101.00"),
            "realized_pnl": Decimal("1.00"),
            "opening_order_ids": ["ord-1"],
            "closing_order_ids": [],
            "execution_event_ids": execution_event_ids,
        }
    )


def _position(*, order_ids: list[str], execution_event_ids: list[str]) -> Position:
    return Position.model_validate(
        {
            "position_id": "pos-1",
            "strategy_id": "strategy-a",
            "symbol": "AAPL",
            "direction": "long",
            "status": "closed",
            "opened_at": "2025-01-01T09:00:00Z",
            "closed_at": "2025-01-02T09:00:00Z",
            "quantity_opened": Decimal("1"),
            "quantity_closed": Decimal("1"),
            "net_quantity": Decimal("0"),
            "average_entry_price": Decimal("100.00"),
            "average_exit_price": Decimal("101.00"),
            "realized_pnl": Decimal("1.00"),
            "order_ids": order_ids,
            "execution_event_ids": execution_event_ids,
            "trade_ids": ["trade-1"],
        }
    )


def test_create_and_read_round_trip_is_consistent(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    order = _order("ord-1")
    event = _event(
        compute_execution_event_id(
            order_id="ord-1",
            event_type="filled",
            occurred_at="2025-01-01T09:01:00Z",
            sequence=1,
        ),
        "ord-1",
        sequence=1,
        occurred_at="2025-01-01T09:01:00Z",
    )
    order = Order.model_validate({**order.model_dump(mode="python"), "last_execution_event_id": event.event_id})
    trade = _trade(execution_event_ids=[event.event_id])

    repo.save_order(order)
    repo.save_execution_events([event])
    repo.save_trade(trade)

    stored_order = repo.get_order(order.order_id)
    stored_trade = repo.get_trade(trade.trade_id)
    stored_events = repo.list_execution_events(order_id=order.order_id)

    assert stored_order is not None
    assert stored_trade is not None
    assert stored_events == [event]
    assert stored_order.to_canonical_json() == order.to_canonical_json()
    assert stored_trade.to_canonical_json() == trade.to_canonical_json()


def test_execution_event_ordering_is_deterministic(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    e2 = _event("evt-2", "ord-1", sequence=2, occurred_at="2025-01-01T09:02:00Z")
    e1 = _event("evt-1", "ord-1", sequence=1, occurred_at="2025-01-01T09:01:00Z")
    e1b = _event("evt-1b", "ord-1", sequence=1, occurred_at="2025-01-01T09:01:00Z")

    repo.save_execution_events([e2, e1b, e1])

    first_read = repo.list_execution_events(order_id="ord-1")
    second_read = repo.list_execution_events(order_id="ord-1")

    assert first_read == second_read
    assert [event.event_id for event in first_read] == ["evt-1", "evt-1b", "evt-2"]


def test_replay_reads_support_relationship_validation(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    order = _order("ord-1")
    event = _event("evt-1", "ord-1", sequence=1, occurred_at="2025-01-01T09:01:00Z")
    order = Order.model_validate({**order.model_dump(mode="python"), "last_execution_event_id": event.event_id})
    trade = _trade(execution_event_ids=[event.event_id])

    repo.save_order(order)
    repo.save_execution_events([event])
    repo.save_trade(trade)

    replay_orders = repo.list_orders(strategy_id="strategy-a", symbol="AAPL")
    replay_events = repo.list_execution_events(strategy_id="strategy-a", symbol="AAPL")
    replay_trade = repo.get_trade("trade-1")
    replay_position = _position(
        order_ids=[order.order_id],
        execution_event_ids=[event.event_id],
    )

    assert replay_trade is not None
    validate_trading_core_relationships(
        trade=replay_trade,
        position=replay_position,
        orders=replay_orders,
        execution_events=replay_events,
    )


def test_negative_conflicting_execution_event_payload_is_rejected(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    event = _event("evt-1", "ord-1", sequence=1, occurred_at="2025-01-01T09:01:00Z")
    conflicting = _event("evt-1", "ord-1", sequence=1, occurred_at="2025-01-01T09:01:00Z")
    conflicting = ExecutionEvent.model_validate(
        {**conflicting.model_dump(mode="python"), "execution_price": Decimal("101.00")}
    )

    repo.save_execution_events([event])
    with pytest.raises(ValueError, match="conflicting_execution_event_payload"):
        repo.save_execution_events([conflicting])


def test_negative_invalid_order_is_rejected_before_write(tmp_path: Path) -> None:
    repo = _repo(tmp_path)

    with pytest.raises(ValidationError):
        repo.save_order(  # type: ignore[arg-type]
            {
                "order_id": "ord-invalid",
                "strategy_id": "strategy-a",
                "symbol": "AAPL",
                "sequence": 1,
                "side": "BUY",
                "order_type": "market",
                "time_in_force": "day",
                "status": "filled",
                "quantity": Decimal("1"),
                "filled_quantity": Decimal("1"),
                "created_at": "2025-01-01T09:00:00Z",
                "average_fill_price": Decimal("100.00"),
                # missing last_execution_event_id on a filled order
                "position_id": "pos-1",
                "trade_id": "trade-1",
            }
        )
