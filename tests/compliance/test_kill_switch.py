"""Tests for deterministic global kill switch orchestration guard."""

from __future__ import annotations

import pytest

from cilly_trading.orchestrator.runtime import (
    ExecutionBlockedError,
    ExecutionRequest,
    execute_request,
)


def _request() -> ExecutionRequest:
    return ExecutionRequest(strategy_id="strategy-a", symbol="AAPL", quantity=1.0)


def test_execution_blocked_when_kill_switch_active() -> None:
    adapter_called = False

    def _adapter(_: ExecutionRequest) -> dict[str, object]:
        nonlocal adapter_called
        adapter_called = True
        return {"status": "executed"}

    with pytest.raises(ExecutionBlockedError, match="global_kill_switch_active"):
        execute_request(
            _request(),
            execute_adapter=_adapter,
            config={"execution.kill_switch.active": True},
        )

    assert adapter_called is False


def test_execution_proceeds_when_kill_switch_inactive() -> None:
    adapter_called = False

    def _adapter(request: ExecutionRequest) -> dict[str, object]:
        nonlocal adapter_called
        adapter_called = True
        return {
            "status": "executed",
            "strategy_id": request.strategy_id,
            "symbol": request.symbol,
            "quantity": request.quantity,
        }

    result = execute_request(
        _request(),
        execute_adapter=_adapter,
        config={"execution.kill_switch.active": False},
    )

    assert adapter_called is True
    assert result["status"] == "executed"
