from __future__ import annotations

from cilly_trading.engine.decision_card_contract import ComponentScore, HardGateResult
from cilly_trading.engine.qualification_engine import (
    BacktestEvidenceInput,
    PortfolioFitInput,
    QualificationEngineInput,
    SENTIMENT_OVERLAY_MAX_POINTS,
    SentimentOverlayInput,
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
    backtest_evidence: BacktestEvidenceInput | None = None,
    portfolio_fit_input: PortfolioFitInput | None = None,
    sentiment_overlay: SentimentOverlayInput | None = None,
) -> QualificationEngineInput:
    return QualificationEngineInput(
        decision_card_id="dc_20260329_AAPL_RSI2",
        generated_at_utc="2026-03-29T10:00:00Z",
        symbol="AAPL",
        strategy_id="RSI2",
        hard_gates=_base_hard_gates(),
        component_scores=_base_component_scores(),
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
    assert "does not imply live-trading approval" in card.rationale.final_explanation.casefold()
    assert [component.category for component in card.score.component_scores] == [
        "backtest_quality",
        "execution_readiness",
        "portfolio_fit",
        "risk_alignment",
        "signal_quality",
    ]


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
