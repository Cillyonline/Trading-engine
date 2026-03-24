"""Tests for the canonical portfolio decision pipeline (Issue #759)."""

from __future__ import annotations

from cilly_trading.portfolio_framework import (
    CapitalAllocationRules,
    PortfolioGuardrailLimits,
    PortfolioPosition,
    PortfolioState,
    PrioritizedAllocationConfig,
    PrioritizedAllocationSignal,
    StrategyAllocationRule,
    run_portfolio_decision_pipeline,
)


def _allocation_rules() -> CapitalAllocationRules:
    return CapitalAllocationRules(
        global_capital_cap_pct=0.60,
        strategy_rules=(
            StrategyAllocationRule(
                strategy_id="alpha",
                capital_cap_pct=0.60,
                allocation_score=1.0,
            ),
            StrategyAllocationRule(
                strategy_id="beta",
                capital_cap_pct=0.60,
                allocation_score=1.0,
            ),
        ),
    )


def _guardrail_limits() -> PortfolioGuardrailLimits:
    return PortfolioGuardrailLimits(
        max_gross_exposure_pct=0.60,
        max_abs_net_exposure_pct=0.60,
        max_offset_exposure_pct=0.20,
        max_strategy_concentration_pct=1.0,
        max_symbol_concentration_pct=1.0,
        max_position_concentration_pct=1.0,
    )


def test_pipeline_approves_signal_and_persists_it_in_final_state() -> None:
    result = run_portfolio_decision_pipeline(
        state=PortfolioState(account_equity=1_000.0, positions=()),
        signals=(
            PrioritizedAllocationSignal(
                signal_id="sig-1",
                strategy_id="alpha",
                symbol="BTCUSDT",
                priority_score=90.0,
                requested_notional=250.0,
                signal_timestamp="2026-03-24T09:00:00Z",
                mark_price=100.0,
            ),
        ),
        allocation_config=PrioritizedAllocationConfig(
            available_capital_notional=300.0,
            max_positions=2,
            default_position_cap_notional=300.0,
            min_allocation_notional=50.0,
        ),
        allocation_rules=_allocation_rules(),
        guardrail_limits=_guardrail_limits(),
    )

    assert result.approved_signal_ids == ("sig-1",)
    assert result.rejected_signal_ids == ()
    assert result.constraint_hit_signal_ids == ()
    assert result.remaining_capital_notional == 50.0
    assert len(result.final_state.positions) == 1
    assert result.decisions[0].outcome == "approved"
    assert result.decisions[0].primary_constraint is None
    assert result.decisions[0].constraint_categories == ()
    assert result.decisions[0].allocation_assessment is not None
    assert result.decisions[0].guardrail_assessment is not None
    assert result.decisions[0].intent.higher_priority_approved_signal_ids == ()
    assert result.decisions[0].intent.capital_after_signal == 50.0


def test_pipeline_rejects_signal_before_exposure_checks_when_intent_is_below_minimum() -> None:
    result = run_portfolio_decision_pipeline(
        state=PortfolioState(account_equity=1_000.0, positions=()),
        signals=(
            PrioritizedAllocationSignal(
                signal_id="sig-small",
                strategy_id="alpha",
                symbol="ETHUSDT",
                priority_score=90.0,
                requested_notional=25.0,
                signal_timestamp="2026-03-24T09:00:00Z",
            ),
        ),
        allocation_config=PrioritizedAllocationConfig(
            available_capital_notional=300.0,
            max_positions=2,
            default_position_cap_notional=300.0,
            min_allocation_notional=50.0,
        ),
        allocation_rules=_allocation_rules(),
        guardrail_limits=_guardrail_limits(),
    )

    assert result.approved_signal_ids == ()
    assert result.rejected_signal_ids == ("sig-small",)
    assert result.constraint_hit_signal_ids == ()
    assert result.final_state.positions == ()
    assert result.decisions[0].outcome == "rejected"
    assert result.decisions[0].primary_constraint == "below_min_allocation"
    assert result.decisions[0].constraint_categories == ("sizing",)
    assert result.decisions[0].outcome_reasons == ("below_min_allocation",)
    assert result.decisions[0].allocation_assessment is None
    assert result.decisions[0].guardrail_assessment is None


def test_pipeline_resolves_prioritization_conflicts_deterministically() -> None:
    result = run_portfolio_decision_pipeline(
        state=PortfolioState(account_equity=1_000.0, positions=()),
        signals=(
            PrioritizedAllocationSignal(
                signal_id="sig-b",
                strategy_id="alpha",
                symbol="ETHUSDT",
                priority_score=90.0,
                requested_notional=100.0,
                signal_timestamp="2026-03-24T09:00:00Z",
            ),
            PrioritizedAllocationSignal(
                signal_id="sig-a",
                strategy_id="alpha",
                symbol="BTCUSDT",
                priority_score=90.0,
                requested_notional=100.0,
                signal_timestamp="2026-03-24T09:00:00Z",
            ),
        ),
        allocation_config=PrioritizedAllocationConfig(
            available_capital_notional=200.0,
            max_positions=1,
            default_position_cap_notional=100.0,
            min_allocation_notional=10.0,
        ),
        allocation_rules=_allocation_rules(),
        guardrail_limits=_guardrail_limits(),
    )

    assert [item.signal_id for item in result.decisions] == ["sig-a", "sig-b"]
    assert [item.intent.priority_rank for item in result.decisions] == [1, 2]
    assert result.approved_signal_ids == ("sig-a",)
    assert result.rejected_signal_ids == ("sig-b",)
    assert result.decisions[1].primary_constraint == "position_limit_reached"
    assert result.decisions[1].constraint_categories == ("capacity",)
    assert result.decisions[1].intent.higher_priority_approved_signal_ids == ("sig-a",)
    assert result.decisions[1].outcome_reasons == ("position_limit_reached",)


