from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal, Optional, Sequence

from fastapi import HTTPException

from cilly_trading.models import ExecutionEvent, Order, Position, Trade


def paginate_items(items: list[object], *, limit: int, offset: int) -> tuple[list[object], int]:
    total = len(items)
    return items[offset : offset + limit], total


def resolve_paper_starting_cash() -> Decimal:
    raw_value = os.getenv("CILLY_PAPER_ACCOUNT_STARTING_CASH", "100000")
    try:
        value = Decimal(raw_value)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="paper_account_starting_cash_invalid") from exc
    if value < Decimal("0"):
        raise HTTPException(status_code=500, detail="paper_account_starting_cash_invalid")
    return value


def sum_decimals(values: list[Decimal]) -> Decimal:
    return sum(values, Decimal("0"))


@dataclass(frozen=True)
class PortfolioInspectionPositionState:
    strategy_id: str
    symbol: str
    size: Decimal
    average_price: Decimal
    unrealized_pnl: Decimal


@dataclass(frozen=True)
class _AggregatedPortfolioPosition:
    strategy_id: str
    symbol: str
    size: Decimal
    weighted_notional: Decimal
    unrealized_pnl: Decimal


@dataclass(frozen=True)
class BoundedPaperSimulationState:
    orders: tuple[Order, ...]
    execution_events: tuple[ExecutionEvent, ...]
    trades: tuple[Trade, ...]
    positions: tuple[Position, ...]
    account: dict[str, object]
    portfolio_positions: tuple[PortfolioInspectionPositionState, ...]
    reconciliation_mismatches: tuple[dict[str, Optional[str]], ...]


def build_paper_account_state(
    *,
    paper_trades: list[Trade],
    paper_positions: list[Position],
) -> dict[str, object]:
    starting_cash = resolve_paper_starting_cash()
    realized_pnl = sum_decimals([trade.realized_pnl or Decimal("0") for trade in paper_trades])
    unrealized_pnl = sum_decimals([trade.unrealized_pnl or Decimal("0") for trade in paper_trades])
    total_pnl = realized_pnl + unrealized_pnl
    cash = starting_cash + realized_pnl
    equity = cash + unrealized_pnl
    open_positions = sum(1 for position in paper_positions if position.status == "open")
    open_trades = sum(1 for trade in paper_trades if trade.status == "open")
    closed_trades = sum(1 for trade in paper_trades if trade.status == "closed")

    as_of_candidates = [
        value
        for value in [
            *[trade.closed_at for trade in paper_trades],
            *[trade.opened_at for trade in paper_trades],
        ]
        if value is not None
    ]
    as_of = max(as_of_candidates) if as_of_candidates else None

    return {
        "starting_cash": starting_cash,
        "cash": cash,
        "equity": equity,
        "realized_pnl": realized_pnl,
        "unrealized_pnl": unrealized_pnl,
        "total_pnl": total_pnl,
        "open_positions": open_positions,
        "open_trades": open_trades,
        "closed_trades": closed_trades,
        "as_of": as_of,
    }


def _ensure_unique_ids(
    *,
    items: Sequence[object],
    entity_name: str,
    id_attr: str,
) -> None:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for item in items:
        value = getattr(item, id_attr, None)
        if not isinstance(value, str):
            continue
        if value in seen:
            duplicates.add(value)
        seen.add(value)

    if duplicates:
        detail = f"bounded_simulation_state_duplicate_{entity_name}_id"
        raise HTTPException(status_code=500, detail=detail)


def validate_bounded_paper_simulation_state(
    *,
    orders: Sequence[Order],
    execution_events: Sequence[ExecutionEvent],
    trades: Sequence[Trade],
    positions: Sequence[Position],
    portfolio_positions: Sequence[PortfolioInspectionPositionState],
) -> None:
    _ensure_unique_ids(items=orders, entity_name="order", id_attr="order_id")
    _ensure_unique_ids(items=execution_events, entity_name="execution_event", id_attr="event_id")
    _ensure_unique_ids(items=trades, entity_name="trade", id_attr="trade_id")
    _ensure_unique_ids(items=positions, entity_name="position", id_attr="position_id")

    for item in portfolio_positions:
        if item.size < Decimal("0"):
            raise HTTPException(status_code=500, detail="bounded_simulation_state_negative_portfolio_size")
        if item.average_price < Decimal("0"):
            raise HTTPException(
                status_code=500,
                detail="bounded_simulation_state_negative_portfolio_average_price",
            )


