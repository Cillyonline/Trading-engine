from __future__ import annotations

import itertools
from decimal import Decimal

import pytest
from pydantic import ValidationError

from cilly_trading.models import Order, Position, Trade
from cilly_trading.trading_lifecycle import (
    ORDER_ALLOWED_TRANSITIONS,
    POSITION_ALLOWED_TRANSITIONS,
    TRADE_ALLOWED_TRANSITIONS,
    OrderLifecycleSnapshot,
    OrderLifecycleState,
    PositionLifecycleSnapshot,
    PositionLifecycleState,
    TradeLifecycleSnapshot,
    TradeLifecycleState,
    TradingLifecycleInvariantError,
    TradingLifecycleTransitionError,
    get_allowed_order_transitions,
    get_allowed_position_transitions,
    get_allowed_trade_transitions,
    validate_order_transition,
    validate_order_transition_invariants,
    validate_order_transition_sequence,
    validate_position_transition,
    validate_position_transition_invariants,
    validate_position_transition_sequence,
    validate_trade_transition,
    validate_trade_transition_invariants,
    validate_trade_transition_sequence,
)


VALID_ORDER_TRANSITIONS = {
    (OrderLifecycleState.CREATED, OrderLifecycleState.SUBMITTED),
    (OrderLifecycleState.CREATED, OrderLifecycleState.CANCELLED),
    (OrderLifecycleState.CREATED, OrderLifecycleState.REJECTED),
    (OrderLifecycleState.SUBMITTED, OrderLifecycleState.PARTIALLY_FILLED),
    (OrderLifecycleState.SUBMITTED, OrderLifecycleState.FILLED),
    (OrderLifecycleState.SUBMITTED, OrderLifecycleState.CANCELLED),
    (OrderLifecycleState.SUBMITTED, OrderLifecycleState.REJECTED),
    (OrderLifecycleState.PARTIALLY_FILLED, OrderLifecycleState.FILLED),
    (OrderLifecycleState.PARTIALLY_FILLED, OrderLifecycleState.CANCELLED),
}

VALID_TRADE_TRANSITIONS = {
    (TradeLifecycleState.OPEN, TradeLifecycleState.CLOSED),
}

VALID_POSITION_TRANSITIONS = {
    (PositionLifecycleState.FLAT, PositionLifecycleState.OPEN),
    (PositionLifecycleState.OPEN, PositionLifecycleState.CLOSED),
}


@pytest.mark.parametrize(("current", "target"), sorted(VALID_ORDER_TRANSITIONS, key=lambda t: (t[0].value, t[1].value)))
def test_valid_order_transitions_succeed(current: OrderLifecycleState, target: OrderLifecycleState) -> None:
    validate_order_transition(current_state=current, target_state=target)


@pytest.mark.parametrize(("current", "target"), sorted(VALID_TRADE_TRANSITIONS, key=lambda t: (t[0].value, t[1].value)))
def test_valid_trade_transitions_succeed(current: TradeLifecycleState, target: TradeLifecycleState) -> None:
    validate_trade_transition(current_state=current, target_state=target)


@pytest.mark.parametrize(
    ("current", "target"),
    sorted(VALID_POSITION_TRANSITIONS, key=lambda t: (t[0].value, t[1].value)),
)
def test_valid_position_transitions_succeed(current: PositionLifecycleState, target: PositionLifecycleState) -> None:
    validate_position_transition(current_state=current, target_state=target)


def test_invalid_order_transitions_fail_deterministically() -> None:
    all_pairs = set(itertools.product(OrderLifecycleState, repeat=2))
    invalid_pairs = sorted(all_pairs - VALID_ORDER_TRANSITIONS, key=lambda t: (t[0].value, t[1].value))

    for current, target in invalid_pairs:
        with pytest.raises(TradingLifecycleTransitionError) as error:
            validate_order_transition(current_state=current, target_state=target)

        if current == target:
            assert str(error.value) == f"Illegal Order lifecycle transition: {current.value} -> {target.value}"
        elif current in {OrderLifecycleState.FILLED, OrderLifecycleState.CANCELLED, OrderLifecycleState.REJECTED}:
            assert str(error.value) == f"Illegal Order lifecycle transition: {current.value} is terminal"
        else:
            assert str(error.value) == f"Illegal Order lifecycle transition: {current.value} -> {target.value}"


