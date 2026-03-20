from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from cilly_trading.models import (
    ExecutionEvent,
    Order,
    Position,
    Trade,
    TRADING_CORE_ENTITIES,
    TRADING_CORE_RELATIONSHIPS,
    compute_execution_event_id,
    serialize_trading_core_entity,
    validate_trading_core_entity,
    validate_trading_core_relationships,
)


def _order_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "order_id": "ord-1",
        "strategy_id": "strategy-a",
        "symbol": "AAPL",
        "sequence": 1,
        "side": "BUY",
        "order_type": "market",
        "time_in_force": "day",
        "status": "created",
        "quantity": Decimal("2"),
        "filled_quantity": Decimal("0"),
        "created_at": "2024-01-01T00:00:00Z",
        "position_id": "pos-1",
        "trade_id": "trade-1",
    }
    payload.update(overrides)
    return payload


def _event_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "event_id": compute_execution_event_id(
            order_id="ord-1",
            event_type="filled",
            occurred_at="2024-01-02T00:00:00Z",
            sequence=1,
        ),
        "order_id": "ord-1",
        "strategy_id": "strategy-a",
        "symbol": "AAPL",
        "side": "BUY",
        "event_type": "filled",
        "occurred_at": "2024-01-02T00:00:00Z",
        "sequence": 1,
        "execution_quantity": Decimal("2"),
        "execution_price": Decimal("100.10"),
        "commission": Decimal("1.25"),
        "position_id": "pos-1",
        "trade_id": "trade-1",
    }
    payload.update(overrides)
    return payload


def _position_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "position_id": "pos-1",
        "strategy_id": "strategy-a",
        "symbol": "AAPL",
        "direction": "long",
        "status": "open",
        "opened_at": "2024-01-02T00:00:00Z",
        "quantity_opened": Decimal("2"),
        "quantity_closed": Decimal("0"),
        "net_quantity": Decimal("2"),
        "average_entry_price": Decimal("100.10"),
        "order_ids": ["ord-1"],
        "execution_event_ids": ["evt-b", "evt-a"],
        "trade_ids": ["trade-1"],
    }
    payload.update(overrides)
    return payload


def _trade_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "trade_id": "trade-1",
        "position_id": "pos-1",
        "strategy_id": "strategy-a",
        "symbol": "AAPL",
        "direction": "long",
        "status": "open",
        "opened_at": "2024-01-02T00:00:00Z",
        "quantity_opened": Decimal("2"),
        "quantity_closed": Decimal("0"),
        "average_entry_price": Decimal("100.10"),
        "opening_order_ids": ["ord-1"],
        "closing_order_ids": [],
        "execution_event_ids": ["evt-b", "evt-a"],
    }
    payload.update(overrides)
    return payload


def test_trading_core_entity_responsibilities_are_explicit() -> None:
    assert TRADING_CORE_ENTITIES["Order"]["authority"] == "authoritative"
    assert TRADING_CORE_ENTITIES["ExecutionEvent"]["authority"] == "authoritative"
    assert TRADING_CORE_ENTITIES["Position"]["authority"] == "derived"
    assert TRADING_CORE_ENTITIES["Trade"]["authority"] == "derived"
    assert any(
        relationship["from_entity"] == "Trade" and relationship["to_entity"] == "ExecutionEvent"
        for relationship in TRADING_CORE_RELATIONSHIPS
    )


def test_representative_payloads_validate_and_relationships_hold() -> None:
    order = Order.model_validate(
        _order_payload(
            status="filled",
            filled_quantity=Decimal("2"),
            average_fill_price=Decimal("100.10"),
            last_execution_event_id="evt-1",
        )
    )
    event = ExecutionEvent.model_validate(_event_payload())
    position = Position.model_validate(
        _position_payload(execution_event_ids=[event.event_id], order_ids=[order.order_id])
    )
    trade = Trade.model_validate(
        _trade_payload(execution_event_ids=[event.event_id], opening_order_ids=[order.order_id])
    )

    validate_trading_core_relationships(
        trade=trade,
        position=position,
        orders=[order],
        execution_events=[event],
    )


def test_trading_core_serialization_is_deterministic() -> None:
    trade_a = validate_trading_core_entity("trade", _trade_payload())
    trade_b = validate_trading_core_entity(
        "trade",
        _trade_payload(execution_event_ids=["evt-a", "evt-b"]),
    )

    assert serialize_trading_core_entity(trade_a) == serialize_trading_core_entity(trade_b)


def test_negative_order_validation_rejects_invalid_fill_state() -> None:
    with pytest.raises(ValidationError):
        Order.model_validate(
            _order_payload(
                status="filled",
                filled_quantity=Decimal("1"),
                average_fill_price=Decimal("100.10"),
                last_execution_event_id="evt-1",
            )
        )


def test_negative_execution_event_validation_rejects_missing_fill_fields() -> None:
    with pytest.raises(ValidationError):
        ExecutionEvent.model_validate(_event_payload(execution_price=None))


def test_negative_position_validation_rejects_incorrect_net_quantity() -> None:
    with pytest.raises(ValidationError):
        Position.model_validate(_position_payload(net_quantity=Decimal("3")))


def test_negative_trade_validation_rejects_closed_trade_without_exit_fields() -> None:
    with pytest.raises(ValidationError):
        Trade.model_validate(
            _trade_payload(
                status="closed",
                quantity_closed=Decimal("2"),
                closed_at=None,
                average_exit_price=None,
                realized_pnl=None,
            )
        )


def test_relationship_validation_rejects_unknown_execution_event_reference() -> None:
    order = Order.model_validate(
        _order_payload(
            status="filled",
            filled_quantity=Decimal("2"),
            average_fill_price=Decimal("100.10"),
            last_execution_event_id="evt-1",
        )
    )
    event = ExecutionEvent.model_validate(_event_payload())
    position = Position.model_validate(_position_payload(order_ids=[order.order_id], execution_event_ids=[event.event_id]))
    trade = Trade.model_validate(_trade_payload(opening_order_ids=[order.order_id], execution_event_ids=["evt-missing"]))

    with pytest.raises(ValueError):
        validate_trading_core_relationships(
            trade=trade,
            position=position,
            orders=[order],
            execution_events=[event],
        )
