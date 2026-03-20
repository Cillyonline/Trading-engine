"""Deterministic market-order execution model for backtesting."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
import inspect
from typing import Any, Literal, Mapping, Sequence

from risk.contracts import RiskDecision

from cilly_trading.engine.risk import enforce_approved_risk_decision
from cilly_trading.models import ExecutionEvent, Order, Position, compute_execution_event_id


@dataclass(frozen=True)
class DeterministicExecutionConfig:
    """Configuration for deterministic order execution."""

    slippage_bps: int
    commission_per_order: Decimal
    price_scale: Decimal = Decimal("0.00000001")
    money_scale: Decimal = Decimal("0.01")
    quantity_scale: Decimal = Decimal("0.00000001")
    fill_timing: Literal["next_snapshot", "same_snapshot"] = "next_snapshot"


def _enforce_orchestrator_caller() -> None:
    for frame_info in inspect.stack()[1:]:
        caller_module = frame_info.frame.f_globals.get("__name__")
        if caller_module == "cilly_trading.engine.pipeline.orchestrator":
            return
    raise RuntimeError(
        "Execution entrypoint is restricted to cilly_trading.engine.pipeline.orchestrator"
    )


def _execute_order(
    *,
    orders: Sequence[Order],
    snapshot: Mapping[str, Any],
    position: Position,
    config: DeterministicExecutionConfig,
    risk_decision: RiskDecision | None,
) -> tuple[list[ExecutionEvent], Position]:
    _enforce_orchestrator_caller()
    model = _DeterministicExecutionModel()
    return model._execute(
        orders=orders,
        snapshot=snapshot,
        position=position,
        config=config,
        risk_decision=risk_decision,
    )


class _DeterministicExecutionModel:
    """Executes market orders with deterministic semantics."""

    def _execute(
        self,
        *,
        orders: Sequence[Order],
        snapshot: Mapping[str, Any],
        position: Position,
        config: DeterministicExecutionConfig,
        risk_decision: RiskDecision | None,
    ) -> tuple[list[ExecutionEvent], Position]:
        enforce_approved_risk_decision(risk_decision)

        snapshot_key = self._snapshot_key(snapshot)
        base_price = self._extract_fill_price(snapshot, config)
        current = position
        ordered_orders = sorted(
            orders,
            key=lambda order: (order.created_at, order.sequence, order.order_id),
        )

        execution_events: list[ExecutionEvent] = []
        for order in ordered_orders:
            quantity = self._q(order.quantity, config.quantity_scale)
            if quantity <= Decimal("0"):
                raise ValueError(f"Order quantity must be positive: {order.order_id}")
            if not self._is_ready(order=order, snapshot_key=snapshot_key, config=config):
                continue

            execution_price = self._apply_slippage(price=base_price, side=order.side, config=config)
            commission = self._q(config.commission_per_order, config.money_scale)
            event = ExecutionEvent(
                event_id=compute_execution_event_id(
                    order_id=order.order_id,
                    event_type="filled",
                    occurred_at=snapshot_key,
                    sequence=len(execution_events) + 1,
                ),
                order_id=order.order_id,
                strategy_id=order.strategy_id,
                symbol=order.symbol,
                side=order.side,
                event_type="filled",
                occurred_at=snapshot_key,
                sequence=len(execution_events) + 1,
                execution_quantity=quantity,
                execution_price=execution_price,
                commission=commission,
                position_id=order.position_id or current.position_id,
                trade_id=order.trade_id,
            )
            execution_events.append(event)
            current = self._apply_fill(
                position=current,
                order=order,
                event=event,
                config=config,
            )

        return execution_events, current

    def _apply_fill(
        self,
        *,
        position: Position,
        order: Order,
        event: ExecutionEvent,
        config: DeterministicExecutionConfig,
    ) -> Position:
        quantity = event.execution_quantity
        execution_price = event.execution_price
        if quantity is None or execution_price is None:
            raise ValueError("fill events must define execution_quantity and execution_price")

        order_ids = self._merge_ids(position.order_ids, order.order_id)
        event_ids = self._merge_ids(position.execution_event_ids, event.event_id)
        trade_ids = self._merge_ids(position.trade_ids, order.trade_id)

        if order.side == "BUY":
            quantity_opened = self._q(position.quantity_opened + quantity, config.quantity_scale)
            net_quantity = self._q(position.net_quantity + quantity, config.quantity_scale)
            if quantity_opened == Decimal("0"):
                average_entry_price = Decimal("0")
            else:
                weighted = (
                    position.average_entry_price * position.quantity_opened
                ) + (execution_price * quantity)
                average_entry_price = self._q(weighted / quantity_opened, config.price_scale)

            return Position.model_validate(
                {
                    **position.model_dump(mode="python"),
                    "opened_at": position.opened_at if position.status != "flat" else event.occurred_at,
                    "status": "open",
                    "closed_at": None,
                    "quantity_opened": quantity_opened,
                    "net_quantity": net_quantity,
                    "average_entry_price": average_entry_price,
                    "order_ids": order_ids,
                    "execution_event_ids": event_ids,
                    "trade_ids": trade_ids,
                }
            )

        if quantity > position.net_quantity:
            raise ValueError("SELL quantity exceeds current position quantity")

        quantity_closed = self._q(position.quantity_closed + quantity, config.quantity_scale)
        net_quantity = self._q(position.net_quantity - quantity, config.quantity_scale)
        previous_exit_notional = (
            position.average_exit_price * position.quantity_closed
            if position.average_exit_price is not None
            else Decimal("0")
        )
        average_exit_price = self._q(
            (previous_exit_notional + (execution_price * quantity)) / quantity_closed,
            config.price_scale,
        )
        realized_pnl = self._q(
            (position.realized_pnl or Decimal("0"))
            + ((execution_price - position.average_entry_price) * quantity),
            config.money_scale,
        )

        status = "closed" if net_quantity == Decimal("0") else "open"
        closed_at = event.occurred_at if status == "closed" else None

        return Position.model_validate(
            {
                **position.model_dump(mode="python"),
                "status": status,
                "closed_at": closed_at,
                "quantity_closed": quantity_closed,
                "net_quantity": net_quantity,
                "average_exit_price": average_exit_price,
                "realized_pnl": realized_pnl,
                "order_ids": order_ids,
                "execution_event_ids": event_ids,
                "trade_ids": trade_ids,
            }
        )

    def _is_ready(
        self,
        *,
        order: Order,
        snapshot_key: str,
        config: DeterministicExecutionConfig,
    ) -> bool:
        if config.fill_timing == "same_snapshot":
            return order.created_at <= snapshot_key
        return order.created_at < snapshot_key

    def _extract_fill_price(self, snapshot: Mapping[str, Any], config: DeterministicExecutionConfig) -> Decimal:
        if snapshot.get("open") is not None:
            return self._q(Decimal(str(snapshot["open"])), config.price_scale)
        if snapshot.get("price") is not None:
            return self._q(Decimal(str(snapshot["price"])), config.price_scale)
        raise ValueError("Snapshot must contain either 'open' or 'price'")

    def _apply_slippage(
        self,
        *,
        price: Decimal,
        side: Literal["BUY", "SELL"],
        config: DeterministicExecutionConfig,
    ) -> Decimal:
        slippage_fraction = Decimal(config.slippage_bps) / Decimal("10000")
        if side == "BUY":
            return self._q(price * (Decimal("1") + slippage_fraction), config.price_scale)
        return self._q(price * (Decimal("1") - slippage_fraction), config.price_scale)

    def _snapshot_key(self, snapshot: Mapping[str, Any]) -> str:
        if snapshot.get("timestamp") is not None:
            return str(snapshot["timestamp"])
        if snapshot.get("snapshot_key") is not None:
            return str(snapshot["snapshot_key"])
        if snapshot.get("id") is not None:
            return str(snapshot["id"])
        raise ValueError("Snapshot must contain one of: timestamp, snapshot_key, id")

    def _q(self, value: Decimal, scale: Decimal) -> Decimal:
        return value.quantize(scale, rounding=ROUND_HALF_UP)

    def _merge_ids(self, current_ids: Sequence[str], candidate: str | None) -> list[str]:
        values = set(current_ids)
        if candidate is not None:
            values.add(candidate)
        return sorted(values)


__all__ = [
    "DeterministicExecutionConfig",
    "ExecutionEvent",
    "Order",
    "Position",
]