def test_invalid_trade_transitions_fail_deterministically() -> None:
    with pytest.raises(TradingLifecycleTransitionError, match="Illegal Trade lifecycle transition: closed is terminal"):
        validate_trade_transition(
            current_state=TradeLifecycleState.CLOSED,
            target_state=TradeLifecycleState.OPEN,
        )


def test_invalid_position_transitions_fail_deterministically() -> None:
    with pytest.raises(TradingLifecycleTransitionError, match="Illegal Position lifecycle transition: flat -> closed"):
        validate_position_transition(
            current_state=PositionLifecycleState.FLAT,
            target_state=PositionLifecycleState.CLOSED,
        )


def test_transition_order_sequences_are_validated() -> None:
    validate_order_transition_sequence(
        [OrderLifecycleState.CREATED, OrderLifecycleState.SUBMITTED, OrderLifecycleState.PARTIALLY_FILLED, OrderLifecycleState.FILLED]
    )
    validate_trade_transition_sequence([TradeLifecycleState.OPEN, TradeLifecycleState.CLOSED])
    validate_position_transition_sequence([PositionLifecycleState.FLAT, PositionLifecycleState.OPEN, PositionLifecycleState.CLOSED])

    with pytest.raises(TradingLifecycleTransitionError, match="Illegal Order lifecycle transition: created -> filled"):
        validate_order_transition_sequence([OrderLifecycleState.CREATED, OrderLifecycleState.FILLED])

    with pytest.raises(TradingLifecycleTransitionError, match="Illegal Position lifecycle transition: open -> flat"):
        validate_position_transition_sequence([PositionLifecycleState.OPEN, PositionLifecycleState.FLAT])


def test_transition_invariants_enforce_monotonic_progression() -> None:
    validate_order_transition_invariants(
        current=OrderLifecycleSnapshot(
            status=OrderLifecycleState.SUBMITTED,
            quantity=Decimal("2"),
            filled_quantity=Decimal("0"),
        ),
        target=OrderLifecycleSnapshot(
            status=OrderLifecycleState.PARTIALLY_FILLED,
            quantity=Decimal("2"),
            filled_quantity=Decimal("1"),
        ),
    )

    with pytest.raises(TradingLifecycleInvariantError, match="filled_quantity must be monotonic non-decreasing"):
        validate_order_transition_invariants(
            current=OrderLifecycleSnapshot(
                status=OrderLifecycleState.PARTIALLY_FILLED,
                quantity=Decimal("2"),
                filled_quantity=Decimal("1"),
            ),
            target=OrderLifecycleSnapshot(
                status=OrderLifecycleState.FILLED,
                quantity=Decimal("2"),
                filled_quantity=Decimal("0.5"),
            ),
        )

    validate_trade_transition_invariants(
        current=TradeLifecycleSnapshot(
            status=TradeLifecycleState.OPEN,
            quantity_opened=Decimal("3"),
            quantity_closed=Decimal("1"),
        ),
        target=TradeLifecycleSnapshot(
            status=TradeLifecycleState.CLOSED,
            quantity_opened=Decimal("3"),
            quantity_closed=Decimal("3"),
        ),
    )

    with pytest.raises(TradingLifecycleInvariantError, match="quantity_opened must be immutable"):
        validate_position_transition_invariants(
            current=PositionLifecycleSnapshot(
                status=PositionLifecycleState.OPEN,
                quantity_opened=Decimal("3"),
                quantity_closed=Decimal("1"),
                net_quantity=Decimal("2"),
            ),
            target=PositionLifecycleSnapshot(
                status=PositionLifecycleState.CLOSED,
                quantity_opened=Decimal("4"),
                quantity_closed=Decimal("4"),
                net_quantity=Decimal("0"),
            ),
        )