def build_paper_reconciliation_mismatches(
    *,
    orders: list[Order],
    execution_events: list[ExecutionEvent],
    trades: list[Trade],
    positions: list[Position],
    account: dict[str, object],
) -> list[dict[str, Optional[str]]]:
    mismatches: list[dict[str, Optional[str]]] = []
    orders_by_id = {order.order_id: order for order in orders}
    execution_events_by_id = {event.event_id: event for event in execution_events}
    trades_by_id = {trade.trade_id: trade for trade in trades}
    positions_by_id = {position.position_id: position for position in positions}

    for event in execution_events:
        if event.order_id not in orders_by_id:
            mismatches.append(
                {
                    "code": "execution_event_order_missing",
                    "message": f"execution event references unknown order_id={event.order_id}",
                    "entity_type": "execution_event",
                    "entity_id": event.event_id,
                }
            )

    for trade in trades:
        if trade.position_id not in positions_by_id:
            mismatches.append(
                {
                    "code": "trade_position_missing",
                    "message": f"trade references unknown position_id={trade.position_id}",
                    "entity_type": "trade",
                    "entity_id": trade.trade_id,
                }
            )

        for order_id in [*trade.opening_order_ids, *trade.closing_order_ids]:
            order = orders_by_id.get(order_id)
            if order is None:
                mismatches.append(
                    {
                        "code": "trade_order_missing",
                        "message": f"trade references unknown order_id={order_id}",
                        "entity_type": "trade",
                        "entity_id": trade.trade_id,
                    }
                )
                continue
            if order.trade_id is not None and order.trade_id != trade.trade_id:
                mismatches.append(
                    {
                        "code": "trade_order_trade_mismatch",
                        "message": f"order trade_id={order.trade_id} does not match trade_id={trade.trade_id}",
                        "entity_type": "trade",
                        "entity_id": trade.trade_id,
                    }
                )

        for event_id in trade.execution_event_ids:
            event = execution_events_by_id.get(event_id)
            if event is None:
                mismatches.append(
                    {
                        "code": "trade_execution_event_missing",
                        "message": f"trade references unknown execution_event_id={event_id}",
                        "entity_type": "trade",
                        "entity_id": trade.trade_id,
                    }
                )
                continue
            if event.trade_id is not None and event.trade_id != trade.trade_id:
                mismatches.append(
                    {
                        "code": "trade_execution_event_trade_mismatch",
                        "message": f"execution event trade_id={event.trade_id} does not match trade_id={trade.trade_id}",
                        "entity_type": "trade",
                        "entity_id": trade.trade_id,
                    }
                )

    for position in positions:
        for trade_id in position.trade_ids:
            trade = trades_by_id.get(trade_id)
            if trade is None:
                mismatches.append(
                    {
                        "code": "position_trade_missing",
                        "message": f"position references unknown trade_id={trade_id}",
                        "entity_type": "position",
                        "entity_id": position.position_id,
                    }
                )
                continue
            if trade.position_id != position.position_id:
                mismatches.append(
                    {
                        "code": "position_trade_position_mismatch",
                        "message": f"trade position_id={trade.position_id} does not match position_id={position.position_id}",
                        "entity_type": "position",
                        "entity_id": position.position_id,
                    }
                )

        for order_id in position.order_ids:
            order = orders_by_id.get(order_id)
            if order is None:
                mismatches.append(
                    {
                        "code": "position_order_missing",
                        "message": f"position references unknown order_id={order_id}",
                        "entity_type": "position",
                        "entity_id": position.position_id,
                    }
                )
                continue
            if order.position_id is not None and order.position_id != position.position_id:
                mismatches.append(
                    {
                        "code": "position_order_position_mismatch",
                        "message": f"order position_id={order.position_id} does not match position_id={position.position_id}",
                        "entity_type": "position",
                        "entity_id": position.position_id,
                    }
                )

        for event_id in position.execution_event_ids:
            event = execution_events_by_id.get(event_id)
            if event is None:
                mismatches.append(
                    {
                        "code": "position_execution_event_missing",
                        "message": f"position references unknown execution_event_id={event_id}",
                        "entity_type": "position",
                        "entity_id": position.position_id,
                    }
                )
                continue
            if event.position_id is not None and event.position_id != position.position_id:
                mismatches.append(
                    {
                        "code": "position_execution_event_position_mismatch",
                        "message": f"execution event position_id={event.position_id} does not match position_id={position.position_id}",
                        "entity_type": "position",
                        "entity_id": position.position_id,
                    }
                )

    expected_open_trades = sum(1 for trade in trades if trade.status == "open")
    expected_closed_trades = sum(1 for trade in trades if trade.status == "closed")
    expected_open_positions = sum(1 for position in positions if position.status == "open")
    expected_realized_pnl = sum_decimals([trade.realized_pnl or Decimal("0") for trade in trades])
    expected_unrealized_pnl = sum_decimals([trade.unrealized_pnl or Decimal("0") for trade in trades])
    expected_total_pnl = expected_realized_pnl + expected_unrealized_pnl
    expected_cash = account["starting_cash"] + expected_realized_pnl
    expected_equity = expected_cash + expected_unrealized_pnl

    if account["open_trades"] != expected_open_trades:
        mismatches.append(
            {
                "code": "paper_account_open_trades_mismatch",
                "message": f"open_trades={account['open_trades']} expected={expected_open_trades}",
                "entity_type": "paper_account",
                "entity_id": "account",
            }
        )
    if account["closed_trades"] != expected_closed_trades:
        mismatches.append(
            {
                "code": "paper_account_closed_trades_mismatch",
                "message": f"closed_trades={account['closed_trades']} expected={expected_closed_trades}",
                "entity_type": "paper_account",
                "entity_id": "account",
            }
        )
    if account["open_positions"] != expected_open_positions:
        mismatches.append(
            {
                "code": "paper_account_open_positions_mismatch",
                "message": f"open_positions={account['open_positions']} expected={expected_open_positions}",
                "entity_type": "paper_account",
                "entity_id": "account",
            }
        )
    if account["realized_pnl"] != expected_realized_pnl:
        mismatches.append(
            {
                "code": "paper_account_realized_pnl_mismatch",
                "message": f"realized_pnl={account['realized_pnl']} expected={expected_realized_pnl}",
                "entity_type": "paper_account",
                "entity_id": "account",
            }
        )
    if account["unrealized_pnl"] != expected_unrealized_pnl:
        mismatches.append(
            {
                "code": "paper_account_unrealized_pnl_mismatch",
                "message": f"unrealized_pnl={account['unrealized_pnl']} expected={expected_unrealized_pnl}",
                "entity_type": "paper_account",
                "entity_id": "account",
            }
        )
    if account["total_pnl"] != expected_total_pnl:
        mismatches.append(
            {
                "code": "paper_account_total_pnl_mismatch",
                "message": f"total_pnl={account['total_pnl']} expected={expected_total_pnl}",
                "entity_type": "paper_account",
                "entity_id": "account",
            }
        )
    if account["cash"] != expected_cash:
        mismatches.append(
            {
                "code": "paper_account_cash_mismatch",
                "message": f"cash={account['cash']} expected={expected_cash}",
                "entity_type": "paper_account",
                "entity_id": "account",
            }
        )
    if account["equity"] != expected_equity:
        mismatches.append(
            {
                "code": "paper_account_equity_mismatch",
                "message": f"equity={account['equity']} expected={expected_equity}",
                "entity_type": "paper_account",
                "entity_id": "account",
            }
        )

    return sorted(
        mismatches,
        key=lambda mismatch: (
            mismatch["code"] or "",
            mismatch["entity_type"] or "",
            mismatch["entity_id"] or "",
            mismatch["message"] or "",
        ),
    )


