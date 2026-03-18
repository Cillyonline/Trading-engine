"""Contract tests for portfolio framework."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from cilly_trading.portfolio_framework.contract import PortfolioPosition, PortfolioState


def test_portfolio_state_is_immutable() -> None:
    """PortfolioState must be an immutable dataclass."""
    state = PortfolioState(
        account_equity=1000.0,
        positions=(
            PortfolioPosition(
                strategy_id="strategy-a",
                symbol="BTCUSDT",
                quantity=1.0,
                mark_price=25000.0,
            ),
        ),
    )

    with pytest.raises(FrozenInstanceError):
        state.account_equity = 1200.0  # type: ignore[misc]
