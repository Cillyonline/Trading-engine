from __future__ import annotations

from cilly_trading.engine.decision_card_contract import ComponentScore, HardGateResult
from cilly_trading.engine.qualification_engine import (
    BacktestEvidenceInput,
    PortfolioFitInput,
    QualificationEngineInput,
    SENTIMENT_OVERLAY_MAX_POINTS,
    SentimentOverlayInput,
    compute_bounded_expected_value,
    compute_bounded_win_rate,
    evaluate_qualification,
)


def _base_component_scores() -> list[ComponentScore]:
    return [
        ComponentScore(
            category="signal_quality",
            score=86.0,
            rationale="Signal quality remains stable across deterministic windows",
            evidence=["hit_rate=0.62", "window=120d"],
        ),
        ComponentScore(
            category="backtest_quality",
            score=82.0,
            rationale="Backtest quality remains bounded and reproducible",
            evidence=["sharpe=1.32", "profit_factor=1.54"],
        ),
        ComponentScore(
            category="portfolio_fit",
            score=80.0,
            rationale="Portfolio fit remains inside configured concentration bounds",
            evidence=["sector=0.18", "corr_cluster=0.44"],
        ),
        ComponentScore(
            category="risk_alignment",
            score=85.0,
            rationale="Risk alignment is consistent with explicit risk policy",
            evidence=["risk_trade=0.005", "max_dd=0.10"],
        ),
        ComponentScore(
            category="execution_readiness",
            score=78.0,
            rationale="Execution assumptions remain deterministic and bounded",
            evidence=["slippage_bps=9", "commission=1.00"],
        ),
    ]


