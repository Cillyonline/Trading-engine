"""Tests for deterministic decision trace framework."""

from __future__ import annotations

import ast
import pathlib

from engine.journal_framework import generate_decision_trace
from engine.portfolio_framework.capital_allocation_policy import (
    CapitalAllocationRules,
    StrategyAllocationRule,
    assess_capital_allocation,
)
from engine.portfolio_framework.contract import PortfolioPosition, PortfolioState
from engine.portfolio_framework.exposure_aggregator import aggregate_portfolio_exposure



def _build_exposure_and_allocation(*, tweak: bool = False):
    state = PortfolioState(
        account_equity=1000.0,
        positions=(
            PortfolioPosition(strategy_id="s1", symbol="BTC-USD", quantity=1.0, mark_price=100.0),
            PortfolioPosition(strategy_id="s2", symbol="ETH-USD", quantity=-2.0, mark_price=50.0),
            PortfolioPosition(
                strategy_id="s1" if not tweak else "s3",
                symbol="SOL-USD",
                quantity=3.0,
                mark_price=10.0,
            ),
        ),
    )
    rules = CapitalAllocationRules(
        global_capital_cap_pct=0.5,
        strategy_rules=(
            StrategyAllocationRule(strategy_id="s1", capital_cap_pct=0.4, allocation_score=2.0),
            StrategyAllocationRule(strategy_id="s2", capital_cap_pct=0.2, allocation_score=1.0),
            StrategyAllocationRule(
                strategy_id="s3" if tweak else "s1_aux",
                capital_cap_pct=0.2,
                allocation_score=1.0,
            ),
        ),
    )
    exposure = aggregate_portfolio_exposure(state)
    allocation = assess_capital_allocation(state, rules)
    return exposure, allocation



def test_generate_decision_trace_is_deterministic() -> None:
    exposure, allocation = _build_exposure_and_allocation()
    context = {"market_regime": "range", "risk_budget": 0.3}

    trace_a = generate_decision_trace(
        exposure=exposure,
        allocation=allocation,
        decision_context=context,
    )
    trace_b = generate_decision_trace(
        exposure=exposure,
        allocation=allocation,
        decision_context=context,
    )

    assert trace_a.trace_id == trace_b.trace_id
    assert trace_a == trace_b



def test_snapshot_equality_is_stable() -> None:
    exposure_a, allocation_a = _build_exposure_and_allocation()
    exposure_b, allocation_b = _build_exposure_and_allocation()

    trace_a = generate_decision_trace(exposure=exposure_a, allocation=allocation_a)
    trace_b = generate_decision_trace(exposure=exposure_b, allocation=allocation_b)

    assert trace_a == trace_b



def test_cross_strategy_generates_distinct_trace_ids() -> None:
    exposure_a, allocation_a = _build_exposure_and_allocation(tweak=False)
    exposure_b, allocation_b = _build_exposure_and_allocation(tweak=True)

    trace_a = generate_decision_trace(exposure=exposure_a, allocation=allocation_a)
    trace_b = generate_decision_trace(exposure=exposure_b, allocation=allocation_b)

    assert trace_a.trace_id != trace_b.trace_id



def test_generate_decision_trace_has_no_side_effects(monkeypatch) -> None:
    def _forbidden(*_args, **_kwargs):
        raise AssertionError("non-deterministic function should not be called")

    monkeypatch.setattr("time.time", _forbidden)
    monkeypatch.setattr("random.random", _forbidden)

    exposure, allocation = _build_exposure_and_allocation()

    trace = generate_decision_trace(exposure=exposure, allocation=allocation)

    assert len(trace.trace_id) == 64



def test_import_boundary_no_forbidden_imports() -> None:
    forbidden_prefixes = (
        "engine.execution",
        "engine.orchestrator",
        "engine.broker",
        "engine.risk_framework",
    )

    for path in pathlib.Path("engine/journal_framework").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith(forbidden_prefixes)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                assert not module.startswith(forbidden_prefixes)