def weighted_average(*, values: list[tuple[Decimal, Decimal]]) -> Optional[Decimal]:
    total_weight = sum_decimals([weight for _, weight in values])
    if total_weight <= Decimal("0"):
        return None
    weighted_sum = sum_decimals([value * weight for value, weight in values])
    return weighted_sum / total_weight


def build_portfolio_positions_from_trades(
    *,
    trades: Sequence[Trade],
) -> list[PortfolioInspectionPositionState]:
    aggregates: dict[tuple[str, str], _AggregatedPortfolioPosition] = {}
    for trade in trades:
        if trade.status != "open":
            continue
        if trade.quantity_opened <= Decimal("0"):
            continue
        if trade.average_entry_price <= Decimal("0"):
            continue
        remaining_quantity = trade.quantity_opened - trade.quantity_closed
        if remaining_quantity <= Decimal("0"):
            continue

        key = (trade.strategy_id, trade.symbol)
        existing = aggregates.get(key)
        remaining_notional = remaining_quantity * trade.average_entry_price
        trade_unrealized_pnl = trade.unrealized_pnl or Decimal("0")

        if existing is None:
            aggregates[key] = _AggregatedPortfolioPosition(
                strategy_id=trade.strategy_id,
                symbol=trade.symbol,
                size=remaining_quantity,
                weighted_notional=remaining_notional,
                unrealized_pnl=trade_unrealized_pnl,
            )
            continue

        aggregates[key] = _AggregatedPortfolioPosition(
            strategy_id=existing.strategy_id,
            symbol=existing.symbol,
            size=existing.size + remaining_quantity,
            weighted_notional=existing.weighted_notional + remaining_notional,
            unrealized_pnl=existing.unrealized_pnl + trade_unrealized_pnl,
        )

    positions: list[PortfolioInspectionPositionState] = []
    for aggregate in aggregates.values():
        if aggregate.size <= Decimal("0"):
            continue
        average_price = aggregate.weighted_notional / aggregate.size
        positions.append(
            PortfolioInspectionPositionState(
                strategy_id=aggregate.strategy_id,
                symbol=aggregate.symbol,
                size=aggregate.size,
                average_price=average_price,
                unrealized_pnl=aggregate.unrealized_pnl,
            )
        )

    return sorted(
        positions,
        key=lambda item: (
            item.symbol,
            item.strategy_id,
            item.size,
            item.average_price,
            item.unrealized_pnl,
        ),
    )


