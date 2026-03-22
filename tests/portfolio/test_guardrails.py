"""Tests for deterministic portfolio-level exposure and concentration guardrails (Issue #730)."""

from __future__ import annotations

from cilly_trading.portfolio_framework.contract import PortfolioPosition, PortfolioState
from cilly_trading.portfolio_framework.guardrails import (
    PortfolioGuardrailLimits,
    assess_portfolio_guardrails,
)


def _limits() -> PortfolioGuardrailLimits:
    return PortfolioGuardrailLimits(
        max_gross_exposure_pct=0.6,
        max_abs_net_exposure_pct=0.4,
        max_offset_exposure_pct=0.35,
        max_strategy_concentration_pct=0.75,
        max_symbol_concentration_pct=0.75,
        max_position_concentration_pct=0.75,
    )


def test_exposure_limits_are_enforced() -> None:
    state = PortfolioState(
        account_equity=1_000.0,
        positions=(
            PortfolioPosition(strategy_id="alpha", symbol="BTCUSDT", quantity=4.0, mark_price=100.0),
            PortfolioPosition(strategy_id="beta", symbol="ETHUSDT", quantity=3.0, mark_price=100.0),
        ),
    )

    assessment = assess_portfolio_guardrails(state, _limits())

    assert assessment.approved is False
    assert assessment.exposure_summary.gross_exposure_pct == 0.7
    assert assessment.absolute_net_exposure_pct == 0.7
    assert "type=gross_exposure_pct" in assessment.reasons[0]


def test_concentration_limits_are_enforced() -> None:
    state = PortfolioState(
        account_equity=1_000.0,
        positions=(
            PortfolioPosition(strategy_id="alpha", symbol="BTCUSDT", quantity=5.0, mark_price=100.0),
            PortfolioPosition(strategy_id="beta", symbol="ETHUSDT", quantity=1.0, mark_price=100.0),
        ),
    )

    limits = PortfolioGuardrailLimits(
        max_gross_exposure_pct=1.0,
        max_abs_net_exposure_pct=1.0,
        max_offset_exposure_pct=1.0,
        max_strategy_concentration_pct=0.70,
        max_symbol_concentration_pct=0.70,
        max_position_concentration_pct=0.70,
    )

    assessment = assess_portfolio_guardrails(state, limits)

    assert assessment.approved is False
    assert assessment.max_strategy_concentration_pct_observed == 5.0 / 6.0
    assert assessment.max_symbol_concentration_pct_observed == 5.0 / 6.0
    assert assessment.max_position_concentration_pct_observed == 5.0 / 6.0
    assert any("type=strategy_concentration_pct" in reason for reason in assessment.reasons)
    assert any("type=symbol_concentration_pct" in reason for reason in assessment.reasons)
    assert any("type=position_concentration_pct" in reason for reason in assessment.reasons)


def test_negative_case_reports_multiple_deterministic_violations() -> None:
    state = PortfolioState(
        account_equity=1_000.0,
        positions=(
            PortfolioPosition(strategy_id="alpha", symbol="ADAUSDT", quantity=4.0, mark_price=100.0),
            PortfolioPosition(strategy_id="alpha", symbol="ADAUSDT", quantity=-4.0, mark_price=100.0),
            PortfolioPosition(strategy_id="beta", symbol="SOLUSDT", quantity=1.0, mark_price=100.0),
        ),
    )

    limits = PortfolioGuardrailLimits(
        max_gross_exposure_pct=0.6,
        max_abs_net_exposure_pct=0.2,
        max_offset_exposure_pct=0.4,
        max_strategy_concentration_pct=0.7,
        max_symbol_concentration_pct=0.7,
        max_position_concentration_pct=0.6,
    )

    assessment = assess_portfolio_guardrails(state, limits)

    assert assessment.approved is False
    assert assessment.exposure_summary.gross_exposure_pct == 0.9
    assert assessment.absolute_net_exposure_pct == 0.1
    assert assessment.offset_exposure_pct == 0.8
    assert assessment.reasons == (
        "guardrail_exceeded: type=gross_exposure_pct observed=0.9 limit=0.6",
        "guardrail_exceeded: type=offset_exposure_pct observed=0.8 limit=0.4",
        "guardrail_exceeded: type=strategy_concentration_pct observed=0.8888888888888888 limit=0.7",
        "guardrail_exceeded: type=symbol_concentration_pct observed=0.8888888888888888 limit=0.7",
    )


def test_regression_boundary_and_determinism() -> None:
    state = PortfolioState(
        account_equity=1_000.0,
        positions=(
            PortfolioPosition(strategy_id="alpha", symbol="BTCUSDT", quantity=2.0, mark_price=100.0),
            PortfolioPosition(strategy_id="beta", symbol="ETHUSDT", quantity=1.0, mark_price=100.0),
        ),
    )

    limits = PortfolioGuardrailLimits(
        max_gross_exposure_pct=0.3,
        max_abs_net_exposure_pct=0.3,
        max_offset_exposure_pct=0.0,
        max_strategy_concentration_pct=2.0 / 3.0,
        max_symbol_concentration_pct=2.0 / 3.0,
        max_position_concentration_pct=2.0 / 3.0,
    )

    first = assess_portfolio_guardrails(state, limits)
    second = assess_portfolio_guardrails(state, limits)

    assert first == second
    assert first.approved is True
    assert first.reasons == ()


def test_regression_zero_portfolio_is_bounded() -> None:
    state = PortfolioState(account_equity=0.0, positions=())
    assessment = assess_portfolio_guardrails(state, _limits())

    assert assessment.approved is True
    assert assessment.reasons == ()
    assert assessment.max_strategy_concentration_pct_observed == 0.0
    assert assessment.max_symbol_concentration_pct_observed == 0.0
    assert assessment.max_position_concentration_pct_observed == 0.0
