"""Tests for deterministic decision trace framework."""

from __future__ import annotations

import ast
import pathlib

from cilly_trading.journal_framework import generate_decision_trace
from cilly_trading.journal_framework.decision_trace import _canonicalize, _deep_freeze
from cilly_trading.portfolio_framework.capital_allocation_policy import (
    CapitalAllocationRules,
    StrategyAllocationRule,
    assess_capital_allocation,
)
from cilly_trading.portfolio_framework.contract import PortfolioPosition, PortfolioState
from cilly_trading.portfolio_framework.exposure_aggregator import aggregate_portfolio_exposure



def _build_exposure_and_allocation(*, tweak: bool = False, reorder_positions: bool = False):
    positions = [
        PortfolioPosition(strategy_id="s1", symbol="BTC-USD", quantity=1.0, mark_price=100.0),
        PortfolioPosition(strategy_id="s2", symbol="ETH-USD", quantity=-2.0, mark_price=50.0),
        PortfolioPosition(
            strategy_id="s1" if not tweak else "s3",
            symbol="SOL-USD",
            quantity=3.0,
            mark_price=10.0,
        ),
    ]
    if reorder_positions:
        positions = [positions[2], positions[0], positions[1]]

    state = PortfolioState(
        account_equity=1000.0,
        positions=tuple(positions),
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



def test_identical_inputs_produce_identical_exposure_allocation_and_trace() -> None:
    exposure_a, allocation_a = _build_exposure_and_allocation()
    exposure_b, allocation_b = _build_exposure_and_allocation()
    context_a = {"market_regime": "range", "params": [1, 2, 3], "nested": {"b": 2, "a": 1}}
    context_b = {"nested": {"a": 1, "b": 2}, "params": [1, 2, 3], "market_regime": "range"}

    trace_a = generate_decision_trace(
        exposure=exposure_a,
        allocation=allocation_a,
        decision_context=context_a,
    )
    trace_b = generate_decision_trace(
        exposure=exposure_b,
        allocation=allocation_b,
        decision_context=context_b,
    )

    assert exposure_a == exposure_b
    assert allocation_a == allocation_b
    assert trace_a == trace_b



def test_snapshot_reproducible_with_different_position_ordering() -> None:
    exposure_a, allocation_a = _build_exposure_and_allocation(reorder_positions=False)
    exposure_b, allocation_b = _build_exposure_and_allocation(reorder_positions=True)

    trace_a = generate_decision_trace(exposure=exposure_a, allocation=allocation_a)
    trace_b = generate_decision_trace(exposure=exposure_b, allocation=allocation_b)

    assert trace_a.trace_id == trace_b.trace_id
    assert trace_a == trace_b



def test_cross_strategy_generates_distinct_trace_ids() -> None:
    exposure_a, allocation_a = _build_exposure_and_allocation(tweak=False)
    exposure_b, allocation_b = _build_exposure_and_allocation(tweak=True)

    trace_a = generate_decision_trace(exposure=exposure_a, allocation=allocation_a)
    trace_b = generate_decision_trace(exposure=exposure_b, allocation=allocation_b)

    assert trace_a.trace_id != trace_b.trace_id



def test_generate_decision_trace_has_no_runtime_side_effects(monkeypatch) -> None:
    def _forbidden(*_args, **_kwargs):
        raise AssertionError("non-deterministic function should not be called")

    monkeypatch.setattr("time.time", _forbidden)
    monkeypatch.setattr("random.random", _forbidden)
    monkeypatch.setattr("builtins.open", _forbidden)

    exposure, allocation = _build_exposure_and_allocation()

    trace = generate_decision_trace(exposure=exposure, allocation=allocation)

    assert len(trace.trace_id) == 64



def test_context_is_frozen_and_default_context_is_empty_mapping() -> None:
    exposure, allocation = _build_exposure_and_allocation()

    trace = generate_decision_trace(exposure=exposure, allocation=allocation, decision_context=None)

    assert dict(trace.decision_context) == {}



def test_deep_freeze_and_canonicalize_cover_container_variants() -> None:
    input_value = {
        "z": [3, {"k2": 2, "k1": 1}],
        "a": (1, 2),
    }

    frozen = _deep_freeze(input_value)
    canonical = _canonicalize(frozen)

    assert list(frozen.keys()) == ["a", "z"]
    assert frozen["a"] == (1, 2)
    assert frozen["z"][1]["k1"] == 1
    assert canonical == {"a": [1, 2], "z": [3, {"k1": 1, "k2": 2}]}



def test_import_boundary_no_forbidden_imports() -> None:
    forbidden_prefixes = (
        "cilly_trading.execution",
        "cilly_trading.orchestrator",
        "cilly_trading.broker",
        "cilly_trading.risk_framework",
    )

    for path in pathlib.Path("src/cilly_trading/journal_framework").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith(forbidden_prefixes)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                assert not module.startswith(forbidden_prefixes)
