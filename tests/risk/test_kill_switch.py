"""Tests for global risk kill switch behavior (Issue #485)."""

from __future__ import annotations

from engine.risk_framework.allocation_rules import RiskLimits
from engine.risk_framework.contract import RiskEvaluationRequest
from engine.risk_framework.kill_switch import is_kill_switch_enabled
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


def test_enabled_kill_switch_always_rejects() -> None:
    response = evaluate_risk(
        _request(),
        limits=_limits(),
        strategy_exposure=10_000.0,
        symbol_exposure=8_000.0,
        config={"risk.kill_switch.enabled": True},
    )

    assert response.approved is False
    assert response.reason == "rejected: kill_switch_enabled"
    assert response.adjusted_position_size == 0.0
    assert response.risk_score == float("inf")


def test_disabled_kill_switch_allows_normal_approval_path() -> None:
    response = evaluate_risk(
        _request(),
        limits=_limits(),
        strategy_exposure=10_000.0,
        symbol_exposure=8_000.0,
        config={"risk.kill_switch.enabled": False},
    )

    assert response.approved is True
    assert response.reason == "approved: within_risk_limits"


def test_kill_switch_determinism() -> None:
    request = _request()
    limits = _limits()
    config = {"risk.kill_switch.enabled": True}

    first = evaluate_risk(
        request,
        limits=limits,
        strategy_exposure=10_000.0,
        symbol_exposure=8_000.0,
        config=config,
    )
    second = evaluate_risk(
        request,
        limits=limits,
        strategy_exposure=10_000.0,
        symbol_exposure=8_000.0,
        config=config,
    )

    assert first == second


def test_is_kill_switch_enabled_invalid_values_are_false() -> None:
    assert is_kill_switch_enabled(config=None) is False
    assert is_kill_switch_enabled(config={}) is False
    assert is_kill_switch_enabled(config={"risk.kill_switch.enabled": "true"}) is False