def _base_hard_gates() -> list[HardGateResult]:
    return [
        HardGateResult(
            gate_id="drawdown_safety",
            status="pass",
            blocking=True,
            reason="Drawdown remains under policy threshold",
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
        decision_card_id="dc_20260329_AAPL_RSI2",
        generated_at_utc="2026-03-29T10:00:00Z",
        symbol="AAPL",
        strategy_id="RSI2",
        hard_gates=list(hard_gates or _base_hard_gates()),
        component_scores=list(component_scores or _base_component_scores()),
        backtest_evidence=backtest_evidence,
        portfolio_fit_input=portfolio_fit_input,
        sentiment_overlay=sentiment_overlay,
        metadata={"analysis_run_id": "run_20260329_1000"},
    )


def test_decision_layer_integrates_backtest_portfolio_and_bounded_sentiment() -> None:
    card = evaluate_qualification(
        _engine_input(
            backtest_evidence=BacktestEvidenceInput(
                quality_score=57.0,
                rationale="Backtest quality decreases under stricter out-of-sample checks",
                evidence=["oos_sharpe=0.78", "profit_factor=1.07"],
            ),
            portfolio_fit_input=PortfolioFitInput(
                fit_score=53.0,
                rationale="Portfolio fit weakens due to concentration drift",
                evidence=["sector_weight=0.27", "corr_cluster=0.66"],
            ),
            sentiment_overlay=SentimentOverlayInput(
                sentiment_score=1.0,
                as_of_utc="2026-03-29T09:45:00Z",
                rationale="Positive bounded sentiment overlay",
                evidence=["source=synthetic"],
            ),
        )
    )

    by_category = {component.category: component for component in card.score.component_scores}
    assert by_category["backtest_quality"].score == 57.0
    assert "input_path=backtest_evidence" in by_category["backtest_quality"].evidence
    assert by_category["portfolio_fit"].score == 53.0
    assert "input_path=portfolio_fit_input" in by_category["portfolio_fit"].evidence
    assert card.metadata["backtest_input_applied"] is True
    assert card.metadata["portfolio_fit_input_applied"] is True

    assert card.metadata["sentiment_overlay_status"] == "applied"
    assert card.metadata["sentiment_overlay_points"] <= card.metadata["sentiment_overlay_cap_points"]
    assert card.metadata["sentiment_overlay_cap_points"] <= SENTIMENT_OVERLAY_MAX_POINTS
    assert "Sentiment overlay status=applied" in " ".join(card.rationale.score_explanations)


def test_evidence_semantics_and_contract_boundary_remain_explicit() -> None:
    card = evaluate_qualification(_engine_input())

    confidence_reason = card.score.confidence_reason.casefold()
    assert any(term in confidence_reason for term in ("aggregate", "component", "threshold", "evidence"))
    assert card.metadata["qualification_threshold_profile_id"] == "qualification-threshold.mean-reversion.v1"
    assert "Qualification threshold profile applied:" in " ".join(card.rationale.score_explanations)
    assert "does not imply live-trading approval" in card.rationale.final_explanation.casefold()
    assert [component.category for component in card.score.component_scores] == [
        "backtest_quality",
        "execution_readiness",
        "portfolio_fit",
        "risk_alignment",
        "signal_quality",
    ]


def test_robustness_audit_and_boundary_language_are_integrated_into_decision_card() -> None:
    card = evaluate_qualification(_engine_input())
    audit = card.metadata["qualification_profile_robustness_audit"]
    score_explanations = " ".join(card.rationale.score_explanations)

    assert audit["stable_slice_ids"] == ["covered.current_evidence.v1"]
    assert audit["failing_slice_ids"] == ["failure_envelope.execution_stress.v1"]
    assert "Qualification-profile robustness audit:" in score_explanations
    assert audit["audit_summary"] in score_explanations
    assert audit["interpretation_limit"] in score_explanations

    final_explanation = card.rationale.final_explanation.casefold()
    assert "covered conditions" in final_explanation
    assert "weak or failing slices limit interpretation outside covered conditions" in (
        final_explanation
    )
    assert "live-trading approval" in final_explanation
    assert "paper profitability" in final_explanation
    assert "trader_validation" in final_explanation


def test_stale_sentiment_overlay_is_explicitly_neutral_and_bounded() -> None:
    card = evaluate_qualification(
        _engine_input(
            sentiment_overlay=SentimentOverlayInput(
                sentiment_score=1.0,
                as_of_utc="2026-03-27T00:00:00Z",
                rationale="Positive sentiment snapshot from older session",
                evidence=["source=synthetic"],
                stale_after_hours=12,
            )
        )
    )

    assert card.metadata["sentiment_overlay_status"] == "stale"
    assert card.metadata["sentiment_overlay_points"] == 0.0
    assert card.metadata["base_aggregate_score"] == card.score.aggregate_score


def test_confidence_boundary_is_explicitly_upstream_evidence_limited() -> None:
    card = evaluate_qualification(_engine_input())

    confidence_reason = card.score.confidence_reason.casefold()
    assert "upstream evidence quality" in confidence_reason
    assert any(term in confidence_reason for term in ("aggregate", "component", "threshold", "evidence"))
    assert "does not imply live-trading approval" in card.rationale.final_explanation.casefold()


def test_expected_value_calculation_positive_zero_negative_cases() -> None:
    base_components = _base_component_scores()
    positive_win_rate = compute_bounded_win_rate(component_scores=base_components)
    positive_expected_value = compute_bounded_expected_value(
        component_scores=base_components,
        win_rate=positive_win_rate,
    )
    assert positive_expected_value > 0.0

    zero_components = [
        ComponentScore(
            category="signal_quality",
            score=50.0,
            rationale="Signal quality is neutral in bounded evidence space",
            evidence=["hit_rate=0.50"],
        ),
        ComponentScore(
            category="backtest_quality",
            score=50.0,
            rationale="Backtest quality is neutral in bounded evidence space",
            evidence=["profit_factor=1.00"],
        ),
        ComponentScore(
            category="portfolio_fit",
            score=70.0,
            rationale="Portfolio fit remains bounded for neutral EV check",
            evidence=["sector=0.20"],
        ),
        ComponentScore(
            category="risk_alignment",
            score=50.0,
            rationale="Risk alignment neutral for bounded EV check",
            evidence=["risk_trade=0.005"],
        ),
        ComponentScore(
            category="execution_readiness",
            score=50.0,
            rationale="Execution readiness neutral for bounded EV check",
            evidence=["slippage_bps=10"],
        ),
    ]
    zero_win_rate = compute_bounded_win_rate(component_scores=zero_components)
    zero_expected_value = compute_bounded_expected_value(
        component_scores=zero_components,
        win_rate=zero_win_rate,
    )
    assert zero_expected_value == 0.0

    negative_components = [
        ComponentScore(
            category="signal_quality",
            score=45.0,
            rationale="Signal quality weakens under bounded evidence assumptions",
            evidence=["hit_rate=0.45"],
        ),
        ComponentScore(
            category="backtest_quality",
            score=40.0,
            rationale="Backtest quality weakens under bounded evidence assumptions",
            evidence=["profit_factor=0.90"],
        ),
        ComponentScore(
            category="portfolio_fit",
            score=65.0,
            rationale="Portfolio fit remains bounded for negative EV check",
            evidence=["sector=0.22"],
        ),
        ComponentScore(
            category="risk_alignment",
            score=40.0,
            rationale="Risk alignment weakens under bounded evidence assumptions",
            evidence=["risk_trade=0.009"],
        ),
        ComponentScore(
            category="execution_readiness",
            score=40.0,
            rationale="Execution readiness weakens under bounded evidence assumptions",
            evidence=["slippage_bps=18"],
        ),
    ]
    negative_win_rate = compute_bounded_win_rate(component_scores=negative_components)
    negative_expected_value = compute_bounded_expected_value(
        component_scores=negative_components,
        win_rate=negative_win_rate,
    )
    assert negative_expected_value < 0.0


def test_decision_action_resolution_scenarios() -> None:
    hard_gate_failures = _base_hard_gates()
    hard_gate_failures[0] = HardGateResult(
        gate_id="drawdown_safety",
        status="fail",
        blocking=True,
        reason="Drawdown threshold breached",
        failure_reason="Max drawdown exceeded configured cap",
        evidence=["max_dd=0.15", "threshold=0.12"],
    )
    ignored = evaluate_qualification(_engine_input(hard_gates=hard_gate_failures))
    assert ignored.action == "ignore"

    weak_components = _base_component_scores()
    weak_components[0] = ComponentScore(
        category="signal_quality",
        score=52.0,
        rationale="Signal quality is insufficient for bounded confidence support",
        evidence=["hit_rate=0.52", "window=120d"],
    )
    weak_components[1] = ComponentScore(
        category="backtest_quality",
        score=53.0,
        rationale="Backtest quality is insufficient for bounded confidence support",
        evidence=["profit_factor=1.01", "window=120d"],
    )
    weak_components[4] = ComponentScore(
        category="execution_readiness",
        score=45.0,
        rationale="Execution readiness weakens expected evidence confidence",
        evidence=["slippage_bps=19", "commission=1.00"],
    )
    weak = evaluate_qualification(_engine_input(component_scores=weak_components))
    assert weak.qualification.state == "watch"
    assert weak.action == "ignore"

    positive = evaluate_qualification(_engine_input())
    assert positive.score.expected_value >= 0.0
    assert positive.action == "entry"

    exit_components = _base_component_scores()
    exit_components[0] = ComponentScore(
        category="signal_quality",
        score=66.0,
        rationale="Signal quality remains above watch threshold",
        evidence=["hit_rate=0.66", "window=120d"],
    )
    exit_components[1] = ComponentScore(
        category="backtest_quality",
        score=66.0,
        rationale="Backtest quality remains above watch threshold",
        evidence=["profit_factor=1.10", "window=120d"],
    )
    exit_components[2] = ComponentScore(
        category="portfolio_fit",
        score=70.0,
        rationale="Portfolio fit remains inside bounded threshold",
        evidence=["sector=0.19", "corr_cluster=0.44"],
    )
    exit_components[3] = ComponentScore(
        category="risk_alignment",
        score=30.0,
        rationale="Risk alignment weakens payoff assumptions",
        evidence=["risk_trade=0.010", "max_dd=0.14"],
    )
    exit_components[4] = ComponentScore(
        category="execution_readiness",
        score=20.0,
        rationale="Execution readiness weakens payoff assumptions",
        evidence=["slippage_bps=25", "commission=1.00"],
    )
    exiting = evaluate_qualification(_engine_input(component_scores=exit_components))
    assert exiting.qualification.state in {"watch", "paper_candidate"}
    assert exiting.score.expected_value < 0.0
    assert exiting.action == "exit"


def test_regression_identical_inputs_produce_identical_action_expected_value_and_win_rate() -> None:
    input_data = _engine_input()
    first = evaluate_qualification(input_data)
    second = evaluate_qualification(input_data)

    assert first.action == second.action
    assert first.score.expected_value == second.score.expected_value
    assert first.score.win_rate == second.score.win_rate
