"""Deterministic daily loss shutdown guard utilities."""

from __future__ import annotations

import logging

from cilly_trading.portfolio import PortfolioState

_logger = logging.getLogger(__name__)


_DAILY_LOSS_LIMIT_KEY = "execution.daily_loss.max_abs"


def configured_daily_loss_limit(*, config: dict[str, object] | None) -> float | None:
    """Return configured max daily loss in absolute portfolio currency."""
    if config is None:
        return None

    value = config.get(_DAILY_LOSS_LIMIT_KEY)
    if not isinstance(value, int | float):
        return None

    limit = float(value)
    if limit < 0.0:
        return None

    return limit


def is_daily_loss_limit_breached(
    *,
    portfolio_state: PortfolioState,
    max_daily_loss: float,
) -> bool:
    """Return True when daily loss strictly exceeds max allowed loss."""
    return portfolio_state.daily_loss() > max_daily_loss


def should_block_execution_for_daily_loss(
    *,
    portfolio_state: PortfolioState,
    config: dict[str, object] | None = None,
) -> bool:
    """Return deterministic execution block state for daily loss guard.

    WARNING: When this guard triggers, open positions are NOT automatically
    liquidated. Manual intervention is required to close existing exposure.
    """
    daily_loss_limit = configured_daily_loss_limit(config=config)
    if daily_loss_limit is None:
        return False

    blocked = is_daily_loss_limit_breached(
        portfolio_state=portfolio_state,
        max_daily_loss=daily_loss_limit,
    )
    if blocked:
        _logger.critical(
            "DAILY_LOSS_GUARD_TRIGGERED: current_daily_loss=%.4f limit=%.4f "
            "open_positions_NOT_liquidated=true manual_intervention_required=true",
            portfolio_state.daily_loss(),
            daily_loss_limit,
        )
    return blocked
