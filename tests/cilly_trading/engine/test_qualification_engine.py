from __future__ import annotations

import pytest

from cilly_trading.engine.decision_card_contract import (
    DECISION_CARD_CONTRACT_VERSION,
    ComponentScore,
    HardGateResult,
)
from cilly_trading.engine.qualification_engine import (
    BacktestEvidenceInput,
    PortfolioFitInput,
    QualificationEngineInput,
    SENTIMENT_OVERLAY_MAX_POINTS,
    SentimentOverlayInput,
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
    backtest_evidence: BacktestEvidenceInput | None = None,
    portfolio_fit_input: PortfolioFitInput | None = None,
    sentiment_overlay: SentimentOverlayInput | None = None,
) -> QualificationEngineInput:
    return QualificationEngineInput(
        decision_card_id="dc_20260324_AAPL_RSI2",
        generated_at_utc="2026-03-24T08:10:00Z",
        symbol="AAPL",
        strategy_id="RSI2",
        hard_gates=list(hard_gates or _base_hard_gates()),
        component_scores=list(component_scores or _base_component_scores()),
        backtest_evidence=backtest_evidence,
        portfolio_fit_input=portfolio_fit_input,
        sentiment_overlay=sentiment_overlay,
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


def test_backtest_evidence_input_is_explicitly_integrated() -> None:
    input_data = _engine_input(
        backtest_evidence=BacktestEvidenceInput(
            quality_score=55.0,
            rationale="Backtest quality is reduced after stricter out-of-sample checks",
            evidence=["oos_sharpe=0.74", "profit_factor=1.08"],
        )
    )
    card = evaluate_qualification(input_data)

    backtest_component = next(
        component for component in card.score.component_scores if component.category == "backtest_quality"
    )
    assert backtest_component.score == 55.0
    assert "input_path=backtest_evidence" in backtest_component.evidence
    assert card.metadata["backtest_input_applied"] is True
    assert "Backtest input path is explicitly integrated." in card.rationale.score_explanations


def test_portfolio_fit_input_is_explicitly_integrated() -> None:
    input_data = _engine_input(
        portfolio_fit_input=PortfolioFitInput(
            fit_score=52.0,
            rationale="Portfolio fit weakens due to concentration drift",
            evidence=["sector_weight=0.27", "corr_cluster=0.69"],
        )
    )
    card = evaluate_qualification(input_data)

    portfolio_component = next(
        component for component in card.score.component_scores if component.category == "portfolio_fit"
    )
    assert portfolio_component.score == 52.0
    assert "input_path=portfolio_fit_input" in portfolio_component.evidence
    assert card.metadata["portfolio_fit_input_applied"] is True
    assert "Portfolio-fit input path is explicitly integrated." in card.rationale.score_explanations


def test_missing_sentiment_is_neutral_and_explicit() -> None:
    card = evaluate_qualification(_engine_input())

    assert card.metadata["sentiment_overlay_status"] == "missing"
    assert card.metadata["sentiment_overlay_points"] == 0.0
    assert card.score.aggregate_score == card.metadata["base_aggregate_score"]


def test_stale_sentiment_is_neutral_and_explicit() -> None:
    card = evaluate_qualification(
        _engine_input(
            sentiment_overlay=SentimentOverlayInput(
                sentiment_score=0.90,
                as_of_utc="2026-03-23T00:00:00Z",
                rationale="Positive sentiment snapshot from earlier session",
                evidence=["source=synthetic"],
                stale_after_hours=12,
            )
        )
    )

    assert card.metadata["sentiment_overlay_status"] == "stale"
    assert card.metadata["sentiment_overlay_points"] == 0.0
    assert card.score.aggregate_score == card.metadata["base_aggregate_score"]


def test_sentiment_overlay_impact_is_bounded_by_stronger_evidence_layers() -> None:
    components = _base_component_scores()
    components[1] = ComponentScore(
        category="backtest_quality",
        score=60.0,
        rationale=components[1].rationale,
        evidence=components[1].evidence,
    )
    components[2] = ComponentScore(
        category="portfolio_fit",
        score=50.0,
        rationale=components[2].rationale,
        evidence=components[2].evidence,
    )
    components[3] = ComponentScore(
        category="risk_alignment",
        score=40.0,
        rationale=components[3].rationale,
        evidence=components[3].evidence,
    )
    card = evaluate_qualification(
        _engine_input(
            component_scores=components,
            sentiment_overlay=SentimentOverlayInput(
                sentiment_score=1.0,
                as_of_utc="2026-03-24T07:59:59Z",
                rationale="Positive sentiment overlay",
                evidence=["source=synthetic"],
            ),
        )
    )

    assert card.metadata["sentiment_overlay_status"] == "applied"
    assert card.metadata["sentiment_overlay_points"] == 2.0
    assert card.metadata["sentiment_overlay_cap_points"] == 2.0
    assert card.metadata["sentiment_overlay_points"] <= card.metadata["sentiment_overlay_cap_points"]
    assert card.metadata["sentiment_overlay_cap_points"] < SENTIMENT_OVERLAY_MAX_POINTS


def test_sentiment_overlay_does_not_override_blocking_gate_rejection() -> None:
    gates = _base_hard_gates()
    gates[0] = HardGateResult(
        gate_id="drawdown_safety",
        status="fail",
        blocking=True,
        reason="Drawdown guard check failed",
        failure_reason="Max drawdown breached threshold",
        evidence=["max_dd=0.15", "threshold=0.12"],
    )
    card = evaluate_qualification(
        _engine_input(
            hard_gates=gates,
            sentiment_overlay=SentimentOverlayInput(
                sentiment_score=1.0,
                as_of_utc="2026-03-24T08:05:00Z",
                rationale="Positive sentiment overlay",
                evidence=["source=synthetic"],
            ),
        )
    )
    assert card.qualification.state == "reject"
    assert card.qualification.color == "red"
