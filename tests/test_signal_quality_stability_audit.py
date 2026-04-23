"""Tests for the bounded signal-quality stability audit contract."""

from __future__ import annotations

import pytest

from cilly_trading.engine.decision_card_contract import (
    SIGNAL_QUALITY_STABILITY_CONTRACT_ID,
    SIGNAL_QUALITY_STABILITY_CONTRACT_VERSION,
    SIGNAL_QUALITY_STABILITY_HIGH_THRESHOLD,
    SIGNAL_QUALITY_STABILITY_INTERPRETATION_BOUNDARY,
    SIGNAL_QUALITY_STABILITY_LOW_THRESHOLD,
    BoundedSignalQualityStabilityAudit,
    evaluate_bounded_signal_quality_stability_audit,
)


def _outcome(direction: str, *, status: str = "closed") -> dict[str, object]:
    return {
        "trade_id": "tr-1",
        "position_id": "pos-1",
        "symbol": "AAPL",
        "strategy_id": "RSI2",
        "trade_status": status,
        "opened_at_utc": "2026-04-01T08:05:00Z",
        "closed_at_utc": "2026-04-01T08:45:00Z" if status == "closed" else None,
        "outcome_direction": direction,
        "realized_pnl": "1.50" if direction == "favorable" else (
            "-1.50" if direction == "adverse" else "0.00" if direction == "flat" else None
        ),
        "unrealized_pnl": None,
        "outcome_summary": (
            "Matched paper trade closed for bounded signal-quality stability review."
        ),
    }


def _match_reference() -> dict[str, str]:
    return {"match_mode": "paper_trade_id", "paper_trade_id": "tr-1"}


# --- Contract constants ---------------------------------------------------


def test_contract_constants_are_declared() -> None:
    assert SIGNAL_QUALITY_STABILITY_CONTRACT_ID == "bounded_signal_quality_stability.paper_audit.v1"
    assert SIGNAL_QUALITY_STABILITY_CONTRACT_VERSION == "1.0.0"
    assert SIGNAL_QUALITY_STABILITY_HIGH_THRESHOLD == 70.0
    assert SIGNAL_QUALITY_STABILITY_LOW_THRESHOLD == 50.0
    for phrase in (
        "non-live",
        "trader validation",
        "profitability forecasting",
        "live-trading readiness",
        "operational readiness",
    ):
        assert phrase in SIGNAL_QUALITY_STABILITY_INTERPRETATION_BOUNDARY.casefold()


# --- Classification paths -------------------------------------------------


def test_matched_high_score_favorable_outcome_classifies_as_stable() -> None:
    audit = evaluate_bounded_signal_quality_stability_audit(
        covered_case_id="dc-001",
        signal_quality_score=88.0,
        match_status="matched",
        match_reference=_match_reference(),
        matched_outcome=_outcome("favorable"),
    )
    assert isinstance(audit, BoundedSignalQualityStabilityAudit)
    assert audit.contract_id == SIGNAL_QUALITY_STABILITY_CONTRACT_ID
    assert audit.contract_version == SIGNAL_QUALITY_STABILITY_CONTRACT_VERSION
    assert audit.stability_classification == "stable"
    assert audit.match_status == "matched"
    assert audit.matched_outcome is not None
    assert "non-live" in audit.interpretation_limit.casefold()


def test_matched_low_score_favorable_outcome_classifies_as_weak() -> None:
    audit = evaluate_bounded_signal_quality_stability_audit(
        covered_case_id="dc-002",
        signal_quality_score=65.0,
        match_status="matched",
        match_reference=_match_reference(),
        matched_outcome=_outcome("favorable"),
    )
    assert audit.stability_classification == "weak"


def test_matched_flat_outcome_classifies_as_weak() -> None:
    audit = evaluate_bounded_signal_quality_stability_audit(
        covered_case_id="dc-003",
        signal_quality_score=88.0,
        match_status="matched",
        match_reference=_match_reference(),
        matched_outcome=_outcome("flat"),
    )
    assert audit.stability_classification == "weak"


