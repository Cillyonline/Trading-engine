"""Deterministic drawdown shutdown guard utilities."""

from __future__ import annotations

import logging

from cilly_trading.portfolio import PortfolioState

_logger = logging.getLogger(__name__)


_DRAWDOWN_THRESHOLD_KEY = "execution.drawdown.max_pct"


def configured_drawdown_threshold(*, config: dict[str, object] | None) -> float | None:
    """Return configured drawdown threshold ratio in [0.0, 1.0]."""
    if config is None:
        return None

    value = config.get(_DRAWDOWN_THRESHOLD_KEY)
    if not isinstance(value, int | float):
        return None

    threshold = float(value)
    if threshold < 0.0 or threshold > 1.0:
        return None

    return threshold


def is_drawdown_threshold_exceeded(
    *,
    portfolio_state: PortfolioState,
    max_drawdown_pct: float,
) -> bool:
    """Return True when portfolio drawdown strictly exceeds max threshold."""
    return portfolio_state.drawdown() > max_drawdown_pct


def should_block_execution_for_drawdown(
    *,
    portfolio_state: PortfolioState,
    config: dict[str, object] | None = None,
) -> bool:
    """Return deterministic execution block state for drawdown guard.

    WARNING: When this guard triggers, open positions are NOT automatically
    liquidated. Manual intervention is required to close existing exposure.
    """
    threshold = configured_drawdown_threshold(config=config)
    if threshold is None:
        return False

    blocked = is_drawdown_threshold_exceeded(
        portfolio_state=portfolio_state,
        max_drawdown_pct=threshold,
    )
    if blocked:
        _logger.critical(
            "DRAWDOWN_GUARD_TRIGGERED: current_drawdown=%.4f limit=%.4f "
            "open_positions_NOT_liquidated=true manual_intervention_required=true",
            portfolio_state.drawdown(),
            threshold,
        )
    return blocked