def test_transition_matrices_are_explicit_and_immutable() -> None:
    assert get_allowed_order_transitions(OrderLifecycleState.CREATED) == frozenset(
        {
            OrderLifecycleState.SUBMITTED,
            OrderLifecycleState.CANCELLED,
            OrderLifecycleState.REJECTED,
        }
    )
    assert get_allowed_trade_transitions(TradeLifecycleState.OPEN) == frozenset({TradeLifecycleState.CLOSED})
    assert get_allowed_position_transitions(PositionLifecycleState.OPEN) == frozenset({PositionLifecycleState.CLOSED})

    with pytest.raises(TypeError):
        ORDER_ALLOWED_TRANSITIONS[OrderLifecycleState.CREATED] = frozenset()  # type: ignore[index]

    with pytest.raises(TypeError):
        TRADE_ALLOWED_TRANSITIONS[TradeLifecycleState.OPEN] = frozenset()  # type: ignore[index]

    with pytest.raises(TypeError):
        POSITION_ALLOWED_TRANSITIONS[PositionLifecycleState.FLAT] = frozenset()  # type: ignore[index]


def test_regression_model_validation_uses_canonical_lifecycle_invariants() -> None:
    Order.model_validate(
        {
            "order_id": "ord-1",
            "strategy_id": "s1",
            "symbol": "AAPL",
            "sequence": 1,
            "side": "BUY",
            "order_type": "market",
            "time_in_force": "day",
            "status": "partially_filled",
            "quantity": Decimal("2"),
            "filled_quantity": Decimal("1"),
            "created_at": "2024-01-01T00:00:00Z",
            "average_fill_price": Decimal("100.1"),
            "last_execution_event_id": "evt-1",
        }
    )

    Order.model_validate(
        {
            "order_id": "ord-cancelled-partial",
            "strategy_id": "s1",
            "symbol": "AAPL",
            "sequence": 2,
            "side": "BUY",
            "order_type": "market",
            "time_in_force": "day",
            "status": "cancelled",
            "quantity": Decimal("2"),
            "filled_quantity": Decimal("1"),
            "created_at": "2024-01-01T00:00:00Z",
            "submitted_at": "2024-01-01T00:01:00Z",
            "average_fill_price": Decimal("100.1"),
            "last_execution_event_id": "evt-cancelled",
        }
    )

    with pytest.raises(ValidationError):
        Order.model_validate(
            {
                "order_id": "ord-1",
                "strategy_id": "s1",
                "symbol": "AAPL",
                "sequence": 1,
                "side": "BUY",
                "order_type": "market",
                "time_in_force": "day",
                "status": "submitted",
                "quantity": Decimal("2"),
                "filled_quantity": Decimal("1"),
                "created_at": "2024-01-01T00:00:00Z",
            }
        )

    with pytest.raises(ValidationError):
        Position.model_validate(
            {
                "position_id": "pos-1",
                "strategy_id": "s1",
                "symbol": "AAPL",
                "direction": "long",
                "status": "flat",
                "opened_at": "2024-01-01T00:00:00Z",
                "quantity_opened": Decimal("1"),
                "quantity_closed": Decimal("0"),
                "net_quantity": Decimal("1"),
                "average_entry_price": Decimal("100"),
            }
        )

    with pytest.raises(ValidationError):
        Trade.model_validate(
            {
                "trade_id": "tr-1",
                "position_id": "pos-1",
                "strategy_id": "s1",
                "symbol": "AAPL",
                "direction": "long",
                "status": "open",
                "opened_at": "2024-01-01T00:00:00Z",
                "quantity_opened": Decimal("2"),
                "quantity_closed": Decimal("2"),
                "average_entry_price": Decimal("100"),
            }
        )
