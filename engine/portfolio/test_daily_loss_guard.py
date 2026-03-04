"""Deterministic tests for daily loss shutdown guard (Issue #522)."""

from __future__ import annotations

from engine.compliance.daily_loss_guard import (
    configured_daily_loss_limit,
    should_block_execution_for_daily_loss,
)
from engine.portfolio.state import PortfolioState, calculate_daily_pnl


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
