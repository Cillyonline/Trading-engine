"""Tests for deterministic risk evaluation rules (Issue #484)."""

from __future__ import annotations

from engine.risk_framework.allocation_rules import RiskLimits
from engine.risk_framework.contract import RiskEvaluationRequest
from engine.risk_framework.risk_evaluator import evaluate_risk


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
