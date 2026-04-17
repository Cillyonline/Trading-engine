"""Contract tests for P56: bounded signal-quality validation."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from api.services.analysis_service import build_ranked_symbol_results
from cilly_trading.engine.decision_card_contract import (
    DECISION_CARD_CONTRACT_VERSION,
    validate_decision_card,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_DOC = REPO_ROOT / "docs" / "governance" / "signal-quality-bounded-contract.md"


def _signal(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "symbol": "AAPL",
        "strategy": "RSI2",
        "stage": "setup",
        "score": 50.0,
        "signal_strength": 0.5,
        "timeframe": "D1",
        "market_type": "stock",
    }
    base.update(overrides)
    return base


def test_p56_ranking_is_deterministic_for_defined_fixture_ordering() -> None:
    signals = [
        _signal(symbol="BBB", score=60.0, signal_strength=0.4),
        _signal(symbol="AAA", score=60.0, signal_strength=0.7),
        _signal(symbol="AAC", score=60.0, signal_strength=0.7),
        _signal(symbol="DDD", score=95.0, signal_strength=0.2),
        _signal(symbol="EEE", score=20.0, signal_strength=0.9),
    ]

    ranked = build_ranked_symbol_results(signals, min_score=30.0)
    assert [item.symbol for item in ranked] == ["DDD", "AAA", "AAC", "BBB"]


def test_p56_ranking_is_stable_for_permuted_input_fixture() -> None:
    fixture_a = [
        _signal(symbol="BBB", score=60.0, signal_strength=0.4),
        _signal(symbol="AAA", score=60.0, signal_strength=0.7),
        _signal(symbol="AAC", score=60.0, signal_strength=0.7),
        _signal(symbol="DDD", score=95.0, signal_strength=0.2),
    ]
    fixture_b = list(reversed(fixture_a))

    ranked_a = build_ranked_symbol_results(fixture_a, min_score=30.0)
    ranked_b = build_ranked_symbol_results(fixture_b, min_score=30.0)

    assert [item.symbol for item in ranked_a] == [item.symbol for item in ranked_b]
    assert [item.score for item in ranked_a] == [item.score for item in ranked_b]
    assert [item.signal_strength for item in ranked_a] == [item.signal_strength for item in ranked_b]


def test_p56_selectivity_respects_min_score_boundary_for_supported_numeric_scores() -> None:
    signals = [
        _signal(symbol="A", score=44.9),
        _signal(symbol="B", score=45.0),
        _signal(symbol="C", score=80.0),
    ]

    ranked = build_ranked_symbol_results(signals, min_score=45.0)

    assert [item.symbol for item in ranked] == ["C", "B"]


def test_p56_weak_or_low_information_cases_are_bounded_where_supported() -> None:
    signals = [
        _signal(symbol="", score=99.0, signal_strength=1.0),
        _signal(symbol="NO_SETUP", stage="entry", score=99.0, signal_strength=1.0),
        _signal(symbol="NO_SCORE", score=None, signal_strength=0.4),
        _signal(symbol="TEXT_SCORE", score="n/a", signal_strength=0.4),
        _signal(symbol="VALID", score=55.0, signal_strength=0.2),
    ]

    ranked = build_ranked_symbol_results(signals, min_score=30.0)

    assert [item.symbol for item in ranked] == ["VALID"]


def test_p56_contract_doc_is_bounded_and_no_trader_readiness_claim() -> None:
    content = CONTRACT_DOC.read_text(encoding="utf-8")

    assert content.startswith("# P56 Signal Quality - Bounded Validation Contract")
    assert "Deterministic ranking behavior under defined fixtures" in content
    assert "Selectivity boundary for low-information candidates" in content
    assert "Stability boundary under equivalent fixture content" in content
    assert "Classification: technically good, traderically weak" in content
    assert "does not claim trader readiness" in content
    assert "no live-trading readiness, execution approval, or profitability guarantee" in content
    assert "bounded win-rate formula" in content
    assert "bounded expected-value formula" in content
    assert "deterministic paper-evaluation action" in content


def _decision_card_payload_with_confidence_reason(confidence_reason: str) -> dict[str, object]:
    return {
        "contract_version": DECISION_CARD_CONTRACT_VERSION,
        "decision_card_id": "dc_20260417_AAPL_RSI2",
        "generated_at_utc": "2026-04-17T10:00:00Z",
        "symbol": "AAPL",
        "strategy_id": "RSI2",
        "hard_gates": {
            "policy_version": "hard-gates.v1",
            "gates": [
                {
                    "gate_id": "drawdown_safety",
                    "status": "pass",
                    "blocking": True,
                    "reason": "Drawdown remains below configured threshold",
                    "evidence": ["max_dd=0.08", "threshold=0.12"],
                }
            ],
        },
        "score": {
            "component_scores": [
                {
                    "category": "signal_quality",
                    "score": 84.0,
                    "rationale": "Signal quality remains stable across deterministic windows",
                    "evidence": ["hit_rate=0.62", "window_days=90"],
                },
                {
                    "category": "backtest_quality",
                    "score": 82.0,
                    "rationale": "Backtest quality remains stable in deterministic replay",
                    "evidence": ["sharpe=1.36", "profit_factor=1.58"],
                },
                {
                    "category": "portfolio_fit",
                    "score": 78.0,
                    "rationale": "Portfolio fit remains bounded under concentration limits",
                    "evidence": ["sector_weight=0.19", "corr_cluster=0.43"],
                },
                {
                    "category": "risk_alignment",
                    "score": 86.0,
                    "rationale": "Risk alignment remains bounded under policy controls",
                    "evidence": ["risk_trade=0.005", "max_dd=0.10"],
                },
                {
                    "category": "execution_readiness",
                    "score": 76.0,
                    "rationale": "Execution readiness remains bounded with explicit assumptions",
                    "evidence": ["slippage_bps=9", "commission=1.00"],
                },
            ],
            "confidence_tier": "high",
            "confidence_reason": confidence_reason,
            "aggregate_score": 80.5,
            "win_rate": 0.61,
            "expected_value": 0.1281,
        },
        "action": "entry",
        "qualification": {
            "state": "paper_approved",
            "color": "green",
            "summary": "Opportunity is approved for bounded paper-trading only.",
        },
        "rationale": {
            "summary": "Hard gates pass and bounded component evidence supports deterministic qualification",
            "gate_explanations": ["Gate drawdown_safety passed with explicit bounded evidence."],
            "score_explanations": ["Bounded deterministic score evidence is complete for this decision card."],
            "final_explanation": (
                "Decision action and qualification are deterministic technical implementation evidence "
                "and do not imply live-trading approval."
            ),
        },
        "metadata": {
            "technical_implementation_status": "technical_in_progress",
            "trader_validation_status": "trader_validation_not_started",
        },
    }


@pytest.mark.parametrize("phrase", ["trader validation", "live approval", "production readiness"])
def test_p56_contract_rejects_unsupported_claim_wording_in_decision_output(phrase: str) -> None:
    payload = _decision_card_payload_with_confidence_reason(
        f"Aggregate component threshold evidence is bounded and excludes {phrase}."
    )

    with pytest.raises(ValidationError, match="unsupported claim language"):
        validate_decision_card(payload)
