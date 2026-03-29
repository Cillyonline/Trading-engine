"""Central pipeline orchestrator enforcing risk-before-execution.

This path is bounded to deterministic non-live operation. Pipeline approval is
strictly a local runtime guard and must not be interpreted as live-trading
approval.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal, Mapping, Sequence

from risk.contracts import RiskDecision, RiskEvaluationRequest, RiskGate

from cilly_trading.engine.logging import emit_structured_engine_log
from cilly_trading.engine.order_execution_model import (
    DeterministicExecutionConfig,
    ExecutionEvent,
    Order,
    Position,
    _execute_order,
)
from cilly_trading.engine.risk import resolve_runtime_guard_type
from cilly_trading.engine.strategy_lifecycle.model import StrategyLifecycleState
from cilly_trading.engine.strategy_lifecycle.service import StrategyLifecycleStore

_ALLOWED_RISK_DECISIONS: frozenset[str] = frozenset({"APPROVED", "REJECTED"})


@dataclass(frozen=True)
class PipelineResult:
    """Result payload for orchestrated pipeline execution."""

    status: Literal["executed", "rejected"]
    fills: list[ExecutionEvent]
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
    normalized_risk_decision = _normalize_risk_decision_value(risk_decision.decision)
    normalized_position = _extract_position(
        position,
        strategy_id=risk_request.strategy_id,
        symbol=risk_request.symbol,
    )
    orders = _extract_orders(
        signal,
        strategy_id=risk_request.strategy_id,
        symbol=risk_request.symbol,
        position_id=normalized_position.position_id,
    )
    snapshot = _extract_snapshot(signal)
    emit_structured_engine_log(
        "order_submission.attempt",
            payload={
                "request_id": risk_request.request_id,
                "strategy_id": risk_request.strategy_id,
                "symbol": risk_request.symbol,
            "order_count": len(orders),
            "snapshot_key": _extract_snapshot_key(snapshot),
            "lifecycle_state": state.value,
            "risk_decision": normalized_risk_decision,
        },
    )

    if state != StrategyLifecycleState.PRODUCTION or normalized_risk_decision != "APPROVED":
        guard_source = (
            "lifecycle"
            if state != StrategyLifecycleState.PRODUCTION
            else "risk_gate"
        )
        emit_structured_engine_log(
            "guard.triggered",
            payload={
                "guard_type": resolve_runtime_guard_type(
                    request=risk_request,
                    guard_source=guard_source,
                ),
                "request_id": risk_request.request_id,
                "strategy_id": risk_request.strategy_id,
                "symbol": risk_request.symbol,
                "guard_source": guard_source,
                "lifecycle_state": state.value,
                "risk_decision": normalized_risk_decision,
            },
        )
        return PipelineResult(
            status="rejected",
            fills=[],
            position=normalized_position,
            risk_decision=risk_decision,
        )

    fills, updated_position = _execute_order(
        orders=orders,
        snapshot=snapshot,
        position=normalized_position,
        config=execution_config,
        risk_decision=risk_decision,
    )
    emit_structured_engine_log(
        "order_submission.executed",
        payload={
            "request_id": risk_request.request_id,
            "strategy_id": risk_request.strategy_id,
            "symbol": risk_request.symbol,
            "fill_count": len(fills),
            "snapshot_key": _extract_snapshot_key(snapshot),
        },
    )

    return PipelineResult(
        status="executed",
        fills=fills,
        position=updated_position,
        risk_decision=risk_decision,
    )


def _normalize_risk_decision_value(value: object) -> str:
    decision = str(value)
    if decision in _ALLOWED_RISK_DECISIONS:
        return decision
    return "REJECTED"


def _extract_orders(
    signal: Mapping[str, object],
    *,
    strategy_id: str,
    symbol: str,
    position_id: str,
) -> Sequence[Order]:
    orders = signal.get("orders")
    if not isinstance(orders, Sequence):
        raise ValueError("Signal must define 'orders' as a sequence")
    normalized_orders: list[Order] = []
    for order in orders:
        if isinstance(order, Order):
            normalized_orders.append(order)
            continue
        if isinstance(order, Mapping):
            normalized_orders.append(Order.model_validate(order))
            continue
        if all(hasattr(order, field) for field in ("id", "side", "quantity", "created_snapshot_key", "sequence")):
            normalized_orders.append(
                Order(
                    order_id=str(order.id),
                    strategy_id=str(strategy_id),
                    symbol=str(symbol),
                    sequence=int(order.sequence),
                    side=str(order.side),
                    order_type="market",
                    time_in_force="day",
                    status="created",
                    quantity=Decimal(str(order.quantity)),
                    created_at=str(order.created_snapshot_key),
                    position_id=position_id,
                )
            )
            continue
        normalized_orders.append(Order.model_validate(order))
    return normalized_orders


def _extract_position(position: object, *, strategy_id: str, symbol: str) -> Position:
    if isinstance(position, Position):
        return position
    if isinstance(position, Mapping):
        return Position.model_validate(position)
    if all(hasattr(position, field) for field in ("quantity", "avg_price")):
        quantity = Decimal(str(position.quantity))
        avg_price = Decimal(str(position.avg_price))
        status = "flat" if quantity == Decimal("0") else "open"
        return Position(
            position_id="runtime-position",
            strategy_id=strategy_id,
            symbol=symbol,
            direction="long",
            status=status,
            opened_at="legacy-position",
            quantity_opened=quantity,
            quantity_closed=Decimal("0"),
            net_quantity=quantity,
            average_entry_price=avg_price,
            order_ids=[],
            execution_event_ids=[],
            trade_ids=[],
        )
    return Position.model_validate(position)


def _extract_snapshot(signal: Mapping[str, object]) -> Mapping[str, object]:
    snapshot = signal.get("snapshot")
    if not isinstance(snapshot, Mapping):
        raise ValueError("Signal must define 'snapshot' as a mapping")
    return snapshot


def _extract_snapshot_key(snapshot: Mapping[str, object]) -> str:
    for key in ("timestamp", "snapshot_key", "id"):
        value = snapshot.get(key)
        if value is not None:
            return str(value)
    return "unknown"


__all__ = ["PipelineResult", "run_pipeline"]