def _filter_trades(
    *,
    trades: Sequence[Trade],
    strategy_id: Optional[str],
    symbol: Optional[str],
    position_id: Optional[str],
) -> list[Trade]:
    filtered = list(trades)
    if strategy_id is not None:
        filtered = [item for item in filtered if item.strategy_id == strategy_id]
    if symbol is not None:
        filtered = [item for item in filtered if item.symbol == symbol]
    if position_id is not None:
        filtered = [item for item in filtered if item.position_id == position_id]
    return filtered


def _filter_orders(
    *,
    orders: Sequence[Order],
    strategy_id: Optional[str],
    symbol: Optional[str],
    target_position_ids: set[str],
) -> list[Order]:
    filtered = list(orders)
    if strategy_id is not None:
        filtered = [item for item in filtered if item.strategy_id == strategy_id]
    if symbol is not None:
        filtered = [item for item in filtered if item.symbol == symbol]
    if not target_position_ids:
        return []
    return [
        item for item in filtered if item.position_id is not None and item.position_id in target_position_ids
    ]


def _filter_execution_events(
    *,
    events: Sequence[ExecutionEvent],
    strategy_id: Optional[str],
    symbol: Optional[str],
    target_position_ids: set[str],
) -> list[ExecutionEvent]:
    filtered = list(events)
    if strategy_id is not None:
        filtered = [item for item in filtered if item.strategy_id == strategy_id]
    if symbol is not None:
        filtered = [item for item in filtered if item.symbol == symbol]
    if not target_position_ids:
        return []
    return [
        item for item in filtered if item.position_id is not None and item.position_id in target_position_ids
    ]


