"""Deterministic lifecycle state machine for trading-core entities."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from types import MappingProxyType
from typing import Callable, Mapping, Sequence


class OrderLifecycleState(str, Enum):
    CREATED = "created"
    SUBMITTED = "submitted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class TradeLifecycleState(str, Enum):
    OPEN = "open"
    CLOSED = "closed"


class PositionLifecycleState(str, Enum):
    FLAT = "flat"
    OPEN = "open"
    CLOSED = "closed"


class TradingLifecycleTransitionError(ValueError):
    """Raised when a lifecycle transition is not explicitly allowed."""


class TradingLifecycleInvariantError(ValueError):
    """Raised when lifecycle invariants are violated."""


_ORDER_ALLOWED_TRANSITIONS_MUTABLE: dict[OrderLifecycleState, frozenset[OrderLifecycleState]] = {
    OrderLifecycleState.CREATED: frozenset(
        {
            OrderLifecycleState.SUBMITTED,
            OrderLifecycleState.CANCELLED,
            OrderLifecycleState.REJECTED,
        }
    ),
    OrderLifecycleState.SUBMITTED: frozenset(
        {
            OrderLifecycleState.PARTIALLY_FILLED,
            OrderLifecycleState.FILLED,
            OrderLifecycleState.CANCELLED,
            OrderLifecycleState.REJECTED,
        }
    ),
    OrderLifecycleState.PARTIALLY_FILLED: frozenset({OrderLifecycleState.FILLED}),
    OrderLifecycleState.FILLED: frozenset(),
    OrderLifecycleState.CANCELLED: frozenset(),
    OrderLifecycleState.REJECTED: frozenset(),
}

_TRADE_ALLOWED_TRANSITIONS_MUTABLE: dict[TradeLifecycleState, frozenset[TradeLifecycleState]] = {
    TradeLifecycleState.OPEN: frozenset({TradeLifecycleState.CLOSED}),
    TradeLifecycleState.CLOSED: frozenset(),
}

_POSITION_ALLOWED_TRANSITIONS_MUTABLE: dict[PositionLifecycleState, frozenset[PositionLifecycleState]] = {
    PositionLifecycleState.FLAT: frozenset({PositionLifecycleState.OPEN}),
    PositionLifecycleState.OPEN: frozenset({PositionLifecycleState.CLOSED}),
    PositionLifecycleState.CLOSED: frozenset(),
}

ORDER_ALLOWED_TRANSITIONS = MappingProxyType(_ORDER_ALLOWED_TRANSITIONS_MUTABLE)
TRADE_ALLOWED_TRANSITIONS = MappingProxyType(_TRADE_ALLOWED_TRANSITIONS_MUTABLE)
POSITION_ALLOWED_TRANSITIONS = MappingProxyType(_POSITION_ALLOWED_TRANSITIONS_MUTABLE)

ORDER_TERMINAL_STATES: frozenset[OrderLifecycleState] = frozenset(
    {
        OrderLifecycleState.FILLED,
        OrderLifecycleState.CANCELLED,
        OrderLifecycleState.REJECTED,
    }
)
TRADE_TERMINAL_STATES: frozenset[TradeLifecycleState] = frozenset({TradeLifecycleState.CLOSED})
POSITION_TERMINAL_STATES: frozenset[PositionLifecycleState] = frozenset({PositionLifecycleState.CLOSED})


def _validate_transition(
    *,
    entity_name: str,
    current_state: Enum,
    target_state: Enum,
    allowed_transitions: Mapping[Enum, frozenset[Enum]],
    terminal_states: frozenset[Enum],
) -> None:
    if current_state == target_state:
        raise TradingLifecycleTransitionError(
            f"Illegal {entity_name} lifecycle transition: {current_state.value} -> {target_state.value}"
        )

    allowed_targets = allowed_transitions[current_state]
    if target_state in allowed_targets:
        return

    if current_state in terminal_states:
        raise TradingLifecycleTransitionError(
            f"Illegal {entity_name} lifecycle transition: {current_state.value} is terminal"
        )

    raise TradingLifecycleTransitionError(
        f"Illegal {entity_name} lifecycle transition: {current_state.value} -> {target_state.value}"
    )


def _validate_transition_sequence(
    *,
    states: Sequence[Enum],
    validate_step: Callable[[Enum, Enum], None],
) -> None:
    if len(states) < 2:
        return
    for index in range(1, len(states)):
        validate_step(states[index - 1], states[index])


def get_allowed_order_transitions(state: OrderLifecycleState) -> frozenset[OrderLifecycleState]:
    return ORDER_ALLOWED_TRANSITIONS[state]


def get_allowed_trade_transitions(state: TradeLifecycleState) -> frozenset[TradeLifecycleState]:
    return TRADE_ALLOWED_TRANSITIONS[state]


def get_allowed_position_transitions(state: PositionLifecycleState) -> frozenset[PositionLifecycleState]:
    return POSITION_ALLOWED_TRANSITIONS[state]


def validate_order_transition(current_state: OrderLifecycleState, target_state: OrderLifecycleState) -> None:
    _validate_transition(
        entity_name="Order",
        current_state=current_state,
        target_state=target_state,
        allowed_transitions=ORDER_ALLOWED_TRANSITIONS,
        terminal_states=ORDER_TERMINAL_STATES,
    )


def validate_trade_transition(current_state: TradeLifecycleState, target_state: TradeLifecycleState) -> None:
    _validate_transition(
        entity_name="Trade",
        current_state=current_state,
        target_state=target_state,
        allowed_transitions=TRADE_ALLOWED_TRANSITIONS,
        terminal_states=TRADE_TERMINAL_STATES,
    )


def validate_position_transition(
    current_state: PositionLifecycleState,
    target_state: PositionLifecycleState,
) -> None:
    _validate_transition(
        entity_name="Position",
        current_state=current_state,
        target_state=target_state,
        allowed_transitions=POSITION_ALLOWED_TRANSITIONS,
        terminal_states=POSITION_TERMINAL_STATES,
    )


def validate_order_transition_sequence(states: Sequence[OrderLifecycleState]) -> None:
    _validate_transition_sequence(
        states=states,
        validate_step=lambda current, target: validate_order_transition(
            current_state=current,  # type: ignore[arg-type]
            target_state=target,  # type: ignore[arg-type]
        ),
    )


def validate_trade_transition_sequence(states: Sequence[TradeLifecycleState]) -> None:
    _validate_transition_sequence(
        states=states,
        validate_step=lambda current, target: validate_trade_transition(
            current_state=current,  # type: ignore[arg-type]
            target_state=target,  # type: ignore[arg-type]
        ),
    )


def validate_position_transition_sequence(states: Sequence[PositionLifecycleState]) -> None:
    _validate_transition_sequence(
        states=states,
        validate_step=lambda current, target: validate_position_transition(
            current_state=current,  # type: ignore[arg-type]
            target_state=target,  # type: ignore[arg-type]
        ),
    )


def validate_order_state_invariants(
    *,
    status: OrderLifecycleState,
    quantity: Decimal,
    filled_quantity: Decimal,
) -> None:
    if filled_quantity > quantity:
        raise TradingLifecycleInvariantError("Order invariant violation: filled_quantity must not exceed quantity")

    if status in {
        OrderLifecycleState.CREATED,
        OrderLifecycleState.SUBMITTED,
        OrderLifecycleState.CANCELLED,
        OrderLifecycleState.REJECTED,
    }:
        if filled_quantity != Decimal("0"):
            raise TradingLifecycleInvariantError(
                "Order invariant violation: non-fill states must have filled_quantity equal to zero"
            )
        return

    if status == OrderLifecycleState.PARTIALLY_FILLED:
        if filled_quantity <= Decimal("0"):
            raise TradingLifecycleInvariantError(
                "Order invariant violation: partially_filled requires positive filled_quantity"
            )
        if filled_quantity >= quantity:
            raise TradingLifecycleInvariantError(
                "Order invariant violation: partially_filled requires filled_quantity less than quantity"
            )
        return

    if status == OrderLifecycleState.FILLED and filled_quantity != quantity:
        raise TradingLifecycleInvariantError(
            "Order invariant violation: filled state requires filled_quantity equal to quantity"
        )


def validate_trade_state_invariants(
    *,
    status: TradeLifecycleState,
    quantity_opened: Decimal,
    quantity_closed: Decimal,
) -> None:
    if quantity_closed > quantity_opened:
        raise TradingLifecycleInvariantError("Trade invariant violation: quantity_closed must not exceed quantity_opened")

    if status == TradeLifecycleState.OPEN and quantity_closed >= quantity_opened:
        raise TradingLifecycleInvariantError(
            "Trade invariant violation: open state requires quantity_closed less than quantity_opened"
        )

    if status == TradeLifecycleState.CLOSED and quantity_closed != quantity_opened:
        raise TradingLifecycleInvariantError(
            "Trade invariant violation: closed state requires quantity_closed equal to quantity_opened"
        )


def validate_position_state_invariants(
    *,
    status: PositionLifecycleState,
    quantity_opened: Decimal,
    quantity_closed: Decimal,
    net_quantity: Decimal,
) -> None:
    if quantity_closed > quantity_opened:
        raise TradingLifecycleInvariantError(
            "Position invariant violation: quantity_closed must not exceed quantity_opened"
        )
    if net_quantity != quantity_opened - quantity_closed:
        raise TradingLifecycleInvariantError(
            "Position invariant violation: net_quantity must equal quantity_opened minus quantity_closed"
        )

    if status == PositionLifecycleState.FLAT:
        if any(value != Decimal("0") for value in (quantity_opened, quantity_closed, net_quantity)):
            raise TradingLifecycleInvariantError(
                "Position invariant violation: flat state requires all quantities to be zero"
            )
        return

    if status == PositionLifecycleState.OPEN and net_quantity <= Decimal("0"):
        raise TradingLifecycleInvariantError("Position invariant violation: open state requires positive net_quantity")

    if status == PositionLifecycleState.CLOSED:
        if net_quantity != Decimal("0"):
            raise TradingLifecycleInvariantError(
                "Position invariant violation: closed state requires net_quantity equal to zero"
            )
        if quantity_opened != quantity_closed:
            raise TradingLifecycleInvariantError(
                "Position invariant violation: closed state requires quantity_closed equal to quantity_opened"
            )


@dataclass(frozen=True)
class OrderLifecycleSnapshot:
    status: OrderLifecycleState
    quantity: Decimal
    filled_quantity: Decimal


@dataclass(frozen=True)
class TradeLifecycleSnapshot:
    status: TradeLifecycleState
    quantity_opened: Decimal
    quantity_closed: Decimal


@dataclass(frozen=True)
class PositionLifecycleSnapshot:
    status: PositionLifecycleState
    quantity_opened: Decimal
    quantity_closed: Decimal
    net_quantity: Decimal


def validate_order_transition_invariants(
    *,
    current: OrderLifecycleSnapshot,
    target: OrderLifecycleSnapshot,
) -> None:
    validate_order_transition(current_state=current.status, target_state=target.status)
    if target.quantity != current.quantity:
        raise TradingLifecycleInvariantError("Order transition invariant violation: quantity must be immutable")
    if target.filled_quantity < current.filled_quantity:
        raise TradingLifecycleInvariantError(
            "Order transition invariant violation: filled_quantity must be monotonic non-decreasing"
        )
    validate_order_state_invariants(
        status=target.status,
        quantity=target.quantity,
        filled_quantity=target.filled_quantity,
    )


def validate_trade_transition_invariants(
    *,
    current: TradeLifecycleSnapshot,
    target: TradeLifecycleSnapshot,
) -> None:
    validate_trade_transition(current_state=current.status, target_state=target.status)
    if target.quantity_opened != current.quantity_opened:
        raise TradingLifecycleInvariantError("Trade transition invariant violation: quantity_opened must be immutable")
    if target.quantity_closed < current.quantity_closed:
        raise TradingLifecycleInvariantError(
            "Trade transition invariant violation: quantity_closed must be monotonic non-decreasing"
        )
    validate_trade_state_invariants(
        status=target.status,
        quantity_opened=target.quantity_opened,
        quantity_closed=target.quantity_closed,
    )


def validate_position_transition_invariants(
    *,
    current: PositionLifecycleSnapshot,
    target: PositionLifecycleSnapshot,
) -> None:
    validate_position_transition(current_state=current.status, target_state=target.status)
    if target.quantity_opened != current.quantity_opened:
        raise TradingLifecycleInvariantError(
            "Position transition invariant violation: quantity_opened must be immutable"
        )
    if target.quantity_closed < current.quantity_closed:
        raise TradingLifecycleInvariantError(
            "Position transition invariant violation: quantity_closed must be monotonic non-decreasing"
        )
    validate_position_state_invariants(
        status=target.status,
        quantity_opened=target.quantity_opened,
        quantity_closed=target.quantity_closed,
        net_quantity=target.net_quantity,
    )

