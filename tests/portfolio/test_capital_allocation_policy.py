"""Acceptance tests for deterministic capital allocation policy."""

from __future__ import annotations

from cilly_trading.portfolio_framework.capital_allocation_policy import (
    CapitalAllocationRules,
    SignalAllocationInput,
    StrategyAllocationRule,
    allocate_prioritized_signals,
    assess_capital_allocation,
)
from cilly_trading.portfolio_framework.contract import PortfolioPosition, PortfolioState


def test_strategy_cap_violation() -> None:
    """Assessment rejects when strategy-level capital cap is exceeded."""
    state = PortfolioState(
        account_equity=1000.0,
        positions=(
            PortfolioPosition(
                strategy_id="strategy-a",
                symbol="BTCUSDT",
                quantity=6.0,
                mark_price=100.0,
            ),
        ),
    )
    rules = CapitalAllocationRules(
        global_capital_cap_pct=1.0,
        strategy_rules=(
            StrategyAllocationRule(
                strategy_id="strategy-a",
                capital_cap_pct=0.5,
                allocation_score=1.0,
            ),
        ),
    )

    assessment = assess_capital_allocation(state, rules)

    assert not assessment.approved
    assert assessment.reasons == ("strategy_cap_exceeded: strategy_id=strategy-a",)


def test_global_cap_violation() -> None:
    """Assessment rejects when global capital cap is exceeded."""
    state = PortfolioState(
        account_equity=1000.0,
        positions=(
            PortfolioPosition(
                strategy_id="strategy-a",
                symbol="BTCUSDT",
                quantity=6.0,
                mark_price=100.0,
            ),
        ),
    )
    rules = CapitalAllocationRules(
        global_capital_cap_pct=0.5,
        strategy_rules=(
            StrategyAllocationRule(
                strategy_id="strategy-a",
                capital_cap_pct=1.0,
                allocation_score=1.0,
            ),
        ),
    )

    assessment = assess_capital_allocation(state, rules)

    assert not assessment.approved
    assert assessment.reasons[0].startswith("global_cap_exceeded")


def test_boundary_equals_limit_is_approved() -> None:
    """Boundary at exact configured limit must be approved."""
    state = PortfolioState(
        account_equity=1000.0,
        positions=(
            PortfolioPosition(
                strategy_id="strategy-a",
                symbol="BTCUSDT",
                quantity=5.0,
                mark_price=100.0,
            ),
        ),
    )
    rules = CapitalAllocationRules(
        global_capital_cap_pct=0.5,
        strategy_rules=(
            StrategyAllocationRule(
                strategy_id="strategy-a",
                capital_cap_pct=0.5,
                allocation_score=1.0,
            ),
        ),
    )

    assessment = assess_capital_allocation(state, rules)

    assert assessment.approved
    assert assessment.reasons == ()


def test_assessment_is_deterministic_for_identical_input() -> None:
    """Policy assessment should return identical output for identical input."""
    state = PortfolioState(
        account_equity=2000.0,
        positions=(
            PortfolioPosition(
                strategy_id="strategy-b",
                symbol="ETHUSDT",
                quantity=2.0,
                mark_price=50.0,
            ),
            PortfolioPosition(
                strategy_id="strategy-a",
                symbol="BTCUSDT",
                quantity=1.0,
                mark_price=200.0,
            ),
        ),
    )
    rules = CapitalAllocationRules(
        global_capital_cap_pct=0.4,
        strategy_rules=(
            StrategyAllocationRule(
                strategy_id="strategy-b",
                capital_cap_pct=0.2,
                allocation_score=2.0,
            ),
            StrategyAllocationRule(
                strategy_id="strategy-a",
                capital_cap_pct=0.2,
                allocation_score=1.0,
            ),
        ),
    )

    assessment_a = assess_capital_allocation(state, rules)
    assessment_b = assess_capital_allocation(state, rules)

    assert assessment_a == assessment_b


def test_prioritization_orders_signals_by_score_then_tie_breakers() -> None:
    """Competing signals are ranked deterministically with reproducible tie-breaking."""
    state = PortfolioState(account_equity=1_000.0, positions=())
    rules = CapitalAllocationRules(
        global_capital_cap_pct=1.0,
        strategy_rules=(
            StrategyAllocationRule("alpha", 1.0, 1.0),
            StrategyAllocationRule("beta", 1.0, 1.0),
        ),
    )
    plan = allocate_prioritized_signals(
        state=state,
        rules=rules,
        candidates=(
            SignalAllocationInput(
                signal_id="sig-3",
                strategy_id="beta",
                symbol="SOLUSDT",
                side="buy",
                priority_score=7.0,
                requested_notional=100.0,
            ),
            SignalAllocationInput(
                signal_id="sig-1",
                strategy_id="alpha",
                symbol="BTCUSDT",
                side="buy",
                priority_score=10.0,
                requested_notional=100.0,
            ),
            SignalAllocationInput(
                signal_id="sig-2",
                strategy_id="alpha",
                symbol="ETHUSDT",
                side="sell",
                priority_score=10.0,
                requested_notional=100.0,
            ),
        ),
    )

    assert [row.signal_id for row in plan.decisions] == ["sig-1", "sig-2", "sig-3"]


