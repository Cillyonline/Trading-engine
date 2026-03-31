"""Contract and semantic tests for SIG-P47 score semantics and cross-strategy comparability."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from cilly_trading.engine.decision_card_contract import (
    CONFIDENCE_TIER_PRECISION_DISCLAIMER,
    CROSS_STRATEGY_SCORE_COMPARABILITY_BOUNDARY,
    ComponentScore,
    HardGateResult,
)
from cilly_trading.engine.qualification_engine import (
    QualificationEngineInput,
    assign_confidence_tier,
    compute_aggregate_score,
    evaluate_qualification,
)
from cilly_trading.strategies.registry import (
    CROSS_STRATEGY_SCORE_NON_COMPARABILITY_NOTE,
    get_registered_strategy_metadata,
    reset_registry,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
GOVERNANCE_DOC = REPO_ROOT / "docs" / "governance" / "score-semantics-cross-strategy.md"
PHASE_DOC = REPO_ROOT / "docs" / "phases" / "sig-p47-score-semantics-cross-strategy.md"


# ---------------------------------------------------------------------------
# Constants contract tests
# ---------------------------------------------------------------------------


def test_cross_strategy_score_comparability_boundary_constant_is_defined() -> None:
    assert isinstance(CROSS_STRATEGY_SCORE_COMPARABILITY_BOUNDARY, str)
    assert len(CROSS_STRATEGY_SCORE_COMPARABILITY_BOUNDARY) > 0
    assert "not directly comparable" in CROSS_STRATEGY_SCORE_COMPARABILITY_BOUNDARY
    assert "comparison group" in CROSS_STRATEGY_SCORE_COMPARABILITY_BOUNDARY
    assert "within-strategy" in CROSS_STRATEGY_SCORE_COMPARABILITY_BOUNDARY


def test_confidence_tier_precision_disclaimer_constant_is_defined() -> None:
    assert isinstance(CONFIDENCE_TIER_PRECISION_DISCLAIMER, str)
    assert len(CONFIDENCE_TIER_PRECISION_DISCLAIMER) > 0
    assert "ordinal classification" in CONFIDENCE_TIER_PRECISION_DISCLAIMER
    assert "not" in CONFIDENCE_TIER_PRECISION_DISCLAIMER
    assert "precise probability" in CONFIDENCE_TIER_PRECISION_DISCLAIMER
    assert "across strategies" in CONFIDENCE_TIER_PRECISION_DISCLAIMER


def test_registry_cross_strategy_note_constant_is_defined() -> None:
    assert isinstance(CROSS_STRATEGY_SCORE_NON_COMPARABILITY_NOTE, str)
    assert len(CROSS_STRATEGY_SCORE_NON_COMPARABILITY_NOTE) > 0
    assert "not supported" in CROSS_STRATEGY_SCORE_NON_COMPARABILITY_NOTE
    assert "comparison_group" in CROSS_STRATEGY_SCORE_NON_COMPARABILITY_NOTE
    assert "within-strategy" in CROSS_STRATEGY_SCORE_NON_COMPARABILITY_NOTE


# ---------------------------------------------------------------------------
# Registry metadata alignment tests
# ---------------------------------------------------------------------------


def test_default_registry_strategies_have_distinct_comparison_groups() -> None:
    metadata = get_registered_strategy_metadata()
    comparison_groups = {key: meta["comparison_group"] for key, meta in metadata.items()}

    assert "REFERENCE" in comparison_groups
    assert "RSI2" in comparison_groups
    assert "TURTLE" in comparison_groups

    # Each default strategy must have a defined comparison group
    for key, group in comparison_groups.items():
        assert isinstance(group, str) and group.strip(), (
            f"Strategy {key} must have a non-empty comparison_group"
        )

    # RSI2 and TURTLE are in different comparison groups (not cross-comparable by design)
    assert comparison_groups["RSI2"] != comparison_groups["TURTLE"], (
        "RSI2 and TURTLE are in different comparison groups and are not directly comparable"
    )


def test_reference_strategy_is_in_reference_control_group() -> None:
    metadata = get_registered_strategy_metadata()
    assert metadata["REFERENCE"]["comparison_group"] == "reference-control"


def test_rsi2_is_in_mean_reversion_group() -> None:
    metadata = get_registered_strategy_metadata()
    assert metadata["RSI2"]["comparison_group"] == "mean-reversion"


def test_turtle_is_in_trend_following_group() -> None:
    metadata = get_registered_strategy_metadata()
    assert metadata["TURTLE"]["comparison_group"] == "trend-following"


# ---------------------------------------------------------------------------
# Qualification engine precision tests
# ---------------------------------------------------------------------------


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


def _engine_input(**kwargs) -> QualificationEngineInput:
    return QualificationEngineInput(
        decision_card_id="dc_sig_p47_AAPL_RSI2",
        generated_at_utc="2026-03-24T08:10:00Z",
        symbol="AAPL",
        strategy_id="RSI2",
        hard_gates=kwargs.get("hard_gates", _base_hard_gates()),
        component_scores=kwargs.get("component_scores", _base_component_scores()),
        metadata={"analysis_run_id": "run_sig_p47"},
    )


@pytest.mark.parametrize("tier", ["high", "medium", "low"])
def test_confidence_reason_references_ordinal_classification_for_all_tiers(tier: str) -> None:
    """Confidence reason must state ordinal classification for every confidence tier."""
    components = _base_component_scores()
    if tier == "medium":
        components[0] = ComponentScore(
            category="signal_quality",
            score=62.0,
            rationale=components[0].rationale,
            evidence=components[0].evidence,
        )
        components[4] = ComponentScore(
            category="execution_readiness",
            score=55.0,
            rationale=components[4].rationale,
            evidence=components[4].evidence,
        )
    elif tier == "low":
        components[4] = ComponentScore(
            category="execution_readiness",
            score=42.0,
            rationale=components[4].rationale,
            evidence=components[4].evidence,
        )

    card = evaluate_qualification(_engine_input(component_scores=components))

    assert card.score.confidence_tier == tier
    assert "ordinal classification" in card.score.confidence_reason
    assert "not" in card.score.confidence_reason
    assert "precise probability" in card.score.confidence_reason


def test_confidence_reason_does_not_claim_cross_strategy_score_equality() -> None:
    card = evaluate_qualification(_engine_input())

    # Must not imply that the score means the same thing across different strategies
    reason_lower = card.score.confidence_reason.casefold()
    assert "live trading" not in reason_lower
    assert "production" not in reason_lower
    assert "guaranteed" not in reason_lower


def test_confidence_reason_passes_contract_validation() -> None:
    """Verify generated confidence reasons satisfy the contract evidence-term requirement."""
    card = evaluate_qualification(_engine_input())

    reason = card.score.confidence_reason.casefold()
    required_terms = ("aggregate", "component", "threshold", "evidence")
    assert any(term in reason for term in required_terms), (
        "confidence_reason must reference at least one bounded evidence term"
    )


# ---------------------------------------------------------------------------
# Governance doc tests
# ---------------------------------------------------------------------------


def test_score_semantics_governance_doc_defines_comparability_boundaries() -> None:
    content = GOVERNANCE_DOC.read_text(encoding="utf-8")

    assert content.startswith("# Score Semantics and Cross-Strategy Comparability")
    assert "What Cross-Strategy Score Comparison Does and Does Not Mean" in content
    assert "not directly comparable" in content
    assert "comparison group" in content
    assert "ordinal classification" in content
    assert "does not represent" in content.casefold() or "do not represent" in content.casefold()


def test_score_semantics_governance_doc_defines_precision_boundaries() -> None:
    content = GOVERNANCE_DOC.read_text(encoding="utf-8")

    assert "Score Precision Boundaries" in content
    assert "bounded weighted composite" in content
    assert "precise probability" in content
    assert "CROSS_STRATEGY_SCORE_COMPARABILITY_BOUNDARY" in content
    assert "CONFIDENCE_TIER_PRECISION_DISCLAIMER" in content


def test_score_semantics_governance_doc_defines_non_goals() -> None:
    content = GOVERNANCE_DOC.read_text(encoding="utf-8")

    assert "Non-Goals" in content
    assert "live trading approval" in content


# ---------------------------------------------------------------------------
# Phase doc tests
# ---------------------------------------------------------------------------


def test_sig_p47_phase_doc_defines_scope_and_enforcement_surfaces() -> None:
    content = PHASE_DOC.read_text(encoding="utf-8")

    assert content.startswith("# SIG-P47 - Score Semantics and Cross-Strategy Comparability")
    assert "not directly comparable" in content
    assert "ordinal classification" in content
    assert "CROSS_STRATEGY_SCORE_COMPARABILITY_BOUNDARY" in content
    assert "CONFIDENCE_TIER_PRECISION_DISCLAIMER" in content
    assert "CROSS_STRATEGY_SCORE_NON_COMPARABILITY_NOTE" in content
    assert "src/cilly_trading/engine/decision_card_contract.py" in content
    assert "src/cilly_trading/strategies/registry.py" in content
    assert "tests/test_sig_p47_score_semantics.py" in content


def test_sig_p47_phase_doc_lists_out_of_scope_reminders() -> None:
    content = PHASE_DOC.read_text(encoding="utf-8")

    assert "Out-of-Scope" in content
    assert "live trading" in content
    assert "new strategies" in content
