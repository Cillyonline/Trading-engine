"""Deterministic integration tests for compliance guard enforcement (Issue #524)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from cilly_trading.compliance.daily_loss_guard import should_block_execution_for_daily_loss
from cilly_trading.compliance.drawdown_guard import should_block_execution_for_drawdown
from cilly_trading.orchestrator.runtime import (
    ExecutionBlockedError,
    ExecutionRequest,
    execute_request,
)
from cilly_trading.portfolio.state import PortfolioState


def _request() -> ExecutionRequest:
    return ExecutionRequest(strategy_id="strategy-a", symbol="AAPL", quantity=1.0)


def _execute_with_compliance_pipeline(
    request: ExecutionRequest,
    *,
    execute_adapter: Callable[[ExecutionRequest], dict[str, Any]],
    portfolio_state: PortfolioState,
    config: dict[str, object] | None = None,
) -> dict[str, Any]:
    """Run deterministic compliance gates before execution."""

    if should_block_execution_for_drawdown(portfolio_state=portfolio_state, config=config):
        raise ExecutionBlockedError("blocked: drawdown_shutdown_active")

    if should_block_execution_for_daily_loss(portfolio_state=portfolio_state, config=config):
        raise ExecutionBlockedError("blocked: daily_loss_guard_active")

    return execute_request(request, execute_adapter=execute_adapter, config=config)


def _attempt(
    *,
    portfolio_state: PortfolioState,
    config: dict[str, object] | None = None,
) -> tuple[bool, bool, str | None, dict[str, Any] | None]:
    adapter_called = False

    def _adapter(request: ExecutionRequest) -> dict[str, Any]:
        nonlocal adapter_called
        adapter_called = True
        return {
            "status": "executed",
            "strategy_id": request.strategy_id,
            "symbol": request.symbol,
            "quantity": request.quantity,
        }

    try:
        result = _execute_with_compliance_pipeline(
            _request(),
            execute_adapter=_adapter,
            portfolio_state=portfolio_state,
            config=config,
        )
        return False, adapter_called, None, result
    except ExecutionBlockedError as exc:
        return True, adapter_called, str(exc), None


def test_kill_switch_blocks_execution_deterministically() -> None:
    state = PortfolioState(
        peak_equity=100_000.0,
        current_equity=100_000.0,
        start_of_day_equity=100_000.0,
    )
    config = {
        "execution.kill_switch.active": True,
        "execution.emergency_block.active": False,
        "execution.drawdown.max_pct": 0.20,
        "execution.daily_loss.max_abs": 10_000.0,
    }

    first = _attempt(portfolio_state=state, config=config)
    second = _attempt(portfolio_state=state, config=config)

    assert first == second
    blocked, adapter_called, reason, result = first
    assert blocked is True
    assert adapter_called is False
    assert reason == "blocked: global_kill_switch_active"
    assert result is None


def test_drawdown_shutdown_blocks_execution_deterministically() -> None:
    state = PortfolioState(
        peak_equity=100_000.0,
        current_equity=85_000.0,
        start_of_day_equity=100_000.0,
    )
    config = {
        "execution.kill_switch.active": False,
        "execution.emergency_block.active": False,
        "execution.drawdown.max_pct": 0.10,
        "execution.daily_loss.max_abs": 20_000.0,
    }

    first = _attempt(portfolio_state=state, config=config)
    second = _attempt(portfolio_state=state, config=config)

    assert first == second
    blocked, adapter_called, reason, result = first
    assert blocked is True
    assert adapter_called is False
    assert reason == "blocked: drawdown_shutdown_active"
    assert result is None


def test_daily_loss_guard_blocks_execution_deterministically() -> None:
    state = PortfolioState(
        peak_equity=110_000.0,
        current_equity=98_700.0,
        start_of_day_equity=100_000.0,
    )
    config = {
        "execution.kill_switch.active": False,
        "execution.emergency_block.active": False,
        "execution.drawdown.max_pct": 0.50,
        "execution.daily_loss.max_abs": 1_000.0,
    }

    first = _attempt(portfolio_state=state, config=config)
    second = _attempt(portfolio_state=state, config=config)

    assert first == second
    blocked, adapter_called, reason, result = first
    assert blocked is True
    assert adapter_called is False
    assert reason == "blocked: daily_loss_guard_active"
    assert result is None


def test_emergency_stop_blocks_execution_deterministically() -> None:
    state = PortfolioState(
        peak_equity=100_000.0,
        current_equity=100_000.0,
        start_of_day_equity=100_000.0,
    )
    config = {
        "execution.kill_switch.active": False,
        "execution.emergency_block.active": True,
        "execution.drawdown.max_pct": 0.20,
        "execution.daily_loss.max_abs": 10_000.0,
    }

    first = _attempt(portfolio_state=state, config=config)
    second = _attempt(portfolio_state=state, config=config)

    assert first == second
    blocked, adapter_called, reason, result = first
    assert blocked is True
    assert adapter_called is False
    assert reason == "blocked: emergency_execution_block_active"
    assert result is None


def test_execution_proceeds_when_all_guards_are_inactive() -> None:
    state = PortfolioState(
        peak_equity=100_000.0,
        current_equity=99_500.0,
        start_of_day_equity=100_000.0,
    )
    config = {
        "execution.kill_switch.active": False,
        "execution.emergency_block.active": False,
        "execution.drawdown.max_pct": 0.20,
        "execution.daily_loss.max_abs": 1_000.0,
    }

    blocked, adapter_called, reason, result = _attempt(portfolio_state=state, config=config)

    assert blocked is False
    assert adapter_called is True
    assert reason is None
    assert result == {
        "status": "executed",
        "strategy_id": "strategy-a",
        "symbol": "AAPL",
        "quantity": 1.0,
    }