def test_matched_high_score_adverse_outcome_classifies_as_failing() -> None:
    audit = evaluate_bounded_signal_quality_stability_audit(
        covered_case_id="dc-004",
        signal_quality_score=85.0,
        match_status="matched",
        match_reference=_match_reference(),
        matched_outcome=_outcome("adverse"),
    )
    assert audit.stability_classification == "failing"


def test_matched_low_score_adverse_outcome_classifies_as_failing() -> None:
    audit = evaluate_bounded_signal_quality_stability_audit(
        covered_case_id="dc-005",
        signal_quality_score=40.0,
        match_status="matched",
        match_reference=_match_reference(),
        matched_outcome=_outcome("adverse"),
    )
    assert audit.stability_classification == "failing"


def test_matched_intermediate_score_adverse_outcome_classifies_as_weak() -> None:
    audit = evaluate_bounded_signal_quality_stability_audit(
        covered_case_id="dc-006",
        signal_quality_score=60.0,
        match_status="matched",
        match_reference=_match_reference(),
        matched_outcome=_outcome("adverse"),
    )
    assert audit.stability_classification == "weak"


def test_open_match_classifies_as_weak() -> None:
    audit = evaluate_bounded_signal_quality_stability_audit(
        covered_case_id="dc-007",
        signal_quality_score=88.0,
        match_status="open",
        match_reference=_match_reference(),
        matched_outcome=_outcome("open", status="open"),
    )
    assert audit.stability_classification == "weak"


def test_invalid_match_classifies_as_failing() -> None:
    audit = evaluate_bounded_signal_quality_stability_audit(
        covered_case_id="dc-008",
        signal_quality_score=88.0,
        match_status="invalid",
        match_reference=_match_reference(),
        matched_outcome=_outcome("invalid", status="closed"),
    )
    assert audit.stability_classification == "failing"


def test_missing_match_classifies_as_weak_and_excludes_outcome() -> None:
    audit = evaluate_bounded_signal_quality_stability_audit(
        covered_case_id="dc-009",
        signal_quality_score=88.0,
        match_status="missing",
    )
    assert audit.stability_classification == "weak"
    assert audit.matched_outcome is None
    assert audit.match_reference is None
    assert "no matched paper-trade evidence" in audit.stability_reason


# --- Determinism ----------------------------------------------------------


def test_audit_output_is_deterministic_for_identical_inputs() -> None:
    common = dict(
        covered_case_id="dc-detm",
        signal_quality_score=88.0,
        match_status="matched",
        match_reference=_match_reference(),
        matched_outcome=_outcome("favorable"),
    )
    first = evaluate_bounded_signal_quality_stability_audit(**common)
    second = evaluate_bounded_signal_quality_stability_audit(**common)
    assert first.model_dump() == second.model_dump()


# --- Validation -----------------------------------------------------------


def test_matched_status_requires_matched_outcome() -> None:
    with pytest.raises(ValueError):
        BoundedSignalQualityStabilityAudit(
            covered_case_id="dc-bad",
            signal_quality_score=88.0,
            match_reference=None,
            match_status="matched",
            matched_outcome=None,
            stability_classification="weak",
            stability_reason="placeholder reason long enough to satisfy validation",
            interpretation_limit=SIGNAL_QUALITY_STABILITY_INTERPRETATION_BOUNDARY,
        )


def test_missing_status_must_omit_matched_outcome() -> None:
    with pytest.raises(ValueError):
        evaluate_bounded_signal_quality_stability_audit(
            covered_case_id="dc-bad",
            signal_quality_score=88.0,
            match_status="missing",
            match_reference=None,
            matched_outcome=_outcome("favorable"),
        )


def test_interpretation_limit_must_keep_non_live_separation() -> None:
    with pytest.raises(ValueError):
        BoundedSignalQualityStabilityAudit(
            covered_case_id="dc-bad",
            signal_quality_score=88.0,
            match_reference=None,
            match_status="missing",
            matched_outcome=None,
            stability_classification="weak",
            stability_reason="placeholder reason long enough to satisfy validation",
            interpretation_limit="this string is long enough but lacks required boundary phrasing.",
        )
