"""Tests for deterministic risk evaluation rules (Issue #484)."""

from __future__ import annotations

import math

import pytest

from cilly_trading.risk_framework.allocation_rules import RiskLimits
from cilly_trading.risk_framework.contract import RiskEvaluationRequest
from cilly_trading.risk_framework.risk_evaluator import evaluate_risk


def _request() -> RiskEvaluationRequest:
    return RiskEvaluationRequest(
        strategy_id="strategy-a",
        symbol="AAPL",
        proposed_position_size=5_000.0,
        account_equity=100_000.0,
        current_exposure=20_000.0,
    )


def _limits() -> RiskLimits:
    return RiskLimits(
        max_account_exposure_pct=0.50,
        max_position_size=10_000.0,
        max_strategy_exposure_pct=0.30,
        max_symbol_exposure_pct=0.20,
    )


def _bounded_limits() -> RiskLimits:
    return RiskLimits(
        max_account_exposure_pct=0.80,
        max_position_size=10_000.0,
        max_strategy_exposure_pct=0.80,
        max_symbol_exposure_pct=0.80,
        max_trade_risk_pct=0.02,
        max_strategy_risk_pct=0.05,
        max_symbol_risk_pct=0.04,
        max_portfolio_risk_pct=0.10,
    )


def test_approval_case() -> None:
    response = evaluate_risk(
        _request(),
        limits=_limits(),
        strategy_exposure=10_000.0,
        symbol_exposure=8_000.0,
    )

    assert response.approved is True
    assert response.reason == "approved: within_risk_limits"
    assert response.adjusted_position_size == 5_000.0
    assert response.risk_score == 0.25


def test_rejection_max_position_size_rule() -> None:
    request = RiskEvaluationRequest(
        strategy_id="strategy-a",
        symbol="AAPL",
        proposed_position_size=12_000.0,
        account_equity=100_000.0,
        current_exposure=20_000.0,
    )

    response = evaluate_risk(
        request,
        limits=_limits(),
        strategy_exposure=5_000.0,
        symbol_exposure=5_000.0,
    )

    assert response.approved is False
    assert response.reason == "rejected: max_position_size_exceeded"
    assert response.adjusted_position_size == 10_000.0
    assert response.risk_score == 0.32


def test_rejection_max_account_exposure_pct_rule() -> None:
    request = RiskEvaluationRequest(
        strategy_id="strategy-a",
        symbol="AAPL",
        proposed_position_size=6_000.0,
        account_equity=100_000.0,
        current_exposure=48_000.0,
    )

    response = evaluate_risk(
        request,
        limits=_limits(),
        strategy_exposure=10_000.0,
        symbol_exposure=8_000.0,
    )

    assert response.approved is False
    assert response.reason == "rejected: max_account_exposure_pct_exceeded"
    assert response.adjusted_position_size == 2_000.0
    assert response.risk_score == 0.54


def test_rejection_max_strategy_exposure_pct_rule() -> None:
    response = evaluate_risk(
        _request(),
        limits=_limits(),
        strategy_exposure=26_000.0,
        symbol_exposure=8_000.0,
    )

    assert response.approved is False
    assert response.reason == "rejected: max_strategy_exposure_pct_exceeded"
    assert response.adjusted_position_size == 4_000.0
    assert response.risk_score == 0.25


def test_rejection_max_symbol_exposure_pct_rule() -> None:
    response = evaluate_risk(
        _request(),
        limits=_limits(),
        strategy_exposure=10_000.0,
        symbol_exposure=18_000.0,
    )

    assert response.approved is False
    assert response.reason == "rejected: max_symbol_exposure_pct_exceeded"
    assert response.adjusted_position_size == 2_000.0
    assert response.risk_score == 0.25


def test_boundary_equals_limit_is_approved() -> None:
    request = RiskEvaluationRequest(
        strategy_id="strategy-a",
        symbol="AAPL",
        proposed_position_size=10_000.0,
        account_equity=100_000.0,
        current_exposure=40_000.0,
    )
    limits = RiskLimits(
        max_account_exposure_pct=0.50,
        max_position_size=10_000.0,
        max_strategy_exposure_pct=0.30,
        max_symbol_exposure_pct=0.20,
    )

    response = evaluate_risk(
        request,
        limits=limits,
        strategy_exposure=20_000.0,
        symbol_exposure=10_000.0,
    )

    assert response.approved is True
    assert response.reason == "approved: within_risk_limits"
    assert response.adjusted_position_size == 10_000.0
    assert response.risk_score == 0.50


def test_determinism() -> None:
    request = _request()
    limits = _limits()

    first = evaluate_risk(
        request,
        limits=limits,
        strategy_exposure=10_000.0,
        symbol_exposure=8_000.0,
    )
    second = evaluate_risk(
        request,
        limits=limits,
        strategy_exposure=10_000.0,
        symbol_exposure=8_000.0,
    )

    assert first == second


def test_bounded_risk_approval_emits_trade_strategy_symbol_portfolio_evidence() -> None:
    request = RiskEvaluationRequest(
        strategy_id="strategy-a",
        symbol="AAPL",
        proposed_position_size=5_000.0,
        account_equity=100_000.0,
        current_exposure=10_000.0,
        entry_price=100.0,
        stop_loss_price=98.0,
        strategy_risk_used=1_000.0,
        symbol_risk_used=500.0,
        portfolio_risk_used=3_000.0,
        require_bounded_risk_evidence=True,
    )

    response = evaluate_risk(
        request,
        limits=_bounded_limits(),
        strategy_exposure=10_000.0,
        symbol_exposure=5_000.0,
    )

    assert response.approved is True
    assert response.reason == "approved: within_risk_limits"
    assert [row.rule_code for row in response.policy_evidence] == [
        "stop_loss_position_size",
        "max_trade_risk",
        "strategy_risk_budget",
        "symbol_risk_budget",
        "portfolio_risk_budget",
    ]
    assert {row.scope for row in response.policy_evidence} == {
        "trade",
        "strategy",
        "symbol",
        "portfolio",
    }
    assert {row.decision for row in response.policy_evidence} == {"approve"}