def test_constrained_capital_allocates_higher_priority_first() -> None:
    """Limited capacity is consumed by higher priority signals first."""
    state = PortfolioState(account_equity=1_000.0, positions=())
    rules = CapitalAllocationRules(
        global_capital_cap_pct=0.2,
        strategy_rules=(
            StrategyAllocationRule("alpha", 1.0, 3.0),
            StrategyAllocationRule("beta", 1.0, 1.0),
        ),
    )
    plan = allocate_prioritized_signals(
        state=state,
        rules=rules,
        candidates=(
            SignalAllocationInput(
                signal_id="high",
                strategy_id="alpha",
                symbol="BTCUSDT",
                side="buy",
                priority_score=9.0,
                requested_notional=150.0,
            ),
            SignalAllocationInput(
                signal_id="low",
                strategy_id="beta",
                symbol="ETHUSDT",
                side="buy",
                priority_score=1.0,
                requested_notional=150.0,
            ),
        ),
    )

    assert plan.selected_signal_ids == ("high", "low")
    assert plan.decisions[0].allocation_status == "accepted"
    assert plan.decisions[0].allocated_notional == 150.0
    assert plan.decisions[1].allocation_status == "partially_allocated"
    assert plan.decisions[1].allocated_notional == 50.0


def test_prioritization_is_deterministic_for_identical_inputs() -> None:
    """Identical inputs produce identical allocation plans."""
    state = PortfolioState(account_equity=1_000.0, positions=())
    rules = CapitalAllocationRules(
        global_capital_cap_pct=0.5,
        strategy_rules=(
            StrategyAllocationRule("alpha", 0.5, 1.0),
            StrategyAllocationRule("beta", 0.5, 1.0),
        ),
    )
    candidates = (
        SignalAllocationInput(
            signal_id="sig-b",
            strategy_id="beta",
            symbol="ETHUSDT",
            side="buy",
            priority_score=2.0,
            requested_notional=100.0,
        ),
        SignalAllocationInput(
            signal_id="sig-a",
            strategy_id="alpha",
            symbol="BTCUSDT",
            side="buy",
            priority_score=2.0,
            requested_notional=100.0,
        ),
    )

    plan_a = allocate_prioritized_signals(state=state, rules=rules, candidates=candidates)
    plan_b = allocate_prioritized_signals(state=state, rules=rules, candidates=candidates)

    assert plan_a == plan_b


def test_position_limit_and_size_cap_hooks_are_bounded() -> None:
    """Bounded sizing hooks and selected-count limit are enforced deterministically."""
    state = PortfolioState(account_equity=2_000.0, positions=())
    rules = CapitalAllocationRules(
        global_capital_cap_pct=0.5,
        strategy_rules=(StrategyAllocationRule("alpha", 0.5, 1.0),),
    )
    plan = allocate_prioritized_signals(
        state=state,
        rules=rules,
        candidates=(
            SignalAllocationInput(
                signal_id="first",
                strategy_id="alpha",
                symbol="BTCUSDT",
                side="buy",
                priority_score=5.0,
                requested_notional=600.0,
                position_size_cap_notional=300.0,
            ),
            SignalAllocationInput(
                signal_id="second",
                strategy_id="alpha",
                symbol="ETHUSDT",
                side="buy",
                priority_score=4.0,
                requested_notional=200.0,
            ),
        ),
        max_selected_signals=1,
    )

    assert plan.decisions[0].allocation_status == "partially_allocated"
    assert plan.decisions[0].allocated_notional == 300.0
    assert plan.decisions[1].allocation_status == "rejected"
    assert plan.decisions[1].rejection_reason == "max_selected_signals_reached"


def test_regression_assess_capital_allocation_output_shape_unchanged() -> None:
    """Regression guard: base assessment contract remains stable for existing inputs."""
    state = PortfolioState(
        account_equity=1_000.0,
        positions=(
            PortfolioPosition("alpha", "BTCUSDT", 1.0, 100.0),
            PortfolioPosition("beta", "ETHUSDT", 2.0, 50.0),
        ),
    )
    rules = CapitalAllocationRules(
        global_capital_cap_pct=0.25,
        strategy_rules=(
            StrategyAllocationRule("alpha", 0.15, 1.0),
            StrategyAllocationRule("beta", 0.15, 1.0),
        ),
    )

    assessment = assess_capital_allocation(state, rules)

    assert assessment.approved
    assert assessment.reasons == ()
    assert [row.strategy_id for row in assessment.strategy_assessments] == ["alpha", "beta"]
