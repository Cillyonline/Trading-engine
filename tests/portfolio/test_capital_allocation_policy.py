"""Acceptance tests for deterministic capital allocation policy."""

from __future__ import annotations

from cilly_trading.portfolio_framework.capital_allocation_policy import (
    CapitalAllocationRules,
    StrategyAllocationRule,
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
