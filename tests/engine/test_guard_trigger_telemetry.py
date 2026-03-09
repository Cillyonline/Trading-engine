from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

import pytest
from risk.contracts import RiskEvaluationRequest

from cilly_trading.engine.logging import (
    InMemoryEngineLogSink,
    configure_engine_log_emitter,
    reset_engine_logging_for_tests,
)
from cilly_trading.engine.pipeline.orchestrator import run_pipeline
from cilly_trading.engine.risk import (
    RiskApprovalMissingError,
    RiskRejectedError,
    ThresholdRiskGate,
    enforce_approved_risk_decision,
)
from cilly_trading.engine.strategy_lifecycle.model import StrategyLifecycleState


@pytest.fixture(autouse=True)
def _reset_structured_logging() -> None:
    reset_engine_logging_for_tests()


class _ProductionLifecycleStore:
    def get_state(self, strategy_id: str) -> StrategyLifecycleState:
        return StrategyLifecycleState.PRODUCTION

    def set_state(self, strategy_id: str, new_state: StrategyLifecycleState) -> None:
        return None


@dataclass(frozen=True)
class _Position:
    quantity: Decimal
    avg_price: Decimal


@dataclass(frozen=True)
class _ExecutionConfig:
    slippage_bps: int
    commission_per_order: Decimal
    price_scale: Decimal = Decimal("0.00000001")
    money_scale: Decimal = Decimal("0.01")
    quantity_scale: Decimal = Decimal("0.00000001")
    fill_timing: Literal["next_snapshot", "same_snapshot"] = "next_snapshot"


def _guard_events(lines: tuple[str, ...]) -> list[dict[str, object]]:
    return [
        event
        for event in (json.loads(line) for line in lines)
        if event.get("event") == "guard.triggered"
    ]


def _run_rejected_pipeline(*, guard_type: str | None) -> tuple[str, ...]:
    sink = InMemoryEngineLogSink()
    configure_engine_log_emitter(sink.write)
    metadata = {} if guard_type is None else {"guard_type": guard_type}

    result = run_pipeline(
        signal={"orders": [], "snapshot": {"timestamp": "2026-02-05T00:00:00Z", "open": "100"}},
        risk_gate=ThresholdRiskGate(max_notional_usd=100.0, rule_version="threshold-v1"),
        lifecycle_store=_ProductionLifecycleStore(),
        risk_request=RiskEvaluationRequest(
            request_id="req-1",
            strategy_id="strategy-a",
            symbol="AAPL",
            notional_usd=1000.0,
            metadata=metadata,
        ),
        position=_Position(quantity=Decimal("0"), avg_price=Decimal("0")),
        execution_config=_ExecutionConfig(slippage_bps=10, commission_per_order=Decimal("1.25")),
    )
    assert result.status == "rejected"
    return sink.lines


@pytest.mark.parametrize("guard_type", ["kill_switch", "drawdown", "daily_loss", "emergency"])
def test_runtime_pipeline_rejection_emits_single_orchestrator_guard_trigger_event(
    guard_type: str,
) -> None:
    lines = _run_rejected_pipeline(guard_type=guard_type)
    guard_events = _guard_events(lines)

    assert len(guard_events) == 1
    assert guard_events[0]["payload"] == {
        "guard_type": guard_type,
        "guard_source": "risk_gate",
        "lifecycle_state": "PRODUCTION",
        "request_id": "req-1",
        "risk_decision": "REJECTED",
        "strategy_id": "strategy-a",
        "symbol": "AAPL",
    }


def test_runtime_pipeline_rejection_with_unsupported_guard_type_stays_single_event() -> None:
    lines = _run_rejected_pipeline(guard_type="unsupported_guard")
    guard_events = _guard_events(lines)
    assert len(guard_events) == 1
    assert guard_events[0]["payload"] == {
        "guard_type": "emergency",
        "guard_source": "risk_gate",
        "lifecycle_state": "PRODUCTION",
        "request_id": "req-1",
        "risk_decision": "REJECTED",
        "strategy_id": "strategy-a",
        "symbol": "AAPL",
    }


def test_runtime_pipeline_guard_trigger_emission_is_deterministic_across_identical_runs() -> None:
    def _run_once() -> tuple[str, ...]:
        reset_engine_logging_for_tests()
        return _run_rejected_pipeline(guard_type="drawdown")

    first = _run_once()
    second = _run_once()

    assert first == second
    guard_events = _guard_events(first)
    assert len(guard_events) == 1
    assert guard_events[0]["payload"]["guard_type"] == "drawdown"


def test_risk_enforcement_rejection_emits_single_guard_event_with_guard_type() -> None:
    sink = InMemoryEngineLogSink()
    configure_engine_log_emitter(sink.write)

    with pytest.raises(RiskRejectedError):
        enforce_approved_risk_decision(
            ThresholdRiskGate(max_notional_usd=100.0).evaluate(
                RiskEvaluationRequest(
                    request_id="req-1",
                    strategy_id="strategy-a",
                    symbol="AAPL",
                    notional_usd=1000.0,
                    metadata={},
                )
            )
        )

    guard_events = _guard_events(sink.lines)
    assert len(guard_events) == 1
    assert guard_events[0]["payload"]["guard_type"] == "emergency"


def test_risk_enforcement_missing_decision_emits_single_guard_event_with_guard_type() -> None:
    sink = InMemoryEngineLogSink()
    configure_engine_log_emitter(sink.write)

    with pytest.raises(RiskApprovalMissingError):
        enforce_approved_risk_decision(None)

    guard_events = _guard_events(sink.lines)
    assert len(guard_events) == 1
    assert guard_events[0]["payload"]["guard_type"] == "emergency"
