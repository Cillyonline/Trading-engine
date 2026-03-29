"""Read-only portfolio position state for control-plane inspection.

The derived state is intentionally bounded to non-live simulation artifacts and
must not be interpreted as a live portfolio risk model.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol

from cilly_trading.models import Trade

DEFAULT_PORTFOLIO_POSITIONS_ENV = "CILLY_PORTFOLIO_POSITIONS"


@dataclass(frozen=True)
class PortfolioPosition:
    """Deterministic position model exposed through the control plane."""

    strategy_id: str
    symbol: str
    size: float
    average_price: float
    unrealized_pnl: float


@dataclass(frozen=True)
class PortfolioState:
    """Read-only portfolio state containing current positions."""

    positions: tuple[PortfolioPosition, ...]


class PortfolioSimulationStateRepository(Protocol):
    """Bounded read-only repository contract for simulation-derived portfolio state."""

    def list_trades(
        self,
        *,
        strategy_id: str | None = None,
        symbol: str | None = None,
        position_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Trade]: ...


@dataclass(frozen=True)
class _AggregatedPortfolioPosition:
    strategy_id: str
    symbol: str
    size: Decimal
    weighted_notional: Decimal
    unrealized_pnl: Decimal


def load_portfolio_state_from_simulation_repository(
    *,
    repository: PortfolioSimulationStateRepository,
) -> PortfolioState:
    """Derive deterministic bounded inspection state from simulation artifacts."""

    trades = repository.list_trades(limit=1_000_000, offset=0)
    if not trades:
        return PortfolioState(positions=tuple())

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

    positions: list[PortfolioPosition] = []
    for aggregate in aggregates.values():
        if aggregate.size <= Decimal("0"):
            continue
        average_price = aggregate.weighted_notional / aggregate.size
        positions.append(
            PortfolioPosition(
                strategy_id=aggregate.strategy_id,
                symbol=aggregate.symbol,
                size=float(aggregate.size),
                average_price=float(average_price),
                unrealized_pnl=float(aggregate.unrealized_pnl),
            )
        )

    ordered_positions = tuple(
        sorted(
            positions,
            key=lambda item: (
                item.symbol,
                item.strategy_id,
                item.size,
                item.average_price,
                item.unrealized_pnl,
            ),
        )
    )
    return PortfolioState(positions=ordered_positions)


def load_portfolio_state_from_env(
    *,
    env_var: str = DEFAULT_PORTFOLIO_POSITIONS_ENV,
    environ: dict[str, str] | None = None,
) -> PortfolioState:
    """Load deterministic portfolio positions from a JSON environment value."""

    source = environ if environ is not None else os.environ
    raw_payload = source.get(env_var)
    if not raw_payload:
        return PortfolioState(positions=tuple())

    payload = json.loads(raw_payload)
    if not isinstance(payload, list):
        return PortfolioState(positions=tuple())

    positions = []
    for item in payload:
        position = _parse_position(item)
        if position is None:
            continue
        positions.append(position)

    ordered_positions = tuple(
        sorted(
            positions,
            key=lambda item: (
                item.symbol,
                item.strategy_id,
                item.size,
                item.average_price,
                item.unrealized_pnl,
            ),
        )
    )
    return PortfolioState(positions=ordered_positions)


def _parse_position(item: Any) -> PortfolioPosition | None:
    if not isinstance(item, dict):
        return None

    try:
        strategy_id = str(item["strategy_id"])
        symbol = str(item["symbol"])
        size = float(item["size"])
        average_price = float(item["average_price"])
        unrealized_pnl = float(item["unrealized_pnl"])
    except (KeyError, TypeError, ValueError):
        return None

    if not strategy_id or not symbol:
        return None
    if size < 0.0:
        return None
    if average_price < 0.0:
        return None

    return PortfolioPosition(
        strategy_id=strategy_id,
        symbol=symbol,
        size=size,
        average_price=average_price,
        unrealized_pnl=unrealized_pnl,
    )
