"""Deterministic tests for drawdown shutdown guard (Issue #521)."""

from __future__ import annotations

from cilly_trading.compliance.drawdown_guard import (
    configured_drawdown_threshold,
    should_block_execution_for_drawdown,
)
from cilly_trading.portfolio.state import PortfolioState, calculate_drawdown


def test_calculate_drawdown_deterministic_scenario() -> None:
    assert calculate_drawdown(peak_equity=100_000.0, current_equity=85_000.0) == 0.15
    assert calculate_drawdown(peak_equity=100_000.0, current_equity=100_000.0) == 0.0
    assert calculate_drawdown(peak_equity=0.0, current_equity=10_000.0) == 0.0


def test_guard_blocks_execution_when_threshold_exceeded() -> None:
    state = PortfolioState(peak_equity=100_000.0, current_equity=87_000.0)

    blocked = should_block_execution_for_drawdown(
        portfolio_state=state,
        config={"execution.drawdown.max_pct": 0.10},
    )

    assert blocked is True


def test_guard_does_not_block_when_threshold_not_exceeded() -> None:
    state = PortfolioState(peak_equity=100_000.0, current_equity=90_000.0)

    blocked = should_block_execution_for_drawdown(
        portfolio_state=state,
        config={"execution.drawdown.max_pct": 0.10},
    )

    assert blocked is False


def test_invalid_or_missing_threshold_does_not_activate_guard() -> None:
    state = PortfolioState(peak_equity=100_000.0, current_equity=70_000.0)

    assert configured_drawdown_threshold(config=None) is None
    assert configured_drawdown_threshold(config={}) is None
    assert configured_drawdown_threshold(config={"execution.drawdown.max_pct": "0.2"}) is None
    assert configured_drawdown_threshold(config={"execution.drawdown.max_pct": -0.1}) is None
    assert configured_drawdown_threshold(config={"execution.drawdown.max_pct": 1.2}) is None
    assert should_block_execution_for_drawdown(portfolio_state=state, config=None) is False