def test_pipeline_marks_exposure_guardrail_constraint_hits_without_mutating_state() -> None:
    initial_state = PortfolioState(
        account_equity=1_000.0,
        positions=(
            PortfolioPosition(
                strategy_id="alpha",
                symbol="BTCUSDT",
                quantity=4.5,
                mark_price=100.0,
            ),
        ),
    )

    result = run_portfolio_decision_pipeline(
        state=initial_state,
        signals=(
            PrioritizedAllocationSignal(
                signal_id="sig-exposure",
                strategy_id="alpha",
                symbol="ETHUSDT",
                priority_score=90.0,
                requested_notional=200.0,
                signal_timestamp="2026-03-24T09:00:00Z",
                mark_price=100.0,
            ),
        ),
        allocation_config=PrioritizedAllocationConfig(
            available_capital_notional=300.0,
            max_positions=2,
            default_position_cap_notional=300.0,
            min_allocation_notional=10.0,
        ),
        allocation_rules=CapitalAllocationRules(
            global_capital_cap_pct=1.0,
            strategy_rules=(
                StrategyAllocationRule(
                    strategy_id="alpha",
                    capital_cap_pct=1.0,
                    allocation_score=1.0,
                ),
            ),
        ),
        guardrail_limits=PortfolioGuardrailLimits(
            max_gross_exposure_pct=0.60,
            max_abs_net_exposure_pct=1.0,
            max_offset_exposure_pct=1.0,
            max_strategy_concentration_pct=1.0,
            max_symbol_concentration_pct=1.0,
            max_position_concentration_pct=1.0,
        ),
    )

    assert result.approved_signal_ids == ()
    assert result.rejected_signal_ids == ()
    assert result.constraint_hit_signal_ids == ("sig-exposure",)
    assert result.final_state == initial_state
    assert result.remaining_capital_notional == 300.0
    assert result.decisions[0].outcome == "constraint_hit"
    assert result.decisions[0].primary_constraint == (
        "guardrail_exceeded: type=gross_exposure_pct observed=0.65 limit=0.6"
    )
    assert result.decisions[0].constraint_categories == ("exposure",)
    assert result.decisions[0].intent.higher_priority_approved_signal_ids == ()
    assert result.decisions[0].outcome_reasons == (
        "guardrail_exceeded: type=gross_exposure_pct observed=0.65 limit=0.6",
    )
    assert result.decisions[0].allocation_assessment is not None
    assert result.decisions[0].guardrail_assessment is not None


def test_pipeline_marks_concentration_constraint_hits_with_explicit_categories() -> None:
    result = run_portfolio_decision_pipeline(
        state=PortfolioState(account_equity=1_000.0, positions=()),
        signals=(
            PrioritizedAllocationSignal(
                signal_id="sig-concentration",
                strategy_id="alpha",
                symbol="BTCUSDT",
                priority_score=90.0,
                requested_notional=250.0,
                signal_timestamp="2026-03-24T09:00:00Z",
                mark_price=100.0,
            ),
        ),
        allocation_config=PrioritizedAllocationConfig(
            available_capital_notional=300.0,
            max_positions=2,
            default_position_cap_notional=300.0,
            min_allocation_notional=10.0,
        ),
        allocation_rules=CapitalAllocationRules(
            global_capital_cap_pct=1.0,
            strategy_rules=(
                StrategyAllocationRule(
                    strategy_id="alpha",
                    capital_cap_pct=1.0,
                    allocation_score=1.0,
                ),
            ),
        ),
        guardrail_limits=PortfolioGuardrailLimits(
            max_gross_exposure_pct=1.0,
            max_abs_net_exposure_pct=1.0,
            max_offset_exposure_pct=1.0,
            max_strategy_concentration_pct=0.90,
            max_symbol_concentration_pct=0.90,
            max_position_concentration_pct=0.90,
        ),
    )

    assert result.approved_signal_ids == ()
    assert result.constraint_hit_signal_ids == ("sig-concentration",)
    assert result.decisions[0].outcome == "constraint_hit"
    assert result.decisions[0].constraint_categories == ("concentration",)
    assert result.decisions[0].primary_constraint == (
        "guardrail_exceeded: type=strategy_concentration_pct observed=1.0 limit=0.9"
    )
    assert result.decisions[0].outcome_reasons == (
        "guardrail_exceeded: type=strategy_concentration_pct observed=1.0 limit=0.9",
        "guardrail_exceeded: type=symbol_concentration_pct observed=1.0 limit=0.9",
        "guardrail_exceeded: type=position_concentration_pct observed=1.0 limit=0.9",
    )
