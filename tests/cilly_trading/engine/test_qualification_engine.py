from __future__ import annotations

import pytest

from cilly_trading.engine.decision_card_contract import (
    DECISION_CARD_CONTRACT_VERSION,
    ComponentScore,
    HardGateResult,
)
from cilly_trading.engine.qualification_engine import (
    QualificationEngineInput,
    assign_confidence_tier,
    compute_aggregate_score,
    evaluate_qualification,
)


def _base_component_scores() -> list[ComponentScore]:
    return [
        ComponentScore(
            category="signal_quality",
            score=88.0,
            rationale="Signal quality demonstrates stable hit rate in recent windows",
            evidence=["hit_rate=0.64", "window=120d"],
        ),
        ComponentScore(
            category="backtest_quality",
            score=84.0,
            rationale="Backtest quality remains stable under deterministic assumptions",
            evidence=["sharpe=1.40", "profit_factor=1.60"],
        ),
        ComponentScore(
            category="portfolio_fit",
            score=79.0,
            rationale="Portfolio fit remains within concentration and correlation limits",
            evidence=["sector=0.17", "corr_cluster=0.42"],
        ),
        ComponentScore(
            category="risk_alignment",
            score=86.0,
            rationale="Risk alignment is consistent with exposure and drawdown policies",
            evidence=["risk_trade=0.005", "max_dd=0.10"],
        ),
        ComponentScore(
            category="execution_readiness",
            score=77.0,
            rationale="Execution readiness is supported by bounded slippage assumptions",
            evidence=["slippage_bps=9", "commission=1.00"],
        ),
    ]


def _base_hard_gates() -> list[HardGateResult]:
    return [
        HardGateResult(
            gate_id="drawdown_safety",
            status="pass",
            blocking=True,
            reason="Drawdown remains within guard threshold",
            evidence=["max_dd=0.08", "threshold=0.12"],
        ),
        HardGateResult(
            gate_id="portfolio_exposure_cap",
            status="pass",
            blocking=True,
            reason="Exposure remains under policy cap",
            evidence=["gross_exposure=0.41", "cap=0.60"],
        ),
    ]


def _engine_input(
    *,
    hard_gates: list[HardGateResult] | None = None,
    component_scores: list[ComponentScore] | None = None,
) -> QualificationEngineInput:
    return QualificationEngineInput(
        decision_card_id="dc_20260324_AAPL_RSI2",
        generated_at_utc="2026-03-24T08:10:00Z",
        symbol="AAPL",
        strategy_id="RSI2",
        hard_gates=list(hard_gates or _base_hard_gates()),
        component_scores=list(component_scores or _base_component_scores()),
        metadata={"analysis_run_id": "run_20260324_0810"},
    )


def test_hard_gate_blocking_failure_is_deterministically_rejected() -> None:
    gates = _base_hard_gates()
    gates[0] = HardGateResult(
        gate_id="drawdown_safety",
        status="fail",
        blocking=True,
        reason="Drawdown guard check failed",
        failure_reason="Max drawdown breached threshold",
        evidence=["max_dd=0.15", "threshold=0.12"],
    )
    card = evaluate_qualification(_engine_input(hard_gates=gates))

    assert card.contract_version == DECISION_CARD_CONTRACT_VERSION
    assert card.hard_gates.has_blocking_failure is True
    assert card.qualification.state == "reject"
    assert card.qualification.color == "red"
    assert card.rationale.gate_explanations == sorted(card.rationale.gate_explanations)


def test_score_aggregation_is_bounded_and_reproducible() -> None:
    components = _base_component_scores()
    score_a = compute_aggregate_score(component_scores=components)
    score_b = compute_aggregate_score(component_scores=list(reversed(components)))

    assert score_a == score_b
    assert 0.0 <= score_a <= 100.0
    assert score_a == 84.15


@pytest.mark.parametrize(
    ("scores", "expected"),
    [
        ([90.0, 88.0, 85.0, 87.0, 82.0], "high"),
        ([72.0, 70.0, 65.0, 68.0, 61.0], "medium"),
        ([61.0, 58.0, 55.0, 60.0, 45.0], "low"),
    ],
)
def test_confidence_tier_assignment(scores: list[float], expected: str) -> None:
    components = _base_component_scores()
    for index, value in enumerate(scores):
        components[index] = ComponentScore(
            category=components[index].category,
            score=value,
            rationale=components[index].rationale,
            evidence=components[index].evidence,
        )
    aggregate = compute_aggregate_score(component_scores=components)

    assert assign_confidence_tier(aggregate_score=aggregate, component_scores=components) == expected


def test_qualification_state_regression_representative_scenarios() -> None:
    approved = evaluate_qualification(_engine_input())
    assert approved.contract_version == DECISION_CARD_CONTRACT_VERSION
    assert approved.qualification.state == "paper_approved"
    assert approved.qualification.color == "green"

    candidate_components = _base_component_scores()
    candidate_components[2] = ComponentScore(
        category="portfolio_fit",
        score=62.0,
        rationale="Portfolio fit remains acceptable but with weaker diversification",
        evidence=["sector=0.23", "corr_cluster=0.55"],
    )
    candidate = evaluate_qualification(_engine_input(component_scores=candidate_components))
    assert candidate.qualification.state == "paper_candidate"
    assert candidate.qualification.color == "yellow"

    watch_components = _base_component_scores()
    watch_components[4] = ComponentScore(
        category="execution_readiness",
        score=42.0,
        rationale="Execution assumptions require further evidence before paper approval",
        evidence=["slippage_bps=18", "commission=1.00"],
    )
    watch = evaluate_qualification(_engine_input(component_scores=watch_components))
    assert watch.qualification.state == "watch"
    assert watch.qualification.color == "yellow"