def test_bounded_risk_missing_stop_loss_fails_closed() -> None:
    request = RiskEvaluationRequest(
        strategy_id="strategy-a",
        symbol="AAPL",
        proposed_position_size=5_000.0,
        account_equity=100_000.0,
        current_exposure=10_000.0,
        require_bounded_risk_evidence=True,
    )

    response = evaluate_risk(
        request,
        limits=_bounded_limits(),
        strategy_exposure=10_000.0,
        symbol_exposure=5_000.0,
    )

    assert response.approved is False
    assert response.reason == "rejected: stop_loss_evidence_missing"
    assert response.adjusted_position_size == 0.0
    assert response.policy_evidence[0].rule_code == "stop_loss_evidence_required"


def test_bounded_risk_contradictory_stop_loss_fails_closed() -> None:
    request = RiskEvaluationRequest(
        strategy_id="strategy-a",
        symbol="AAPL",
        proposed_position_size=5_000.0,
        account_equity=100_000.0,
        current_exposure=10_000.0,
        entry_price=100.0,
        stop_loss_price=100.0,
        require_bounded_risk_evidence=True,
    )

    response = evaluate_risk(
        request,
        limits=_bounded_limits(),
        strategy_exposure=10_000.0,
        symbol_exposure=5_000.0,
    )

    assert response.approved is False
    assert response.reason == "rejected: stop_loss_evidence_invalid"
    assert response.policy_evidence[0].rule_code == "stop_loss_evidence_valid"


@pytest.mark.parametrize("invalid_value", [math.nan, math.inf])
def test_bounded_risk_non_finite_entry_price_fails_closed(invalid_value: float) -> None:
    request = RiskEvaluationRequest(
        strategy_id="strategy-a",
        symbol="AAPL",
        proposed_position_size=5_000.0,
        account_equity=100_000.0,
        current_exposure=10_000.0,
        entry_price=invalid_value,
        stop_loss_price=98.0,
        require_bounded_risk_evidence=True,
    )

    response = evaluate_risk(
        request,
        limits=_bounded_limits(),
        strategy_exposure=10_000.0,
        symbol_exposure=5_000.0,
    )

    assert response.approved is False
    assert response.reason == "rejected: stop_loss_evidence_invalid"
    assert response.adjusted_position_size == 0.0
    assert response.policy_evidence[0].rule_code == "stop_loss_evidence_valid"


@pytest.mark.parametrize("invalid_value", [math.nan, math.inf])
def test_bounded_risk_non_finite_stop_loss_price_fails_closed(
    invalid_value: float,
) -> None:
    request = RiskEvaluationRequest(
        strategy_id="strategy-a",
        symbol="AAPL",
        proposed_position_size=5_000.0,
        account_equity=100_000.0,
        current_exposure=10_000.0,
        entry_price=100.0,
        stop_loss_price=invalid_value,
        require_bounded_risk_evidence=True,
    )

    response = evaluate_risk(
        request,
        limits=_bounded_limits(),
        strategy_exposure=10_000.0,
        symbol_exposure=5_000.0,
    )

    assert response.approved is False
    assert response.reason == "rejected: stop_loss_evidence_invalid"
    assert response.adjusted_position_size == 0.0
    assert response.policy_evidence[0].rule_code == "stop_loss_evidence_valid"


def test_bounded_risk_budget_rejection_precedes_exposure_rejection() -> None:
    request = RiskEvaluationRequest(
        strategy_id="strategy-a",
        symbol="AAPL",
        proposed_position_size=80_000.0,
        account_equity=100_000.0,
        current_exposure=70_000.0,
        entry_price=100.0,
        stop_loss_price=90.0,
        require_bounded_risk_evidence=True,
    )

    response = evaluate_risk(
        request,
        limits=_bounded_limits(),
        strategy_exposure=70_000.0,
        symbol_exposure=70_000.0,
    )

    assert response.approved is False
    assert response.reason == "rejected: position_size_exceeds_stop_loss_budget"
    assert response.policy_evidence[0].decision == "reject"


def test_bounded_portfolio_risk_budget_rejection_is_deterministic() -> None:
    request = RiskEvaluationRequest(
        strategy_id="strategy-a",
        symbol="AAPL",
        proposed_position_size=5_000.0,
        account_equity=100_000.0,
        current_exposure=10_000.0,
        entry_price=100.0,
        stop_loss_price=98.0,
        portfolio_risk_used=9_950.0,
        require_bounded_risk_evidence=True,
    )

    first = evaluate_risk(
        request,
        limits=_bounded_limits(),
        strategy_exposure=10_000.0,
        symbol_exposure=5_000.0,
    )
    second = evaluate_risk(
        request,
        limits=_bounded_limits(),
        strategy_exposure=10_000.0,
        symbol_exposure=5_000.0,
    )

    assert first == second
    assert first.approved is False
    assert first.reason == "rejected: portfolio_risk_budget_exceeded"
