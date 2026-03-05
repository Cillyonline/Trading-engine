"""Deterministic orchestrator entrypoint with compliance gating."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from engine.compliance.emergency_guard import is_emergency_block_active
from engine.compliance.kill_switch import is_kill_switch_active


class ExecutionBlockedError(RuntimeError):
    """Raised when execution is blocked by a deterministic compliance gate."""


@dataclass(frozen=True)
class ExecutionRequest:
    """Input contract for orchestrator execution attempts."""

    strategy_id: str
    symbol: str
    quantity: float


ExecutionAdapter = Callable[[ExecutionRequest], Any]


def execute_request(
    request: ExecutionRequest,
    *,
    execute_adapter: ExecutionAdapter,
    config: dict[str, object] | None = None,
) -> Any:
    """Execute a request unless blocked by the global kill switch.

    The compliance gate is evaluated before the adapter is called.
    """

    if is_emergency_block_active(config=config):
        raise ExecutionBlockedError("blocked: emergency_execution_block_active")

    if is_kill_switch_active(config=config):
        raise ExecutionBlockedError("blocked: global_kill_switch_active")

    return execute_adapter(request)
