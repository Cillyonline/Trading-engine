"""Read-only portfolio position state for control-plane inspection."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

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

    return PortfolioPosition(
        strategy_id=strategy_id,
        symbol=symbol,
        size=size,
        average_price=average_price,
        unrealized_pnl=unrealized_pnl,
    )

