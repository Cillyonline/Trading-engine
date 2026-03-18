"""Full risk enforcement suite coverage for Issue #486."""

from __future__ import annotations

import pytest

from cilly_trading.risk_framework.allocation_rules import RiskLimits
from cilly_trading.risk_framework.contract import RiskEvaluationRequest
from cilly_trading.risk_framework.risk_evaluator import evaluate_risk


def _request(
    *,
    proposed_position_size: float = 5_000.0,
    current_exposure: float = 20_000.0,
) -> RiskEvaluationRequest:
    return RiskEvaluationRequest(
        strategy_id="strategy-a",
        symbol="AAPL",
        proposed_position_size=proposed_position_size,
        account_equity=100_000.0,
        current_exposure=current_exposure,
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


@pytest.mark.parametrize(
    (
        "risk_request",
        "strategy_exposure",
        "symbol_exposure",
        "expected_reason",
        "expected_size",
        "expected_risk_score",
    ),
    [
        (
            _request(proposed_position_size=12_000.0),
            5_000.0,
            5_000.0,
            "rejected: max_position_size_exceeded",
            10_000.0,
            0.32,
        ),
        (
            _request(proposed_position_size=6_000.0, current_exposure=48_000.0),
            10_000.0,
            8_000.0,
            "rejected: max_account_exposure_pct_exceeded",
            2_000.0,
            0.54,
        ),
        (
            _request(),
            26_000.0,
            8_000.0,
            "rejected: max_strategy_exposure_pct_exceeded",
            4_000.0,
            0.25,
        ),
        (
            _request(),
            10_000.0,
            18_000.0,
            "rejected: max_symbol_exposure_pct_exceeded",
            2_000.0,
            0.25,
        ),
    ],
)
def test_rejection_cases_for_all_rules(
    risk_request: RiskEvaluationRequest,
    strategy_exposure: float,
    symbol_exposure: float,
    expected_reason: str,
    expected_size: float,
    expected_risk_score: float,
) -> None:
    response = evaluate_risk(
        risk_request,
        limits=_limits(),
        strategy_exposure=strategy_exposure,
        symbol_exposure=symbol_exposure,
    )

    assert response.approved is False
    assert response.reason == expected_reason
    assert response.adjusted_position_size == expected_size
    assert response.risk_score == expected_risk_score


def test_boundary_equals_limit_is_approved() -> None:
    response = evaluate_risk(
        _request(proposed_position_size=10_000.0, current_exposure=40_000.0),
        limits=_limits(),
        strategy_exposure=20_000.0,
        symbol_exposure=10_000.0,
    )

    assert response.approved is True
    assert response.reason == "approved: within_risk_limits"
    assert response.adjusted_position_size == 10_000.0
    assert response.risk_score == 0.50


def test_kill_switch_override_always_rejects() -> None:
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


def test_determinism_same_inputs_same_response() -> None:
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
