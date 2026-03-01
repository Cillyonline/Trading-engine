"""Deterministic market order execution model for backtesting.

This module defines deterministic market order filling, slippage, commission,
and position transition behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
import inspect
from typing import Any, Literal, Mapping, Sequence

from risk.contracts import RiskDecision

from cilly_trading.engine.risk import enforce_approved_risk_decision


@dataclass(frozen=True)
class Order:
    """Represents an order submitted to the deterministic executor.

    Args:
        id: Stable order identifier.
        side: Order side (``"BUY"`` or ``"SELL"``).
        quantity: Requested quantity.
        created_snapshot_key: Snapshot key where the order was created.
        sequence: Monotonic sequence number for deterministic tie-breaking.
    """

    id: str
    side: Literal["BUY", "SELL"]
    quantity: Decimal
    created_snapshot_key: str
    sequence: int


@dataclass(frozen=True)
class Fill:
    """Represents a deterministic full fill for an order.

    Args:
        order_id: Filled order identifier.
        fill_price: Deterministic execution price including slippage.
        quantity: Filled quantity.
        commission: Deterministic commission amount.
    """

    order_id: str
    fill_price: Decimal
    quantity: Decimal
    commission: Decimal


@dataclass(frozen=True)
class Position:
    """Represents deterministic position state.

    Args:
        quantity: Current position quantity.
        avg_price: Weighted average entry price for remaining quantity.
    """

    quantity: Decimal
    avg_price: Decimal


@dataclass(frozen=True)
class DeterministicExecutionConfig:
    """Configuration for deterministic order execution.

    Args:
        slippage_bps: Fixed slippage in basis points.
        commission_per_order: Fixed deterministic commission per order.
        price_scale: Decimal scale for prices.
        money_scale: Decimal scale for commission amounts.
        quantity_scale: Decimal scale for quantity tracking.
        fill_timing: Fill timing mode. ``"next_snapshot"`` fills an order only
            after its creation snapshot. ``"same_snapshot"`` allows filling on
            creation snapshot.
    """

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
) -> tuple[list[Fill], Position]:
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
    ) -> tuple[list[Fill], Position]:
        """Executes ready orders for a snapshot in deterministic order.

        Args:
            orders: Orders that may be filled at this snapshot.
            snapshot: Market snapshot providing ``open`` or ``price``.
            position: Existing position state.
            config: Deterministic execution settings.
            risk_decision: Mandatory explicit pre-execution risk decision.

        Returns:
            A tuple containing ordered fills and updated position.

        Raises:
            ValueError: If a required price is missing, a quantity is invalid,
                or an order attempts to sell more than current position.
        """

        enforce_approved_risk_decision(risk_decision)

        snapshot_key = self._snapshot_key(snapshot)
        base_price = self._extract_fill_price(snapshot, config)
        current = Position(
            quantity=self._q(position.quantity, config.quantity_scale),
            avg_price=self._q(position.avg_price, config.price_scale),
        )
        ordered_orders = sorted(
            orders,
            key=lambda order: (order.created_snapshot_key, order.sequence, order.id),
        )

        fills: list[Fill] = []
        for order in ordered_orders:
            quantity = self._q(order.quantity, config.quantity_scale)
            if quantity <= Decimal("0"):
                raise ValueError(f"Order quantity must be positive: {order.id}")
            if not self._is_ready(order=order, snapshot_key=snapshot_key, config=config):
                continue

            fill_price = self._apply_slippage(price=base_price, side=order.side, config=config)
            commission = self._q(config.commission_per_order, config.money_scale)
            fills.append(
                Fill(
                    order_id=order.id,
                    fill_price=fill_price,
                    quantity=quantity,
                    commission=commission,
                )
            )
            current = self._apply_fill(position=current, side=order.side, quantity=quantity, fill_price=fill_price, config=config)

        return fills, current

    def _apply_fill(
        self,
        *,
        position: Position,
        side: Literal["BUY", "SELL"],
        quantity: Decimal,
        fill_price: Decimal,
        config: DeterministicExecutionConfig,
    ) -> Position:
        if side == "BUY":
            new_qty = self._q(position.quantity + quantity, config.quantity_scale)
            if new_qty == Decimal("0"):
                return Position(quantity=Decimal("0"), avg_price=Decimal("0"))
            weighted = (position.avg_price * position.quantity) + (fill_price * quantity)
            avg_price = self._q(weighted / new_qty, config.price_scale)
            return Position(quantity=new_qty, avg_price=avg_price)

        if quantity > position.quantity:
            raise ValueError("SELL quantity exceeds current position quantity")

        remaining = self._q(position.quantity - quantity, config.quantity_scale)
        if remaining == Decimal("0"):
            return Position(quantity=Decimal("0"), avg_price=Decimal("0"))
        return Position(quantity=remaining, avg_price=self._q(position.avg_price, config.price_scale))

    def _is_ready(
        self,
        *,
        order: Order,
        snapshot_key: str,
        config: DeterministicExecutionConfig,
    ) -> bool:
        if config.fill_timing == "same_snapshot":
            return order.created_snapshot_key <= snapshot_key
        return order.created_snapshot_key < snapshot_key

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


__all__ = [
    "DeterministicExecutionConfig",
    "Fill",
    "Order",
    "Position",
]