def build_trading_core_positions(
    *,
    canonical_execution_repo: Any,
    strategy_id: Optional[str] = None,
    symbol: Optional[str] = None,
    position_id: Optional[str] = None,
    trades: Optional[list[Trade]] = None,
    orders: Optional[list[Order]] = None,
    events: Optional[list[ExecutionEvent]] = None,
) -> list[Position]:
    if trades is None:
        trades = canonical_execution_repo.list_trades(
            strategy_id=strategy_id,
            symbol=symbol,
            position_id=position_id,
            limit=1_000_000,
            offset=0,
        )
    else:
        trades = _filter_trades(
            trades=trades,
            strategy_id=strategy_id,
            symbol=symbol,
            position_id=position_id,
        )
    if not trades:
        return []

    target_position_ids = {trade.position_id for trade in trades}
    if orders is None:
        orders = canonical_execution_repo.list_orders(
            strategy_id=strategy_id,
            symbol=symbol,
            limit=1_000_000,
            offset=0,
        )
    else:
        orders = _filter_orders(
            orders=orders,
            strategy_id=strategy_id,
            symbol=symbol,
            target_position_ids=target_position_ids,
        )

    if events is None:
        events = canonical_execution_repo.list_execution_events(
            strategy_id=strategy_id,
            symbol=symbol,
            limit=1_000_000,
            offset=0,
        )
    else:
        events = _filter_execution_events(
            events=events,
            strategy_id=strategy_id,
            symbol=symbol,
            target_position_ids=target_position_ids,
        )

    orders_by_position: dict[str, list[Order]] = {}
    events_by_position: dict[str, list[ExecutionEvent]] = {}
    trades_by_position: dict[str, list[Trade]] = {}

    for trade in trades:
        trades_by_position.setdefault(trade.position_id, []).append(trade)
    for order in orders:
        if order.position_id is None:
            continue
        orders_by_position.setdefault(order.position_id, []).append(order)
    for event in events:
        if event.position_id is None:
            continue
        events_by_position.setdefault(event.position_id, []).append(event)

    positions: list[Position] = []
    for current_position_id in sorted(target_position_ids):
        position_trades = trades_by_position.get(current_position_id, [])
        if not position_trades:
            continue

        position_orders = orders_by_position.get(current_position_id, [])
        position_events = events_by_position.get(current_position_id, [])

        strategy_ids = {trade.strategy_id for trade in position_trades}
        symbols = {trade.symbol for trade in position_trades}
        directions = {trade.direction for trade in position_trades}
        if len(strategy_ids) != 1 or len(symbols) != 1 or len(directions) != 1:
            raise HTTPException(status_code=500, detail="trading_core_position_inconsistent")

        quantity_opened = sum_decimals([trade.quantity_opened for trade in position_trades])
        quantity_closed = sum_decimals([trade.quantity_closed for trade in position_trades])
        net_quantity = quantity_opened - quantity_closed

        opened_at = min(trade.opened_at for trade in position_trades)
        closed_at_candidates = [trade.closed_at for trade in position_trades if trade.closed_at is not None]

        if quantity_opened == Decimal("0") and quantity_closed == Decimal("0"):
            status: Literal["flat", "open", "closed"] = "flat"
        elif net_quantity == Decimal("0"):
            status = "closed"
        else:
            status = "open"

        average_entry_price = weighted_average(
            values=[(trade.average_entry_price, trade.quantity_opened) for trade in position_trades]
        ) or Decimal("0")

        average_exit_price = weighted_average(
            values=[
                (trade.average_exit_price, trade.quantity_closed)
                for trade in position_trades
                if trade.average_exit_price is not None and trade.quantity_closed > Decimal("0")
            ]
        )

        realized_pnl_values = [trade.realized_pnl for trade in position_trades if trade.realized_pnl is not None]
        realized_pnl = sum_decimals(realized_pnl_values) if realized_pnl_values else None

        order_ids = sorted(
            set(
                [order.order_id for order in position_orders]
                + [order_id for trade in position_trades for order_id in trade.opening_order_ids]
                + [order_id for trade in position_trades for order_id in trade.closing_order_ids]
            )
        )
        execution_event_ids = sorted(
            set(
                [event.event_id for event in position_events]
                + [event_id for trade in position_trades for event_id in trade.execution_event_ids]
            )
        )
        trade_ids = sorted([trade.trade_id for trade in position_trades])

        positions.append(
            Position.model_validate(
                {
                    "position_id": current_position_id,
                    "strategy_id": next(iter(strategy_ids)),
                    "symbol": next(iter(symbols)),
                    "direction": next(iter(directions)),
                    "status": status,
                    "opened_at": opened_at,
                    "closed_at": max(closed_at_candidates) if status == "closed" and closed_at_candidates else None,
                    "quantity_opened": quantity_opened,
                    "quantity_closed": quantity_closed,
                    "net_quantity": net_quantity,
                    "average_entry_price": average_entry_price,
                    "average_exit_price": average_exit_price,
                    "realized_pnl": realized_pnl if status == "closed" else None,
                    "order_ids": order_ids,
                    "execution_event_ids": execution_event_ids,
                    "trade_ids": trade_ids,
                }
            )
        )

    return sorted(
        positions,
        key=lambda item: (
            item.opened_at,
            item.position_id,
        ),
    )


def build_bounded_paper_simulation_state(
    *,
    canonical_execution_repo: Any,
) -> BoundedPaperSimulationState:
    orders = canonical_execution_repo.list_orders(limit=1_000_000, offset=0)
    execution_events = canonical_execution_repo.list_execution_events(limit=1_000_000, offset=0)
    trades = canonical_execution_repo.list_trades(limit=1_000_000, offset=0)
    positions = build_trading_core_positions(
        canonical_execution_repo=canonical_execution_repo,
        trades=list(trades),
        orders=list(orders),
        events=list(execution_events),
    )
    account = build_paper_account_state(
        paper_trades=list(trades),
        paper_positions=positions,
    )
    portfolio_positions = build_portfolio_positions_from_trades(trades=trades)
    mismatches = build_paper_reconciliation_mismatches(
        orders=list(orders),
        execution_events=list(execution_events),
        trades=list(trades),
        positions=positions,
        account=account,
    )

    validate_bounded_paper_simulation_state(
        orders=orders,
        execution_events=execution_events,
        trades=trades,
        positions=positions,
        portfolio_positions=portfolio_positions,
    )

    return BoundedPaperSimulationState(
        orders=tuple(orders),
        execution_events=tuple(execution_events),
        trades=tuple(trades),
        positions=tuple(positions),
        account=account,
        portfolio_positions=tuple(portfolio_positions),
        reconciliation_mismatches=tuple(mismatches),
    )
