"""Paper inspection service — all state derived from canonical execution repository.

State authority: SqliteCanonicalExecutionRepository is the sole source of truth.
See ``cilly_trading.portfolio.paper_state_authority`` for the full contract.
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Literal, Optional, Sequence

from fastapi import HTTPException
from pydantic import ValidationError

from cilly_trading.engine.decision_card_contract import (
    BoundedDecisionToPaperUsefulnessMatchReference,
    BacktestRealismCalibrationStatus,
    evaluate_bounded_confidence_calibration_audit,
    evaluate_bounded_decision_to_paper_usefulness_audit,
    evaluate_bounded_signal_quality_stability_audit,
    evaluate_bounded_strategy_score_calibration_audit,
)
from cilly_trading.models import ExecutionEvent, Order, Position, Trade


BOUNDED_SIGNAL_PORTFOLIO_PAPER_RECONCILIATION_CONTRACT_ID = (
    "signal_portfolio_paper_reconciliation_trace.paper_audit.v1"
)
BOUNDED_SIGNAL_PORTFOLIO_PAPER_RECONCILIATION_CONTRACT_VERSION = "1.0.0"
BOUNDED_SIGNAL_PORTFOLIO_PAPER_RECONCILIATION_INTERPRETATION_LIMIT = (
    "Signal-to-portfolio-to-paper reconciliation audit is bounded to non-live deterministic "
    "operator inspection. It does not imply auto-trading, broker execution, live-trading "
    "readiness, profitability forecasting, trader validation, or operational readiness."
)


def paginate_items(items: list[object], *, limit: int, offset: int) -> tuple[list[object], int]:
    total = len(items)
    return items[offset : offset + limit], total


def resolve_paper_starting_cash() -> Decimal:
    raw_value = os.getenv("CILLY_PAPER_ACCOUNT_STARTING_CASH", "100000")
    try:
        value = Decimal(raw_value)
    except (InvalidOperation, ValueError) as exc:
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
    """Immutable snapshot of paper state derived from the canonical execution repository.

    Every field is computed deterministically from ``core_orders``,
    ``core_execution_events``, and ``core_trades``.  No alternative state
    source is used.  See ``cilly_trading.portfolio.paper_state_authority``.
    """

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


def resolve_runtime_canonical_execution_repo() -> Any | None:
    try:
        import api.main as api_main
    except ImportError:
        return None
    return getattr(api_main, "canonical_execution_repo", None)


def _safe_get_trade(repo: Any, trade_id: str) -> Any | None:
    try:
        return repo.get_trade(trade_id)
    except (sqlite3.Error, ValidationError, KeyError, ValueError):
        return None


def _parse_iso_datetime(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00") if value.endswith("Z") else value
    return datetime.fromisoformat(normalized)


def _format_decimal(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return str(value)


def _build_paper_trade_outcome_payload(
    *,
    trade: Trade,
    expected_symbol: str,
    expected_strategy_id: str,
    decision_generated_at_utc: str,
) -> tuple[Literal["matched", "open", "invalid"], dict[str, Any]]:
    try:
        decision_at = _parse_iso_datetime(decision_generated_at_utc)
        opened_at = _parse_iso_datetime(trade.opened_at)
    except ValueError:
        return (
            "invalid",
            {
                "trade_id": trade.trade_id,
                "position_id": trade.position_id,
                "symbol": trade.symbol,
                "strategy_id": trade.strategy_id,
                "trade_status": trade.status,
                "opened_at_utc": trade.opened_at,
                "closed_at_utc": trade.closed_at,
                "outcome_direction": "invalid",
                "realized_pnl": _format_decimal(trade.realized_pnl),
                "unrealized_pnl": _format_decimal(trade.unrealized_pnl),
                "outcome_summary": (
                    "Matched paper trade could not satisfy deterministic timestamp parsing for bounded "
                    "decision-to-paper usefulness review."
                ),
            },
        )

    if trade.symbol != expected_symbol or trade.strategy_id != expected_strategy_id or opened_at < decision_at:
        return (
            "invalid",
            {
                "trade_id": trade.trade_id,
                "position_id": trade.position_id,
                "symbol": trade.symbol,
                "strategy_id": trade.strategy_id,
                "trade_status": trade.status,
                "opened_at_utc": trade.opened_at,
                "closed_at_utc": trade.closed_at,
                "outcome_direction": "invalid",
                "realized_pnl": _format_decimal(trade.realized_pnl),
                "unrealized_pnl": _format_decimal(trade.unrealized_pnl),
                "outcome_summary": (
                    "Matched paper trade violates the explicit symbol, strategy, or subsequent-timing "
                    "comparison contract."
                ),
            },
        )

    if trade.status == "open":
        return (
            "open",
            {
                "trade_id": trade.trade_id,
                "position_id": trade.position_id,
                "symbol": trade.symbol,
                "strategy_id": trade.strategy_id,
                "trade_status": trade.status,
                "opened_at_utc": trade.opened_at,
                "closed_at_utc": trade.closed_at,
                "outcome_direction": "open",
                "realized_pnl": _format_decimal(trade.realized_pnl),
                "unrealized_pnl": _format_decimal(trade.unrealized_pnl),
                "outcome_summary": (
                    "Matched paper trade remains open, so the bounded non-live outcome is not yet closed."
                ),
            },
        )

    realized_pnl = trade.realized_pnl or Decimal("0")
    if realized_pnl > Decimal("0"):
        outcome_direction = "favorable"
    elif realized_pnl < Decimal("0"):
        outcome_direction = "adverse"
    else:
        outcome_direction = "flat"
    return (
        "matched",
        {
            "trade_id": trade.trade_id,
            "position_id": trade.position_id,
            "symbol": trade.symbol,
            "strategy_id": trade.strategy_id,
            "trade_status": trade.status,
            "opened_at_utc": trade.opened_at,
            "closed_at_utc": trade.closed_at,
            "outcome_direction": outcome_direction,
            "realized_pnl": _format_decimal(trade.realized_pnl),
            "unrealized_pnl": _format_decimal(trade.unrealized_pnl),
            "outcome_summary": (
                "Matched paper trade closed and produced a deterministic bounded paper outcome for "
                "decision-to-paper usefulness review."
            ),
        },
    )


def build_bounded_decision_to_paper_usefulness_audit(
    *,
    canonical_execution_repo: Any | None,
    decision_card_id: str,
    generated_at_utc: str,
    symbol: str,
    strategy_id: str,
    action: str,
    qualification_state: str,
    match_reference: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(match_reference, dict):
        return None

    try:
        normalized_match_reference = BoundedDecisionToPaperUsefulnessMatchReference.model_validate(
            match_reference
        )
    except ValidationError:
        return None

    trade: Trade | None = (
        _safe_get_trade(canonical_execution_repo, normalized_match_reference.paper_trade_id)
        if canonical_execution_repo is not None
        else None
    )

    match_status: Literal["matched", "open", "missing", "invalid"] = "missing"
    matched_outcome: dict[str, Any] | None = None
    if trade is not None:
        match_status, matched_outcome = _build_paper_trade_outcome_payload(
            trade=trade,
            expected_symbol=symbol,
            expected_strategy_id=strategy_id,
            decision_generated_at_utc=generated_at_utc,
        )

    audit = evaluate_bounded_decision_to_paper_usefulness_audit(
        covered_case_id=decision_card_id,
        action=action,
        qualification_state=qualification_state,
        match_status=match_status,
        match_reference=normalized_match_reference.model_dump(mode="python"),
        matched_outcome=matched_outcome,
    )
    return audit.model_dump(mode="python")


def _deterministic_reference_id(*parts: str | None) -> str:
    normalized_parts = [part.strip() for part in parts if isinstance(part, str) and part.strip()]
    return ":".join(normalized_parts) if normalized_parts else "missing"


def _paper_outcome_state_from_match_status(
    match_status: Literal["matched", "open", "missing", "invalid"],
) -> Literal["closed", "open", "missing", "invalid"]:
    if match_status == "matched":
        return "closed"
    if match_status == "open":
        return "open"
    return match_status


def _related_reconciliation_mismatches(
    *,
    mismatches: Sequence[dict[str, Optional[str]]],
    order_ids: Sequence[str],
    execution_event_ids: Sequence[str],
    trade_id: str | None,
    position_id: str | None,
) -> list[dict[str, Optional[str]]]:
    related_ids = {item for item in [*order_ids, *execution_event_ids, trade_id, position_id] if item}
    if not related_ids:
        return []
    return [
        mismatch
        for mismatch in mismatches
        if mismatch.get("entity_id") in related_ids
        or any((identifier in (mismatch.get("message") or "")) for identifier in related_ids)
    ]


def build_bounded_signal_portfolio_paper_reconciliation_audit(
    *,
    canonical_execution_repo: Any | None,
    decision_card_id: str,
    generated_at_utc: str,
    symbol: str,
    strategy_id: str,
    action: str,
    qualification_state: str,
    analysis_run_id: str | None,
    signal_id: str | None,
    match_reference: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build an explicit bounded signal -> portfolio -> paper -> reconciliation audit.

    This is an inspection payload only. It derives every resolved paper/order/
    reconciliation field from the canonical execution repository and uses
    deterministic fallback IDs when upstream artifacts do not carry explicit IDs.
    """

    paper_linkage_status, paper_trade_id = resolve_bounded_paper_linkage_status(
        canonical_execution_repo=canonical_execution_repo,
        generated_at_utc=generated_at_utc,
        symbol=symbol,
        strategy_id=strategy_id,
        match_reference=match_reference,
    )
    outcome_state = _paper_outcome_state_from_match_status(paper_linkage_status)

    resolved_signal_id = (
        signal_id
        if isinstance(signal_id, str) and signal_id.strip()
        else _deterministic_reference_id("signal", analysis_run_id, symbol, strategy_id, generated_at_utc)
    )
    portfolio_impact_id = _deterministic_reference_id(
        "portfolio-impact",
        decision_card_id,
        strategy_id,
        symbol,
    )

    trade: Trade | None = (
        _safe_get_trade(canonical_execution_repo, paper_trade_id)
        if canonical_execution_repo is not None and paper_trade_id is not None
        else None
    )

    opening_order_ids: list[str] = list(trade.opening_order_ids) if trade is not None else []
    closing_order_ids: list[str] = list(trade.closing_order_ids) if trade is not None else []
    execution_event_ids: list[str] = list(trade.execution_event_ids) if trade is not None else []
    paper_order_id = opening_order_ids[0] if opening_order_ids else None
    position_id = trade.position_id if trade is not None else None

    lifecycle_status: Literal["closed", "open", "missing", "invalid"] = outcome_state
    reconciliation_status: Literal["matched", "open", "missing", "invalid"] = paper_linkage_status
    related_mismatches: list[dict[str, Optional[str]]] = []
    if canonical_execution_repo is not None and trade is not None:
        try:
            state = build_bounded_paper_simulation_state(
                canonical_execution_repo=canonical_execution_repo,
            )
            related_mismatches = _related_reconciliation_mismatches(
                mismatches=state.reconciliation_mismatches,
                order_ids=[*opening_order_ids, *closing_order_ids],
                execution_event_ids=execution_event_ids,
                trade_id=trade.trade_id,
                position_id=trade.position_id,
            )
        except Exception:
            related_mismatches = [
                {
                    "code": "paper_reconciliation_state_unavailable",
                    "message": "canonical paper reconciliation state could not be derived",
                    "entity_type": "trade",
                    "entity_id": trade.trade_id,
                }
            ]
        if related_mismatches:
            reconciliation_status = "invalid"
            lifecycle_status = "invalid"

    portfolio_impact_status: Literal["available", "missing"] = (
        "available" if action in {"entry", "exit"} and qualification_state != "reject" else "missing"
    )

    return {
        "contract_id": BOUNDED_SIGNAL_PORTFOLIO_PAPER_RECONCILIATION_CONTRACT_ID,
        "contract_version": BOUNDED_SIGNAL_PORTFOLIO_PAPER_RECONCILIATION_CONTRACT_VERSION,
        "signal": {
            "signal_id": resolved_signal_id,
            "analysis_run_id": analysis_run_id,
            "symbol": symbol,
            "strategy_id": strategy_id,
            "linkage_status": "matched" if analysis_run_id is not None else "missing",
        },
        "decision_card": {
            "decision_card_id": decision_card_id,
            "generated_at_utc": generated_at_utc,
            "qualification_state": qualification_state,
            "action": action,
            "linkage_status": "matched",
        },
        "portfolio_impact": {
            "portfolio_impact_id": portfolio_impact_id,
            "status": portfolio_impact_status,
            "surface": "GET /portfolio/positions",
            "pre_paper_execution_visible": True,
            "reference": "decision_card_id + strategy_id + symbol",
        },
        "paper_order": {
            "paper_order_id": paper_order_id,
            "opening_order_ids": opening_order_ids,
            "closing_order_ids": closing_order_ids,
            "execution_event_ids": execution_event_ids,
            "lifecycle_status": lifecycle_status,
            "surface": "GET /trading-core/orders + GET /trading-core/execution-events",
        },
        "paper_outcome": {
            "paper_trade_id": paper_trade_id,
            "position_id": position_id,
            "outcome_state": outcome_state,
            "linkage_status": paper_linkage_status,
            "surface": "GET /paper/trades",
        },
        "reconciliation": {
            "status": reconciliation_status,
            "surface": "GET /paper/reconciliation",
            "related_mismatch_count": len(related_mismatches),
            "related_mismatch_codes": [item["code"] for item in related_mismatches],
        },
        "deterministic_reference_chain": [
            resolved_signal_id,
            decision_card_id,
            portfolio_impact_id,
            paper_order_id or "paper_order:missing",
            paper_trade_id or "paper_trade:missing",
            "GET /paper/reconciliation",
        ],
        "classification_vocabulary": {
            "paper_outcome_states": ["missing", "invalid", "open", "closed"],
            "linkage_statuses": ["missing", "invalid", "open", "matched"],
        },
        "interpretation_limit": BOUNDED_SIGNAL_PORTFOLIO_PAPER_RECONCILIATION_INTERPRETATION_LIMIT,
    }


