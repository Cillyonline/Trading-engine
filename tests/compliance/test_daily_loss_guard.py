"""Deterministic tests for daily loss shutdown guard (Issue #522, #1092)."""

from __future__ import annotations

from cilly_trading.compliance.daily_loss_guard import (
    DailyLossBreachAction,
    DailyLossBreachState,
    acknowledge_daily_loss_breach,
    configured_breach_action,
    configured_daily_loss_limit,
    should_block_execution_for_daily_loss,
)
from cilly_trading.portfolio.state import PortfolioState, calculate_daily_pnl


def test_calculate_daily_pnl_deterministic_scenario() -> None:
    assert calculate_daily_pnl(start_of_day_equity=100_000.0, current_equity=98_500.0) == -1_500.0
    assert calculate_daily_pnl(start_of_day_equity=100_000.0, current_equity=101_250.0) == 1_250.0


def test_guard_blocks_execution_when_daily_loss_limit_exceeded() -> None:
    state = PortfolioState(
        peak_equity=110_000.0,
        start_of_day_equity=100_000.0,
        current_equity=98_900.0,
    )

    blocked = should_block_execution_for_daily_loss(
        portfolio_state=state,
        config={"execution.daily_loss.max_abs": 1_000.0},
    )

    assert blocked is True


def test_guard_does_not_block_when_daily_loss_limit_not_exceeded() -> None:
    state = PortfolioState(
        peak_equity=110_000.0,
        start_of_day_equity=100_000.0,
        current_equity=99_000.0,
    )

    blocked = should_block_execution_for_daily_loss(
        portfolio_state=state,
        config={"execution.daily_loss.max_abs": 1_000.0},
    )

    assert blocked is False


def test_invalid_or_missing_daily_loss_limit_does_not_activate_guard() -> None:
    state = PortfolioState(
        peak_equity=110_000.0,
        start_of_day_equity=100_000.0,
        current_equity=98_000.0,
    )

    assert configured_daily_loss_limit(config=None) is None
    assert configured_daily_loss_limit(config={}) is None
    assert configured_daily_loss_limit(config={"execution.daily_loss.max_abs": "1000"}) is None
    assert configured_daily_loss_limit(config={"execution.daily_loss.max_abs": -1.0}) is None
    assert should_block_execution_for_daily_loss(portfolio_state=state, config=None) is False


def test_missing_start_of_day_equity_does_not_trigger_block() -> None:
    state = PortfolioState(peak_equity=110_000.0, current_equity=95_000.0)

    blocked = should_block_execution_for_daily_loss(
        portfolio_state=state,
        config={"execution.daily_loss.max_abs": 500.0},
    )

    assert blocked is False


# ── Breach-action policy tests (Issue #1092) ──────────────────────────────────


def _breached_state() -> PortfolioState:
    return PortfolioState(
        peak_equity=110_000.0,
        start_of_day_equity=100_000.0,
        current_equity=98_900.0,  # loss = 1100, limit = 1000
    )


def _safe_state() -> PortfolioState:
    return PortfolioState(
        peak_equity=110_000.0,
        start_of_day_equity=100_000.0,
        current_equity=99_100.0,  # loss = 900, limit = 1000
    )


class TestConfiguredBreachAction:
    def test_defaults_to_activate_kill_switch_when_key_absent(self) -> None:
        assert configured_breach_action(config={}) == DailyLossBreachAction.activate_kill_switch

    def test_defaults_to_activate_kill_switch_when_config_is_none(self) -> None:
        assert configured_breach_action(config=None) == DailyLossBreachAction.activate_kill_switch

    def test_log_only_policy_recognised(self) -> None:
        cfg = {"execution.daily_loss.breach_action": "log_only"}
        assert configured_breach_action(config=cfg) == DailyLossBreachAction.log_only

    def test_activate_kill_switch_policy_recognised(self) -> None:
        cfg = {"execution.daily_loss.breach_action": "activate_kill_switch"}
        assert configured_breach_action(config=cfg) == DailyLossBreachAction.activate_kill_switch

    def test_require_acknowledgment_policy_recognised(self) -> None:
        cfg = {"execution.daily_loss.breach_action": "require_acknowledgment"}
        assert configured_breach_action(config=cfg) == DailyLossBreachAction.require_acknowledgment

    def test_unknown_value_falls_back_to_activate_kill_switch(self) -> None:
        cfg = {"execution.daily_loss.breach_action": "unknown_policy"}
        assert configured_breach_action(config=cfg) == DailyLossBreachAction.activate_kill_switch


class TestLogOnlyPolicy:
    def test_blocks_execution_on_breach(self) -> None:
        cfg = {
            "execution.daily_loss.max_abs": 1_000.0,
            "execution.daily_loss.breach_action": "log_only",
        }
        bs = DailyLossBreachState()
        assert should_block_execution_for_daily_loss(
            portfolio_state=_breached_state(), config=cfg, breach_state=bs
        ) is True

    def test_does_not_activate_kill_switch(self) -> None:
        cfg = {
            "execution.daily_loss.max_abs": 1_000.0,
            "execution.daily_loss.breach_action": "log_only",
        }
        bs = DailyLossBreachState()
        should_block_execution_for_daily_loss(
            portfolio_state=_breached_state(), config=cfg, breach_state=bs
        )
        assert cfg.get("execution.kill_switch.active") is not True

    def test_does_not_set_awaiting_acknowledgment(self) -> None:
        cfg = {
            "execution.daily_loss.max_abs": 1_000.0,
            "execution.daily_loss.breach_action": "log_only",
        }
        bs = DailyLossBreachState()
        should_block_execution_for_daily_loss(
            portfolio_state=_breached_state(), config=cfg, breach_state=bs
        )
        assert bs.awaiting_acknowledgment is False

    def test_does_not_block_when_limit_not_exceeded(self) -> None:
        cfg = {
            "execution.daily_loss.max_abs": 1_000.0,
            "execution.daily_loss.breach_action": "log_only",
        }
        bs = DailyLossBreachState()
        assert should_block_execution_for_daily_loss(
            portfolio_state=_safe_state(), config=cfg, breach_state=bs
        ) is False


