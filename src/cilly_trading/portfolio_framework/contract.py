"""Portfolio framework contracts for Issue #496."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PortfolioPosition:
    """Represents a single portfolio position.

    Attributes:
        strategy_id: Strategy identifier that owns the position.
        symbol: Instrument symbol.
        quantity: Signed quantity for the position.
        mark_price: Current mark price used for notional calculations.
    """

    strategy_id: str
    symbol: str
    quantity: float
    mark_price: float


@dataclass(frozen=True)
class PortfolioState:
    """Immutable portfolio state input for aggregation functions.

    Attributes:
        account_equity: Current account equity.
        positions: Tuple of current portfolio positions.
    """

    account_equity: float
    positions: tuple[PortfolioPosition, ...]
