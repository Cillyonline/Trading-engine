"""Full portfolio enforcement suite for deterministic allocation behavior."""

from __future__ import annotations

from engine.portfolio_framework.capital_allocation_policy import (
    CapitalAllocationRules,
    StrategyAllocationRule,
    assess_capital_allocation,
)
from engine.portfolio_framework.contract import PortfolioPosition, PortfolioState
from engine.portfolio_framework.exposure_aggregator import aggregate_portfolio_exposure


def test_enforcement_approval_case() -> None:
    state = PortfolioState(
        account_equity=1_000.0,
        positions=(
            PortfolioPosition(
                strategy_id="alpha",
                symbol="BTCUSDT",
                quantity=1.0,
                mark_price=100.0,
            ),
            PortfolioPosition(
                strategy_id="beta",
                symbol="ETHUSDT",
                quantity=2.0,
                mark_price=50.0,
            ),
        ),
    )
    rules = CapitalAllocationRules(
        global_capital_cap_pct=0.25,
        strategy_rules=(
            StrategyAllocationRule(
                strategy_id="alpha",
                capital_cap_pct=0.15,
                allocation_score=1.0,
            ),
            StrategyAllocationRule(
                strategy_id="beta",
                capital_cap_pct=0.15,
                allocation_score=1.0,
            ),
        ),
    )

    assessment = assess_capital_allocation(state, rules)

    assert assessment.approved
    assert assessment.reasons == ()


def test_enforcement_global_cap_rejection() -> None:
    state = PortfolioState(
        account_equity=1_000.0,
        positions=(
            PortfolioPosition(
                strategy_id="alpha",
                symbol="BTCUSDT",
                quantity=3.0,
                mark_price=100.0,
            ),
        ),
    )
    rules = CapitalAllocationRules(
        global_capital_cap_pct=0.2,
        strategy_rules=(
            StrategyAllocationRule(
                strategy_id="alpha",
                capital_cap_pct=0.5,
                allocation_score=1.0,
            ),
        ),
    )

    assessment = assess_capital_allocation(state, rules)

    assert not assessment.approved
    assert assessment.reasons[0].startswith("global_cap_exceeded")


def test_enforcement_strategy_cap_rejection() -> None:
    state = PortfolioState(
        account_equity=1_000.0,
        positions=(
            PortfolioPosition(
                strategy_id="alpha",
                symbol="BTCUSDT",
                quantity=2.0,
                mark_price=100.0,
            ),
            PortfolioPosition(
                strategy_id="beta",
                symbol="SOLUSDT",
                quantity=1.0,
                mark_price=100.0,
            ),
        ),
    )
    rules = CapitalAllocationRules(
        global_capital_cap_pct=0.5,
        strategy_rules=(
            StrategyAllocationRule(
                strategy_id="alpha",
                capital_cap_pct=0.2,
                allocation_score=1.0,
            ),
            StrategyAllocationRule(
                strategy_id="beta",
                capital_cap_pct=0.5,
                allocation_score=4.0,
            ),
        ),
    )

    assessment = assess_capital_allocation(state, rules)

    assert not assessment.approved
    assert assessment.reasons == ("strategy_cap_exceeded: strategy_id=alpha",)


def test_cross_symbol_aggregation_and_enforcement_outcome() -> None:
    state = PortfolioState(
        account_equity=1_000.0,
        positions=(
            PortfolioPosition(
                strategy_id="alpha",
                symbol="ADAUSDT",
                quantity=100.0,
                mark_price=1.0,
            ),
            PortfolioPosition(
                strategy_id="beta",
                symbol="ADAUSDT",
                quantity=-40.0,
                mark_price=1.0,
            ),
            PortfolioPosition(
                strategy_id="beta",
                symbol="SOLUSDT",
                quantity=5.0,
                mark_price=20.0,
            ),
        ),
    )
    rules = CapitalAllocationRules(
        global_capital_cap_pct=0.25,
        strategy_rules=(
            StrategyAllocationRule(
                strategy_id="alpha",
                capital_cap_pct=0.25,
                allocation_score=1.0,
            ),
            StrategyAllocationRule(
                strategy_id="beta",
                capital_cap_pct=0.25,
                allocation_score=1.0,
            ),
        ),
    )

    summary = aggregate_portfolio_exposure(state)
    assessment = assess_capital_allocation(state, rules)

    assert [row.symbol for row in summary.symbol_exposures] == ["ADAUSDT", "SOLUSDT"]
    assert summary.symbol_exposures[0].total_absolute_notional == 140.0
    assert summary.symbol_exposures[0].net_notional == 60.0
    assert summary.symbol_exposures[1].total_absolute_notional == 100.0
    assert summary.symbol_exposures[1].net_notional == 100.0

    assert not assessment.approved
    assert assessment.reasons == ("strategy_cap_exceeded: strategy_id=beta",)


def test_full_portfolio_enforcement_determinism() -> None:
    state = PortfolioState(
        account_equity=2_000.0,
        positions=(
            PortfolioPosition(
                strategy_id="beta",
                symbol="ETHUSDT",
                quantity=-1.0,
                mark_price=200.0,
            ),
            PortfolioPosition(
                strategy_id="alpha",
                symbol="BTCUSDT",
                quantity=0.5,
                mark_price=400.0,
            ),
        ),
    )
    rules = CapitalAllocationRules(
        global_capital_cap_pct=0.3,
        strategy_rules=(
            StrategyAllocationRule(
                strategy_id="alpha",
                capital_cap_pct=0.2,
                allocation_score=2.0,
            ),
            StrategyAllocationRule(
                strategy_id="beta",
                capital_cap_pct=0.2,
                allocation_score=1.0,
            ),
        ),
    )

    summary_a = aggregate_portfolio_exposure(state)
    summary_b = aggregate_portfolio_exposure(state)
    assessment_a = assess_capital_allocation(state, rules)
    assessment_b = assess_capital_allocation(state, rules)

    assert summary_a == summary_b
    assert assessment_a == assessment_b