class TestActivateKillSwitchPolicy:
    def test_blocks_execution_on_breach(self) -> None:
        cfg = {
            "execution.daily_loss.max_abs": 1_000.0,
            "execution.daily_loss.breach_action": "activate_kill_switch",
        }
        bs = DailyLossBreachState()
        assert should_block_execution_for_daily_loss(
            portfolio_state=_breached_state(), config=cfg, breach_state=bs
        ) is True

    def test_activates_kill_switch_in_config_on_breach(self) -> None:
        cfg = {
            "execution.daily_loss.max_abs": 1_000.0,
            "execution.daily_loss.breach_action": "activate_kill_switch",
        }
        bs = DailyLossBreachState()
        should_block_execution_for_daily_loss(
            portfolio_state=_breached_state(), config=cfg, breach_state=bs
        )
        assert cfg.get("execution.kill_switch.active") is True

    def test_kill_switch_not_activated_when_not_breached(self) -> None:
        cfg = {
            "execution.daily_loss.max_abs": 1_000.0,
            "execution.daily_loss.breach_action": "activate_kill_switch",
        }
        bs = DailyLossBreachState()
        should_block_execution_for_daily_loss(
            portfolio_state=_safe_state(), config=cfg, breach_state=bs
        )
        assert cfg.get("execution.kill_switch.active") is not True

    def test_is_default_when_breach_action_key_absent(self) -> None:
        cfg = {"execution.daily_loss.max_abs": 1_000.0}
        bs = DailyLossBreachState()
        should_block_execution_for_daily_loss(
            portfolio_state=_breached_state(), config=cfg, breach_state=bs
        )
        assert cfg.get("execution.kill_switch.active") is True


class TestRequireAcknowledgmentPolicy:
    def test_blocks_execution_on_breach(self) -> None:
        cfg = {
            "execution.daily_loss.max_abs": 1_000.0,
            "execution.daily_loss.breach_action": "require_acknowledgment",
        }
        bs = DailyLossBreachState()
        assert should_block_execution_for_daily_loss(
            portfolio_state=_breached_state(), config=cfg, breach_state=bs
        ) is True

    def test_sets_awaiting_acknowledgment_flag(self) -> None:
        cfg = {
            "execution.daily_loss.max_abs": 1_000.0,
            "execution.daily_loss.breach_action": "require_acknowledgment",
        }
        bs = DailyLossBreachState()
        should_block_execution_for_daily_loss(
            portfolio_state=_breached_state(), config=cfg, breach_state=bs
        )
        assert bs.awaiting_acknowledgment is True

    def test_blocks_even_after_portfolio_recovers_until_acknowledged(self) -> None:
        cfg = {
            "execution.daily_loss.max_abs": 1_000.0,
            "execution.daily_loss.breach_action": "require_acknowledgment",
        }
        bs = DailyLossBreachState()
        # First call — breach triggers flag.
        should_block_execution_for_daily_loss(
            portfolio_state=_breached_state(), config=cfg, breach_state=bs
        )
        # Portfolio recovers, but flag still set — still blocked.
        still_blocked = should_block_execution_for_daily_loss(
            portfolio_state=_safe_state(), config=cfg, breach_state=bs
        )
        assert still_blocked is True

    def test_resumes_after_acknowledgment(self) -> None:
        cfg = {
            "execution.daily_loss.max_abs": 1_000.0,
            "execution.daily_loss.breach_action": "require_acknowledgment",
        }
        bs = DailyLossBreachState()
        should_block_execution_for_daily_loss(
            portfolio_state=_breached_state(), config=cfg, breach_state=bs
        )
        assert bs.awaiting_acknowledgment is True
        acknowledge_daily_loss_breach(breach_state=bs)
        assert bs.awaiting_acknowledgment is False
        # After acknowledgment, a safe portfolio no longer blocks.
        unblocked = should_block_execution_for_daily_loss(
            portfolio_state=_safe_state(), config=cfg, breach_state=bs
        )
        assert unblocked is False

    def test_re_triggers_immediately_if_still_breached_after_acknowledgment(self) -> None:
        cfg = {
            "execution.daily_loss.max_abs": 1_000.0,
            "execution.daily_loss.breach_action": "require_acknowledgment",
        }
        bs = DailyLossBreachState()
        should_block_execution_for_daily_loss(
            portfolio_state=_breached_state(), config=cfg, breach_state=bs
        )
        acknowledge_daily_loss_breach(breach_state=bs)
        # Portfolio still breached → guard triggers again immediately.
        blocked_again = should_block_execution_for_daily_loss(
            portfolio_state=_breached_state(), config=cfg, breach_state=bs
        )
        assert blocked_again is True
        assert bs.awaiting_acknowledgment is True

    def test_does_not_activate_kill_switch(self) -> None:
        cfg = {
            "execution.daily_loss.max_abs": 1_000.0,
            "execution.daily_loss.breach_action": "require_acknowledgment",
        }
        bs = DailyLossBreachState()
        should_block_execution_for_daily_loss(
            portfolio_state=_breached_state(), config=cfg, breach_state=bs
        )
        assert cfg.get("execution.kill_switch.active") is not True
