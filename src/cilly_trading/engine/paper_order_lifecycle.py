"""Deterministic paper-order lifecycle simulator aligned with Trading Core semantics."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal, Sequence

from cilly_trading.models import ExecutionEvent, Order, compute_execution_event_id
from cilly_trading.trading_lifecycle import (
    OrderLifecycleSnapshot,
    OrderLifecycleState,
    validate_order_transition_invariants,
)


PaperOrderAction = Literal["fill", "cancel"]


@dataclass(frozen=True)
class PaperOrderLifecycleRequest:
    order_id: str
    strategy_id: str
    symbol: str
    side: Literal["BUY", "SELL"]
    quantity: Decimal
    created_at: str
    submitted_at: str
    sequence: int = 1
    order_type: Literal["market"] = "market"
    time_in_force: Literal["day", "gtc"] = "day"
    position_id: str | None = None
    trade_id: str | None = None
    max_fill_per_step: Decimal | None = None


@dataclass(frozen=True)
class PaperOrderStep:
    occurred_at: str
    action: PaperOrderAction
    quantity: Decimal | None = None
    price: Decimal | None = None
    commission: Decimal = Decimal("0")


@dataclass(frozen=True)
class PaperOrderLifecycleResult:
    orders: tuple[Order, ...]
    execution_events: tuple[ExecutionEvent, ...]

    @property
    def final_order(self) -> Order:
        return self.orders[-1]


class PaperOrderLifecycleSimulator:
    """Deterministic state machine for paper-order submission/fill/cancel progression."""

    def run(
        self,
        *,
        request: PaperOrderLifecycleRequest,
        steps: Sequence[PaperOrderStep],
    ) -> PaperOrderLifecycleResult:
        self._validate_request(request)

        orders: list[Order] = []
        events: list[ExecutionEvent] = []

        created_order = self._build_order(
            request=request,
            status="created",
            filled_quantity=Decimal("0"),
            average_fill_price=None,
            last_execution_event_id=None,
        )
        created_event = self._build_event(
            request=request,
            event_type="created",
            occurred_at=request.created_at,
            sequence=1,
        )
        orders.append(created_order)
        events.append(created_event)

        current_order = self._transition_order(
            current=created_order,
            status=OrderLifecycleState.SUBMITTED,
            filled_quantity=Decimal("0"),
            average_fill_price=None,
            last_execution_event_id=None,
        )
        submitted_event = self._build_event(
            request=request,
            event_type="submitted",
            occurred_at=request.submitted_at,
            sequence=2,
        )
        orders.append(current_order)
        events.append(submitted_event)

        for step in steps:
            if current_order.status in {"filled", "cancelled", "rejected"}:
                raise ValueError("paper_order_step_after_terminal_state")

            if step.action == "cancel":
                cancel_event = self._build_event(
                    request=request,
                    event_type="cancelled",
                    occurred_at=step.occurred_at,
                    sequence=len(events) + 1,
                )
                current_order = self._transition_order(
                    current=current_order,
                    status=OrderLifecycleState.CANCELLED,
                    filled_quantity=current_order.filled_quantity,
                    average_fill_price=current_order.average_fill_price,
                    last_execution_event_id=cancel_event.event_id,
                )
                orders.append(current_order)
                events.append(cancel_event)
                continue

            if step.quantity is None or step.price is None:
                raise ValueError("paper_fill_step_requires_quantity_and_price")
            if step.quantity <= Decimal("0"):
                raise ValueError("paper_fill_step_requires_positive_quantity")
            if step.price <= Decimal("0"):
                raise ValueError("paper_fill_step_requires_positive_price")
            if step.commission < Decimal("0"):
                raise ValueError("paper_fill_step_requires_non_negative_commission")

            bounded_fill_quantity = step.quantity
            if request.max_fill_per_step is not None:
                bounded_fill_quantity = min(bounded_fill_quantity, request.max_fill_per_step)

            remaining_quantity = current_order.quantity - current_order.filled_quantity
            bounded_fill_quantity = min(bounded_fill_quantity, remaining_quantity)
            if bounded_fill_quantity <= Decimal("0"):
                raise ValueError("paper_fill_step_cannot_progress_order")

            new_filled_quantity = current_order.filled_quantity + bounded_fill_quantity
            fill_event_type: Literal["partially_filled", "filled"] = (
                "filled" if new_filled_quantity == current_order.quantity else "partially_filled"
            )

            fill_event = self._build_event(
                request=request,
                event_type=fill_event_type,
                occurred_at=step.occurred_at,
                sequence=len(events) + 1,
                execution_quantity=bounded_fill_quantity,
                execution_price=step.price,
                commission=step.commission,
            )

            average_fill_price = self._weighted_average_fill_price(
                prior_average=current_order.average_fill_price,
                prior_filled=current_order.filled_quantity,
                fill_price=step.price,
                fill_quantity=bounded_fill_quantity,
                new_filled=new_filled_quantity,
            )

            current_order = self._transition_order(
                current=current_order,
                status=OrderLifecycleState(fill_event_type),
                filled_quantity=new_filled_quantity,
                average_fill_price=average_fill_price,
                last_execution_event_id=fill_event.event_id,
            )
            orders.append(current_order)
            events.append(fill_event)

        return PaperOrderLifecycleResult(
            orders=tuple(orders),
            execution_events=tuple(events),
        )

    def _validate_request(self, request: PaperOrderLifecycleRequest) -> None:
        if request.quantity <= Decimal("0"):
            raise ValueError("paper_order_quantity_must_be_positive")
        if request.max_fill_per_step is not None and request.max_fill_per_step <= Decimal("0"):
            raise ValueError("paper_order_max_fill_per_step_must_be_positive")

    def _build_order(
        self,
        *,
        request: PaperOrderLifecycleRequest,
        status: Literal["created", "submitted", "partially_filled", "filled", "cancelled", "rejected"],
        filled_quantity: Decimal,
        average_fill_price: Decimal | None,
        last_execution_event_id: str | None,
    ) -> Order:
        return Order.model_validate(
            {
                "order_id": request.order_id,
                "strategy_id": request.strategy_id,
                "symbol": request.symbol,
                "sequence": request.sequence,
                "side": request.side,
                "order_type": request.order_type,
                "time_in_force": request.time_in_force,
                "status": status,
                "quantity": request.quantity,
                "filled_quantity": filled_quantity,
                "created_at": request.created_at,
                "submitted_at": request.submitted_at,
                "average_fill_price": average_fill_price,
                "last_execution_event_id": last_execution_event_id,
                "position_id": request.position_id,
                "trade_id": request.trade_id,
            }
        )

    def _transition_order(
        self,
        *,
        current: Order,
        status: OrderLifecycleState,
        filled_quantity: Decimal,
        average_fill_price: Decimal | None,
        last_execution_event_id: str | None,
    ) -> Order:
        target = Order.model_validate(
            {
                **current.model_dump(mode="python"),
                "status": status.value,
                "filled_quantity": filled_quantity,
                "average_fill_price": average_fill_price,
                "last_execution_event_id": last_execution_event_id,
            }
        )

        validate_order_transition_invariants(
            current=OrderLifecycleSnapshot(
                status=OrderLifecycleState(current.status),
                quantity=current.quantity,
                filled_quantity=current.filled_quantity,
            ),
            target=OrderLifecycleSnapshot(
                status=OrderLifecycleState(target.status),
                quantity=target.quantity,
                filled_quantity=target.filled_quantity,
            ),
        )
        return target

    def _build_event(
        self,
        *,
        request: PaperOrderLifecycleRequest,
        event_type: Literal[
            "created",
            "submitted",
            "partially_filled",
            "filled",
            "cancelled",
            "rejected",
        ],
        occurred_at: str,
        sequence: int,
        execution_quantity: Decimal | None = None,
        execution_price: Decimal | None = None,
        commission: Decimal | None = None,
    ) -> ExecutionEvent:
        payload: dict[str, object] = {
            "event_id": compute_execution_event_id(
                order_id=request.order_id,
                event_type=event_type,
                occurred_at=occurred_at,
                sequence=sequence,
            ),
            "order_id": request.order_id,
            "strategy_id": request.strategy_id,
            "symbol": request.symbol,
            "side": request.side,
            "event_type": event_type,
            "occurred_at": occurred_at,
            "sequence": sequence,
            "position_id": request.position_id,
            "trade_id": request.trade_id,
        }

        if event_type in {"partially_filled", "filled"}:
            payload["execution_quantity"] = execution_quantity
            payload["execution_price"] = execution_price
            payload["commission"] = commission

        return ExecutionEvent.model_validate(payload)

    def _weighted_average_fill_price(
        self,
        *,
        prior_average: Decimal | None,
        prior_filled: Decimal,
        fill_price: Decimal,
        fill_quantity: Decimal,
        new_filled: Decimal,
    ) -> Decimal:
        prior_notional = (prior_average or Decimal("0")) * prior_filled
        new_notional = prior_notional + (fill_price * fill_quantity)
        return new_notional / new_filled


__all__ = [
    "PaperOrderLifecycleRequest",
    "PaperOrderLifecycleResult",
    "PaperOrderLifecycleSimulator",
    "PaperOrderStep",
]
