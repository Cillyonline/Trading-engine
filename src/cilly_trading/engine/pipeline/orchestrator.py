"""Central pipeline orchestrator enforcing risk-before-execution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Mapping, Sequence

from risk.contracts import RiskDecision, RiskEvaluationRequest, RiskGate

from cilly_trading.engine.order_execution_model import (
    DeterministicExecutionConfig,
    Fill,
    Order,
    Position,
    _execute_order,
)
from cilly_trading.engine.strategy_lifecycle.model import StrategyLifecycleState
from cilly_trading.engine.strategy_lifecycle.service import StrategyLifecycleStore


@dataclass(frozen=True)
class PipelineResult:
    """Result payload for orchestrated pipeline execution."""

    status: Literal["executed", "rejected"]
    fills: list[Fill]
    position: Position
    risk_decision: RiskDecision


def run_pipeline(
    signal: Mapping[str, object],
    *,
    risk_gate: RiskGate,
    lifecycle_store: StrategyLifecycleStore,
    risk_request: RiskEvaluationRequest,
    position: Position,
    execution_config: DeterministicExecutionConfig,
) -> PipelineResult:
    """Run the central execution pipeline for a signal.

    The risk gate is always evaluated before any execution attempt.
    """

    state = lifecycle_store.get_state(risk_request.strategy_id)
    risk_decision = risk_gate.evaluate(risk_request)
    if state != StrategyLifecycleState.PRODUCTION or risk_decision.decision != "APPROVED":
        return PipelineResult(
            status="rejected",
            fills=[],
            position=position,
            risk_decision=risk_decision,
        )

    fills, updated_position = _execute_order(
        orders=_extract_orders(signal),
        snapshot=_extract_snapshot(signal),
        position=position,
        config=execution_config,
        risk_decision=risk_decision,
    )

    return PipelineResult(
        status="executed",
        fills=fills,
        position=updated_position,
        risk_decision=risk_decision,
    )


def _extract_orders(signal: Mapping[str, object]) -> Sequence[Order]:
    orders = signal.get("orders")
    if not isinstance(orders, Sequence):
        raise ValueError("Signal must define 'orders' as a sequence")
    return orders  # type: ignore[return-value]


def _extract_snapshot(signal: Mapping[str, object]) -> Mapping[str, object]:
    snapshot = signal.get("snapshot")
    if not isinstance(snapshot, Mapping):
        raise ValueError("Signal must define 'snapshot' as a mapping")
    return snapshot


__all__ = ["PipelineResult", "run_pipeline"]