def resolve_bounded_paper_linkage_status(
    *,
    canonical_execution_repo: Any | None,
    generated_at_utc: str,
    symbol: str,
    strategy_id: str,
    match_reference: dict[str, Any] | None,
) -> tuple[Literal["matched", "open", "missing", "invalid"], str | None]:
    """Return the bounded paper linkage status and resolved paper_trade_id.

    The status mirrors the decision-to-paper usefulness contract semantics
    (matched/open/missing/invalid) so the end-to-end traceability chain can
    expose explicit, deterministic linkage status across stages.
    """

    if not isinstance(match_reference, dict):
        return "missing", None

    try:
        normalized = BoundedDecisionToPaperUsefulnessMatchReference.model_validate(
            match_reference
        )
    except ValidationError:
        return "invalid", None

    paper_trade_id = normalized.paper_trade_id
    if canonical_execution_repo is None:
        return "missing", paper_trade_id

    trade = _safe_get_trade(canonical_execution_repo, paper_trade_id)

    if trade is None:
        return "missing", paper_trade_id

    status, _ = _build_paper_trade_outcome_payload(
        trade=trade,
        expected_symbol=symbol,
        expected_strategy_id=strategy_id,
        decision_generated_at_utc=generated_at_utc,
    )
    return status, paper_trade_id


