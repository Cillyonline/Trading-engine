"""P56 bounded adverse-scenario validation for current risk guard behavior.

Acceptance criteria coverage:
    - drawdown-trigger behavior
    - daily-loss-trigger behavior
    - kill-switch enforcement behavior
    - blocked execution path after guard breach
    - recovery/non-recovery behavior as currently implemented
"""

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
    return ExecutionRequest(strategy_id="strategy-p56", symbol="AAPL", quantity=1.0)


def _execute_with_compliance_pipeline(
    request: ExecutionRequest,
    *,
    execute_adapter: Callable[[ExecutionRequest], dict[str, Any]],
    portfolio_state: PortfolioState,
    config: dict[str, object] | None = None,
) -> dict[str, Any]:
    if should_block_execution_for_drawdown(portfolio_state=portfolio_state, config=config):
        raise ExecutionBlockedError("blocked: drawdown_shutdown_active")

    if should_block_execution_for_daily_loss(portfolio_state=portfolio_state, config=config):
        raise ExecutionBlockedError("blocked: daily_loss_guard_active")

    return execute_request(request, execute_adapter=execute_adapter, config=config)


def _attempt(
    *,
    portfolio_state: PortfolioState,
    config: dict[str, object] | None = None,
) -> tuple[bool, bool, str | None]:
    adapter_called = False

    def _adapter(_: ExecutionRequest) -> dict[str, Any]:
        nonlocal adapter_called
        adapter_called = True
        return {"status": "executed"}

    try:
        _execute_with_compliance_pipeline(
            _request(),
            execute_adapter=_adapter,
            portfolio_state=portfolio_state,
            config=config,
        )
        return False, adapter_called, None
    except ExecutionBlockedError as exc:
        return True, adapter_called, str(exc)


def test_p56_drawdown_trigger_blocks_and_path_is_blocked() -> None:
    blocked, adapter_called, reason = _attempt(
        portfolio_state=PortfolioState(
            peak_equity=100_000.0,
            current_equity=85_000.0,
            start_of_day_equity=100_000.0,
        ),
        config={
            "execution.kill_switch.active": False,
            "execution.emergency_block.active": False,
            "execution.drawdown.max_pct": 0.10,
            "execution.daily_loss.max_abs": 50_000.0,
        },
    )

    assert blocked is True
    assert adapter_called is False
    assert reason == "blocked: drawdown_shutdown_active"


def test_p56_daily_loss_trigger_blocks_and_path_is_blocked() -> None:
    blocked, adapter_called, reason = _attempt(
        portfolio_state=PortfolioState(
            peak_equity=110_000.0,
            current_equity=98_800.0,
            start_of_day_equity=100_000.0,
        ),
        config={
            "execution.kill_switch.active": False,
            "execution.emergency_block.active": False,
            "execution.drawdown.max_pct": 0.90,
            "execution.daily_loss.max_abs": 1_000.0,
        },
    )

    assert blocked is True
    assert adapter_called is False
    assert reason == "blocked: daily_loss_guard_active"


def test_p56_kill_switch_enforcement_overrides_other_conditions() -> None:
    blocked, adapter_called, reason = _attempt(
        portfolio_state=PortfolioState(
            peak_equity=100_000.0,
            current_equity=100_000.0,
            start_of_day_equity=100_000.0,
        ),
        config={
            "execution.kill_switch.active": True,
            "execution.emergency_block.active": False,
            "execution.drawdown.max_pct": 0.50,
            "execution.daily_loss.max_abs": 10_000.0,
        },
    )

    assert blocked is True
    assert adapter_called is False
    assert reason == "blocked: global_kill_switch_active"


def test_p56_drawdown_recovery_behavior_matches_current_implementation() -> None:
    config = {
        "execution.kill_switch.active": False,
        "execution.emergency_block.active": False,
        "execution.drawdown.max_pct": 0.10,
        "execution.daily_loss.max_abs": 50_000.0,
    }

    blocked_first, adapter_called_first, reason_first = _attempt(
        portfolio_state=PortfolioState(
            peak_equity=100_000.0,
            current_equity=85_000.0,
            start_of_day_equity=100_000.0,
        ),
        config=config,
    )
    blocked_second, adapter_called_second, reason_second = _attempt(
        portfolio_state=PortfolioState(
            peak_equity=100_000.0,
            current_equity=95_000.0,
            start_of_day_equity=100_000.0,
        ),
        config=config,
    )

    assert blocked_first is True
    assert adapter_called_first is False
    assert reason_first == "blocked: drawdown_shutdown_active"
    assert blocked_second is False
    assert adapter_called_second is True
    assert reason_second is None


def test_p56_daily_loss_recovery_behavior_matches_current_implementation() -> None:
    config = {
        "execution.kill_switch.active": False,
        "execution.emergency_block.active": False,
        "execution.drawdown.max_pct": 0.90,
        "execution.daily_loss.max_abs": 1_000.0,
    }

    blocked_first, adapter_called_first, reason_first = _attempt(
        portfolio_state=PortfolioState(
            peak_equity=110_000.0,
            current_equity=98_800.0,
            start_of_day_equity=100_000.0,
        ),
        config=config,
    )
    blocked_second, adapter_called_second, reason_second = _attempt(
        portfolio_state=PortfolioState(
            peak_equity=110_000.0,
            current_equity=99_500.0,
            start_of_day_equity=100_000.0,
        ),
        config=config,
    )

    assert blocked_first is True
    assert adapter_called_first is False
    assert reason_first == "blocked: daily_loss_guard_active"
    assert blocked_second is False
    assert adapter_called_second is True
    assert reason_second is None


def test_p56_kill_switch_non_recovery_until_config_switches_off() -> None:
    blocked_first, adapter_called_first, reason_first = _attempt(
        portfolio_state=PortfolioState(
            peak_equity=100_000.0,
            current_equity=100_000.0,
            start_of_day_equity=100_000.0,
        ),
        config={
            "execution.kill_switch.active": True,
            "execution.emergency_block.active": False,
            "execution.drawdown.max_pct": 0.50,
            "execution.daily_loss.max_abs": 10_000.0,
        },
    )
    blocked_second, adapter_called_second, reason_second = _attempt(
        portfolio_state=PortfolioState(
            peak_equity=100_000.0,
            current_equity=100_000.0,
            start_of_day_equity=100_000.0,
        ),
        config={
            "execution.kill_switch.active": True,
            "execution.emergency_block.active": False,
            "execution.drawdown.max_pct": 0.50,
            "execution.daily_loss.max_abs": 10_000.0,
        },
    )
    blocked_third, adapter_called_third, reason_third = _attempt(
        portfolio_state=PortfolioState(
            peak_equity=100_000.0,
            current_equity=100_000.0,
            start_of_day_equity=100_000.0,
        ),
        config={
            "execution.kill_switch.active": False,
            "execution.emergency_block.active": False,
            "execution.drawdown.max_pct": 0.50,
            "execution.daily_loss.max_abs": 10_000.0,
        },
    )

    assert blocked_first is True
    assert adapter_called_first is False
    assert reason_first == "blocked: global_kill_switch_active"
    assert blocked_second is True
    assert adapter_called_second is False
    assert reason_second == "blocked: global_kill_switch_active"
    assert blocked_third is False
    assert adapter_called_third is True
    assert reason_third is None
