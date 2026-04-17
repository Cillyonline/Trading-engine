"""Acceptance tests for deterministic capital allocation policy."""

from __future__ import annotations

from decimal import Decimal

from cilly_trading.portfolio_framework.capital_allocation_policy import (
    CapitalAllocationRules,
    DeterministicTradeSizingInput,
    PrioritizedAllocationConfig,
    PrioritizedAllocationSignal,
    StrategyAllocationRule,
    allocate_prioritized_signals,
    assess_capital_allocation,
    compute_deterministic_trade_notional,
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


def test_prioritization_orders_by_score_then_tie_breakers() -> None:
    """Signals are ordered by explicit deterministic priority and tie-break keys."""
    config = PrioritizedAllocationConfig(
        available_capital_notional=1000.0,
        max_positions=10,
        default_position_cap_notional=500.0,
    )
    signals = (
        PrioritizedAllocationSignal(
            signal_id="sig-3",
            strategy_id="beta",
            symbol="ETHUSDT",
            priority_score=80.0,
            requested_notional=100.0,
            signal_timestamp="2026-03-22T10:00:00Z",
        ),
        PrioritizedAllocationSignal(
            signal_id="sig-1",
            strategy_id="alpha",
            symbol="BTCUSDT",
            priority_score=90.0,
            requested_notional=100.0,
            signal_timestamp="2026-03-22T10:00:00Z",
        ),
        PrioritizedAllocationSignal(
            signal_id="sig-2",
            strategy_id="alpha",
            symbol="ADAUSDT",
            priority_score=90.0,
            requested_notional=100.0,
            signal_timestamp="2026-03-22T09:00:00Z",
        ),
    )

    result = allocate_prioritized_signals(signals=signals, config=config)

    assert [item.signal_id for item in result.decisions] == ["sig-2", "sig-1", "sig-3"]
    assert [item.priority_rank for item in result.decisions] == [1, 2, 3]


def test_constrained_capital_and_position_limit_are_enforced_deterministically() -> None:
    """Limited capital and max position count deterministically gate accepted signals."""
    config = PrioritizedAllocationConfig(
        available_capital_notional=130.0,
        max_positions=2,
        default_position_cap_notional=100.0,
    )
    signals = (
        PrioritizedAllocationSignal(
            signal_id="sig-a",
            strategy_id="s1",
            symbol="BTCUSDT",
            priority_score=100.0,
            requested_notional=100.0,
            signal_timestamp="2026-03-22T09:00:00Z",
        ),
        PrioritizedAllocationSignal(
            signal_id="sig-b",
            strategy_id="s1",
            symbol="ETHUSDT",
            priority_score=95.0,
            requested_notional=100.0,
            signal_timestamp="2026-03-22T09:01:00Z",
        ),
        PrioritizedAllocationSignal(
            signal_id="sig-c",
            strategy_id="s2",
            symbol="SOLUSDT",
            priority_score=90.0,
            requested_notional=100.0,
            signal_timestamp="2026-03-22T09:02:00Z",
        ),
    )

    result = allocate_prioritized_signals(signals=signals, config=config)

    assert result.accepted_signal_ids == ("sig-a", "sig-b")
    assert result.total_allocated_notional == 130.0
    assert result.remaining_capital_notional == 0.0
    assert result.decisions[0].allocated_notional == 100.0
    assert result.decisions[1].allocated_notional == 30.0
    assert result.decisions[2].accepted is False
    assert result.decisions[2].rejection_reason == "position_limit_reached"


def test_deterministic_ordering_and_tie_breaking_is_reproducible() -> None:
    """Equal score/timestamp signals are resolved using stable lexical tie-breakers."""
    config = PrioritizedAllocationConfig(
        available_capital_notional=500.0,
        max_positions=10,
        default_position_cap_notional=100.0,
    )
    signals = (
        PrioritizedAllocationSignal(
            signal_id="sig-2",
            strategy_id="alpha",
            symbol="ETHUSDT",
            priority_score=75.0,
            requested_notional=90.0,
            signal_timestamp="2026-03-22T11:00:00Z",
        ),
        PrioritizedAllocationSignal(
            signal_id="sig-1",
            strategy_id="alpha",
            symbol="ETHUSDT",
            priority_score=75.0,
            requested_notional=90.0,
            signal_timestamp="2026-03-22T11:00:00Z",
        ),
    )

    result_a = allocate_prioritized_signals(signals=signals, config=config)
    result_b = allocate_prioritized_signals(signals=signals, config=config)

    assert result_a == result_b
    assert [item.signal_id for item in result_a.decisions] == ["sig-1", "sig-2"]
    assert result_a.decisions[0].tie_break_key < result_a.decisions[1].tie_break_key


def test_regression_input_permutation_and_bounded_sizing_hook_remain_deterministic() -> None:
    """Regression: input order does not change outcome and bounded hook remains stable."""
    config = PrioritizedAllocationConfig(
        available_capital_notional=200.0,
        max_positions=3,
        default_position_cap_notional=120.0,
        min_allocation_notional=10.0,
    )
    signals_a = (
        PrioritizedAllocationSignal(
            signal_id="sig-x",
            strategy_id="s2",
            symbol="SOLUSDT",
            priority_score=50.0,
            requested_notional=100.0,
            signal_timestamp="2026-03-22T10:00:00Z",
            max_position_notional=80.0,
        ),
        PrioritizedAllocationSignal(
            signal_id="sig-y",
            strategy_id="s1",
            symbol="BTCUSDT",
            priority_score=60.0,
            requested_notional=100.0,
            signal_timestamp="2026-03-22T10:00:00Z",
        ),
    )
    signals_b = tuple(reversed(signals_a))

    def bounded_position_sizing_hook(
        signal: PrioritizedAllocationSignal,
        proposed_notional: float,
    ) -> float:
        if signal.signal_id == "sig-y":
            return proposed_notional * 0.5
        return proposed_notional

    result_a = allocate_prioritized_signals(
        signals=signals_a,
        config=config,
        bounded_position_sizing_hook=bounded_position_sizing_hook,
    )
    result_b = allocate_prioritized_signals(
        signals=signals_b,
        config=config,
        bounded_position_sizing_hook=bounded_position_sizing_hook,
    )

    assert result_a == result_b
    assert result_a.accepted_signal_ids == ("sig-y", "sig-x")
    assert result_a.total_allocated_notional == 130.0
    assert result_a.remaining_capital_notional == 70.0


def test_trade_sizing_computes_deterministic_notional_from_risk_budget() -> None:
    decision = compute_deterministic_trade_notional(
        DeterministicTradeSizingInput(
            account_equity=Decimal("100000"),
            max_risk_per_trade_pct=Decimal("0.01"),
            trade_risk_pct=Decimal("0.02"),
            min_trade_risk_pct=Decimal("0.005"),
            max_trade_risk_pct=Decimal("0.20"),
            notional_rounding_quantum=Decimal("0.01"),
        )
    )

    assert decision.accepted is True
    assert decision.reason_code == "sizing_accepted"
    assert decision.risk_budget_notional == Decimal("1000.00")
    assert decision.rounded_position_notional == Decimal("50000.00")


def test_trade_sizing_rejects_zero_or_negative_inputs_fail_closed() -> None:
    invalid_equity = compute_deterministic_trade_notional(
        DeterministicTradeSizingInput(
            account_equity=Decimal("0"),
            max_risk_per_trade_pct=Decimal("0.01"),
            trade_risk_pct=Decimal("0.02"),
            min_trade_risk_pct=Decimal("0.005"),
            max_trade_risk_pct=Decimal("0.20"),
            notional_rounding_quantum=Decimal("0.01"),
        )
    )
    invalid_trade_risk = compute_deterministic_trade_notional(
        DeterministicTradeSizingInput(
            account_equity=Decimal("100000"),
            max_risk_per_trade_pct=Decimal("0.01"),
            trade_risk_pct=Decimal("-0.02"),
            min_trade_risk_pct=Decimal("0.005"),
            max_trade_risk_pct=Decimal("0.20"),
            notional_rounding_quantum=Decimal("0.01"),
        )
    )

    assert invalid_equity.accepted is False
    assert invalid_equity.reason_code == "sizing_rejected:invalid_account_equity"
    assert invalid_trade_risk.accepted is False
    assert invalid_trade_risk.reason_code == "sizing_rejected:invalid_trade_risk_pct"


def test_trade_sizing_applies_deterministic_rounding() -> None:
    decision = compute_deterministic_trade_notional(
        DeterministicTradeSizingInput(
            account_equity=Decimal("10000"),
            max_risk_per_trade_pct=Decimal("0.01"),
            trade_risk_pct=Decimal("0.03"),
            min_trade_risk_pct=Decimal("0.005"),
            max_trade_risk_pct=Decimal("0.20"),
            notional_rounding_quantum=Decimal("0.01"),
        )
    )

    assert decision.accepted is True
    assert decision.proposed_position_notional == Decimal("3333.333333333333333333333333")
    assert decision.rounded_position_notional == Decimal("3333.33")
