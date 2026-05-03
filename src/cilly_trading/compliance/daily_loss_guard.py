"""Deterministic daily loss shutdown guard utilities."""

from __future__ import annotations

import logging
from enum import Enum

from cilly_trading.portfolio import PortfolioState

_logger = logging.getLogger(__name__)


_DAILY_LOSS_LIMIT_KEY = "execution.daily_loss.max_abs"
_BREACH_ACTION_KEY = "execution.daily_loss.breach_action"


class DailyLossBreachAction(str, Enum):
    """Configurable response when the daily loss limit is breached.

    log_only:
        Log a critical message and block new orders. No other action.
        Preserves the previous behavior exactly for backward compatibility.

    activate_kill_switch:
        Activates the kill switch (sets execution.kill_switch.active=True in
        the config dict) and blocks new orders. This is the default for new
        configurations. Ensures no orders are processed even if the log is
        missed.

    require_acknowledgment:
        Sets a persistent awaiting_acknowledgment flag and blocks all new
        orders until the operator explicitly calls acknowledge_daily_loss_breach()
        (or the POST /compliance/daily-loss/acknowledge API endpoint). Suitable
        for semi-automated or unattended paper trading contexts.
    """

    log_only = "log_only"
    activate_kill_switch = "activate_kill_switch"
    require_acknowledgment = "require_acknowledgment"


class DailyLossBreachState:
    """Mutable state for the require_acknowledgment breach-action policy."""

    def __init__(self) -> None:
        self.awaiting_acknowledgment: bool = False


# Module-level singleton used when no explicit breach_state is provided.
_DEFAULT_BREACH_STATE = DailyLossBreachState()


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


def configured_breach_action(
    *, config: dict[str, object] | None
) -> DailyLossBreachAction:
    """Return the configured breach-action policy.

    Defaults to activate_kill_switch when not configured or unrecognised.
    """
    if config is None:
        return DailyLossBreachAction.activate_kill_switch

    raw = config.get(_BREACH_ACTION_KEY)
    if raw == DailyLossBreachAction.log_only:
        return DailyLossBreachAction.log_only
    if raw == DailyLossBreachAction.require_acknowledgment:
        return DailyLossBreachAction.require_acknowledgment
    return DailyLossBreachAction.activate_kill_switch


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
    breach_state: DailyLossBreachState | None = None,
) -> bool:
    """Return deterministic execution block state for daily loss guard.

    Executes the configured breach-action policy on first breach:
    - log_only: log and block (backward-compatible default).
    - activate_kill_switch: set execution.kill_switch.active=True in config.
    - require_acknowledgment: set breach_state.awaiting_acknowledgment=True;
      block until acknowledge_daily_loss_breach() is called.

    WARNING: When this guard triggers, open positions are NOT automatically
    liquidated. Manual intervention is required to close existing exposure.
    """
    if breach_state is None:
        breach_state = _DEFAULT_BREACH_STATE

    # If we are already waiting for an acknowledgment, keep blocking.
    if breach_state.awaiting_acknowledgment:
        return True

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

        action = configured_breach_action(config=config)

        if action == DailyLossBreachAction.activate_kill_switch:
            if config is not None:
                config["execution.kill_switch.active"] = True
            _logger.critical(
                "DAILY_LOSS_GUARD: kill_switch activated breach_action=activate_kill_switch"
            )

        elif action == DailyLossBreachAction.require_acknowledgment:
            breach_state.awaiting_acknowledgment = True
            _logger.critical(
                "DAILY_LOSS_GUARD: awaiting_acknowledgment=true "
                "breach_action=require_acknowledgment "
                "resume_via=POST /compliance/daily-loss/acknowledge"
            )

        # log_only: no additional action beyond the critical log above.

    return blocked


def acknowledge_daily_loss_breach(
    *,
    breach_state: DailyLossBreachState | None = None,
) -> None:
    """Clear the awaiting_acknowledgment flag set by require_acknowledgment policy.

    After this call, execution resumes on the next guard check. If the portfolio
    still exceeds the loss limit, the guard will trigger again immediately.
    """
    if breach_state is None:
        breach_state = _DEFAULT_BREACH_STATE
    breach_state.awaiting_acknowledgment = False
    _logger.info(
        "DAILY_LOSS_GUARD: acknowledgment received awaiting_acknowledgment=false "
        "execution_resumed=true"
    )
