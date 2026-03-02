"""Tests for deterministic decision trace framework."""

from __future__ import annotations

import pathlib

from engine.journal_framework import (
    PortfolioDecisionSnapshot,
    generate_decision_trace,
)


def test_generate_decision_trace_is_deterministic() -> None:
    snapshot = PortfolioDecisionSnapshot(
        strategy_id="mean_reversion_v1",
        symbol="BTC-USD",
        signal="BUY",
        confidence=0.81,
        allocation=0.2,
        inputs={"zscore": -2.4, "window": 20, "features": {"volatility": 0.41, "trend": -0.1}},
    )
    context = {"market_regime": "range", "risk_budget": 0.3}

    trace_a = generate_decision_trace(snapshot=snapshot, decision_context=context)
    trace_b = generate_decision_trace(snapshot=snapshot, decision_context=context)

    assert trace_a.trace_id == trace_b.trace_id
    assert trace_a == trace_b


def test_snapshot_equality_is_stable() -> None:
    snapshot_a = PortfolioDecisionSnapshot(
        strategy_id="breakout_v2",
        symbol="ETH-USD",
        signal="HOLD",
        confidence=0.5,
        allocation=0.0,
        inputs={"atr": 1.1, "range": [1, 2, 3]},
    )
    snapshot_b = PortfolioDecisionSnapshot(
        strategy_id="breakout_v2",
        symbol="ETH-USD",
        signal="HOLD",
        confidence=0.5,
        allocation=0.0,
        inputs={"atr": 1.1, "range": [1, 2, 3]},
    )

    assert snapshot_a == snapshot_b


def test_cross_strategy_generates_distinct_trace_ids() -> None:
    base_inputs = {"indicator": 42, "window": 14}
    snapshot_a = PortfolioDecisionSnapshot(
        strategy_id="strategy_a",
        symbol="SOL-USD",
        signal="BUY",
        confidence=0.6,
        allocation=0.1,
        inputs=base_inputs,
    )
    snapshot_b = PortfolioDecisionSnapshot(
        strategy_id="strategy_b",
        symbol="SOL-USD",
        signal="BUY",
        confidence=0.6,
        allocation=0.1,
        inputs=base_inputs,
    )

    trace_a = generate_decision_trace(snapshot_a)
    trace_b = generate_decision_trace(snapshot_b)

    assert trace_a.trace_id != trace_b.trace_id


def test_generate_decision_trace_has_no_side_effects(monkeypatch) -> None:
    def _forbidden(*_args, **_kwargs):
        raise AssertionError("non-deterministic function should not be called")

    monkeypatch.setattr("time.time", _forbidden)
    monkeypatch.setattr("random.random", _forbidden)

    snapshot = PortfolioDecisionSnapshot(
        strategy_id="carry_v1",
        symbol="ADA-USD",
        signal="SELL",
        confidence=None,
        allocation=None,
        inputs={"carry": -0.02},
    )

    trace = generate_decision_trace(snapshot)

    assert len(trace.trace_id) == 64


def test_snapshot_and_context_are_immutable_copies() -> None:
    inputs = {"indicator": {"fast": 1, "slow": 2}}
    context = {"regime": {"mode": "trend"}}

    snapshot = PortfolioDecisionSnapshot(
        strategy_id="immutability_v1",
        symbol="DOGE-USD",
        signal="HOLD",
        confidence=0.3,
        allocation=0.0,
        inputs=inputs,
    )
    trace = generate_decision_trace(snapshot=snapshot, decision_context=context)

    inputs["indicator"]["fast"] = 99
    context["regime"]["mode"] = "range"

    assert snapshot.inputs["indicator"]["fast"] == 1
    assert trace.decision_context["regime"]["mode"] == "trend"


def test_import_boundary_no_execution_imports() -> None:
    source = pathlib.Path("engine/journal_framework/decision_trace.py").read_text(encoding="utf-8")

    assert "engine.execution" not in source
    assert "engine.orchestrator" not in source
    assert "engine.risk_framework" not in source
    assert "engine.portfolio_framework" not in source