def build_bounded_signal_quality_stability_audit(
    *,
    canonical_execution_repo: Any | None,
    decision_card_id: str,
    generated_at_utc: str,
    symbol: str,
    strategy_id: str,
    signal_quality_score: float | None,
    match_reference: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Build the bounded signal-quality stability audit payload.

    The audit deterministically classifies the covered signal-quality score
    against the matched paper-trade outcome resolved through the existing
    decision-to-paper match contract. Returns ``None`` when no covered
    signal-quality score is available so the audit stays bounded to covered
    evidence only.
    """

    if signal_quality_score is None:
        return None

    normalized_match_reference: BoundedDecisionToPaperUsefulnessMatchReference | None = None
    if isinstance(match_reference, dict):
        try:
            normalized_match_reference = (
                BoundedDecisionToPaperUsefulnessMatchReference.model_validate(match_reference)
            )
        except ValidationError:
            normalized_match_reference = None

    match_status: Literal["matched", "open", "missing", "invalid"] = "missing"
    matched_outcome: dict[str, Any] | None = None
    if normalized_match_reference is not None:
        trade: Trade | None = (
            _safe_get_trade(canonical_execution_repo, normalized_match_reference.paper_trade_id)
            if canonical_execution_repo is not None
            else None
        )
        if trade is not None:
            match_status, matched_outcome = _build_paper_trade_outcome_payload(
                trade=trade,
                expected_symbol=symbol,
                expected_strategy_id=strategy_id,
                decision_generated_at_utc=generated_at_utc,
            )

    audit = evaluate_bounded_signal_quality_stability_audit(
        covered_case_id=decision_card_id,
        signal_quality_score=float(signal_quality_score),
        match_status=match_status,
        match_reference=(
            normalized_match_reference.model_dump(mode="python")
            if normalized_match_reference is not None
            else None
        ),
        matched_outcome=matched_outcome,
    )
    return audit.model_dump(mode="python")


def classify_backtest_realism_calibration_status(
    realism_sensitivity_matrix: dict[str, Any] | None,
) -> tuple[BacktestRealismCalibrationStatus, str]:
    """Classify bounded backtest-realism evidence completeness for confidence calibration."""

    if not isinstance(realism_sensitivity_matrix, dict):
        return (
            "missing",
            "Covered backtest-realism sensitivity evidence is not available, so confidence "
            "calibration cannot move beyond weak bounded interpretation.",
        )

    if realism_sensitivity_matrix.get("deterministic") is not True:
        return (
            "failing",
            "Backtest-realism sensitivity evidence is present but not marked deterministic, so "
            "confidence calibration fails bounded realism review.",
        )

    profiles = realism_sensitivity_matrix.get("profiles")
    if not isinstance(profiles, list):
        return (
            "failing",
            "Backtest-realism sensitivity evidence is malformed because the profile list is missing, "
            "so confidence calibration fails bounded realism review.",
        )

    profiles_by_id = {
        profile.get("profile_id"): profile for profile in profiles if isinstance(profile, dict)
    }
    baseline = profiles_by_id.get("configured_baseline")
    cost_free = profiles_by_id.get("cost_free_reference")
    cost_stress = profiles_by_id.get("bounded_cost_stress")
    if baseline is None or cost_free is None or cost_stress is None:
        return (
            "weak",
            "Backtest-realism sensitivity evidence is present but missing one or more canonical "
            "profiles, so confidence calibration remains weak under bounded realism review.",
        )

    cost_free_summary = cost_free.get("summary")
    baseline_summary = baseline.get("summary")
    cost_stress_summary = cost_stress.get("summary")
    if not all(isinstance(item, dict) for item in (cost_free_summary, baseline_summary, cost_stress_summary)):
        return (
            "failing",
            "Backtest-realism sensitivity evidence is present but profile summaries are malformed, so "
            "confidence calibration fails bounded realism review.",
        )

    if (
        cost_free_summary.get("total_transaction_cost") != 0.0
        or cost_free_summary.get("total_commission") != 0.0
        or cost_free_summary.get("total_slippage_cost") != 0.0
    ):
        return (
            "failing",
            "Backtest-realism sensitivity evidence violates the cost-free reference boundary, so "
            "confidence calibration fails bounded realism review.",
        )

    for key in ("total_transaction_cost", "total_commission", "total_slippage_cost"):
        baseline_value = baseline_summary.get(key)
        stress_value = cost_stress_summary.get(key)
        if not isinstance(baseline_value, (int, float)) or not isinstance(stress_value, (int, float)):
            return (
                "weak",
                "Backtest-realism sensitivity evidence is present but bounded cost fields are "
                "incomplete, so confidence calibration remains weak under realism review.",
            )
        if float(stress_value) < float(baseline_value):
            return (
                "failing",
                "Backtest-realism sensitivity evidence violates bounded cost-stress directionality, "
                "so confidence calibration fails realism review.",
            )

    return (
        "stable",
        "Backtest-realism sensitivity evidence includes deterministic baseline, cost-free, and bounded "
        "cost-stress profiles with canonical directionality, so confidence calibration has stable "
        "bounded realism coverage.",
    )


def build_bounded_confidence_calibration_audit(
    *,
    canonical_execution_repo: Any | None,
    decision_card_id: str,
    generated_at_utc: str,
    symbol: str,
    strategy_id: str,
    confidence_tier: Literal["low", "medium", "high"],
    realism_sensitivity_matrix: dict[str, Any] | None,
    match_reference: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build bounded confidence calibration against realism coverage and paper outcomes."""

    backtest_realism_status, backtest_realism_reason = classify_backtest_realism_calibration_status(
        realism_sensitivity_matrix
    )

    normalized_match_reference: BoundedDecisionToPaperUsefulnessMatchReference | None = None
    if isinstance(match_reference, dict):
        try:
            normalized_match_reference = (
                BoundedDecisionToPaperUsefulnessMatchReference.model_validate(match_reference)
            )
        except ValidationError:
            normalized_match_reference = None

    match_status: Literal["matched", "open", "missing", "invalid"] = "missing"
    matched_outcome: dict[str, Any] | None = None
    if normalized_match_reference is not None:
        trade: Trade | None = (
            _safe_get_trade(canonical_execution_repo, normalized_match_reference.paper_trade_id)
            if canonical_execution_repo is not None
            else None
        )
        if trade is not None:
            match_status, matched_outcome = _build_paper_trade_outcome_payload(
                trade=trade,
                expected_symbol=symbol,
                expected_strategy_id=strategy_id,
                decision_generated_at_utc=generated_at_utc,
            )

    audit = evaluate_bounded_confidence_calibration_audit(
        covered_case_id=decision_card_id,
        confidence_tier=confidence_tier,
        backtest_realism_status=backtest_realism_status,
        backtest_realism_reason=backtest_realism_reason,
        match_status=match_status,
        match_reference=(
            normalized_match_reference.model_dump(mode="python")
            if normalized_match_reference is not None
            else None
        ),
        matched_outcome=matched_outcome,
    )
    return audit.model_dump(mode="python")


def build_bounded_strategy_score_calibration_audit(
    *,
    canonical_execution_repo: Any | None,
    decision_card_id: str,
    generated_at_utc: str,
    symbol: str,
    strategy_id: str,
    aggregate_score: float,
    confidence_tier: Literal["low", "medium", "high"],
    realism_sensitivity_matrix: dict[str, Any] | None,
    match_reference: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Build bounded per-strategy score calibration for governed MVP strategies."""

    normalized_strategy_id = strategy_id.strip().upper()
    if normalized_strategy_id not in {"RSI2", "TURTLE"}:
        return None

    backtest_realism_status, backtest_realism_reason = classify_backtest_realism_calibration_status(
        realism_sensitivity_matrix
    )

    normalized_match_reference: BoundedDecisionToPaperUsefulnessMatchReference | None = None
    if isinstance(match_reference, dict):
        try:
            normalized_match_reference = (
                BoundedDecisionToPaperUsefulnessMatchReference.model_validate(match_reference)
            )
        except ValidationError:
            normalized_match_reference = None

    match_status: Literal["matched", "open", "missing", "invalid"] = "missing"
    matched_outcome: dict[str, Any] | None = None
    if normalized_match_reference is not None:
        trade: Trade | None = (
            _safe_get_trade(canonical_execution_repo, normalized_match_reference.paper_trade_id)
            if canonical_execution_repo is not None
            else None
        )
        if trade is not None:
            match_status, matched_outcome = _build_paper_trade_outcome_payload(
                trade=trade,
                expected_symbol=symbol,
                expected_strategy_id=normalized_strategy_id,
                decision_generated_at_utc=generated_at_utc,
            )

    audit = evaluate_bounded_strategy_score_calibration_audit(
        covered_case_id=decision_card_id,
        strategy_id=normalized_strategy_id,  # type: ignore[arg-type]
        aggregate_score=aggregate_score,
        confidence_tier=confidence_tier,
        backtest_realism_status=backtest_realism_status,
        backtest_realism_reason=backtest_realism_reason,
        match_status=match_status,
        match_reference=(
            normalized_match_reference.model_dump(mode="python")
            if normalized_match_reference is not None
            else None
        ),
        matched_outcome=matched_outcome,
    )
    return audit.model_dump(mode="python")
