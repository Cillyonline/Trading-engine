from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from cilly_trading.engine.decision_card_contract import (
    DECISION_CARD_CONTRACT_VERSION,
    DecisionCard,
    serialize_decision_card,
    validate_decision_card,
)


def _valid_payload(*, qualification_state: str = "paper_approved", qualification_color: str = "green") -> dict[str, Any]:
    return {
        "contract_version": DECISION_CARD_CONTRACT_VERSION,
        "decision_card_id": "dc_20260324_AAPL_RSI2",
        "generated_at_utc": "2026-03-24T08:10:00Z",
        "symbol": "AAPL",
        "strategy_id": "RSI2",
        "hard_gates": {
            "policy_version": "hard-gates.v1",
            "gates": [
                {
                    "gate_id": "portfolio_exposure_cap",
                    "status": "pass",
                    "blocking": True,
                    "reason": "Gross exposure remains under policy cap",
                    "evidence": ["gross_exposure_pct=0.42", "policy_cap=0.60"],
                },
                {
                    "gate_id": "drawdown_safety",
                    "status": "pass",
                    "blocking": True,
                    "reason": "Drawdown guard remains within threshold",
                    "evidence": ["max_drawdown_pct=0.07", "threshold_pct=0.12"],
                },
            ],
        },
        "score": {
            "component_scores": [
                {
                    "category": "execution_readiness",
                    "score": 78.0,
                    "rationale": "Execution assumptions remain deterministic and bounded",
                    "evidence": ["slippage_bps=10", "commission_per_order=1.00"],
                },
                {
                    "category": "portfolio_fit",
                    "score": 76.0,
                    "rationale": "Portfolio concentration constraints remain satisfied",
                    "evidence": ["sector_weight_pct=0.19", "sector_limit_pct=0.25"],
                },
                {
                    "category": "signal_quality",
                    "score": 82.0,
                    "rationale": "Signal quality remains consistent across recent windows",
                    "evidence": ["signal_hit_rate=0.61", "window_days=90"],
                },
                {
                    "category": "backtest_quality",
                    "score": 74.0,
                    "rationale": "Backtest quality supports bounded forward expectation",
                    "evidence": ["sharpe=1.34", "profit_factor=1.52"],
                },
                {
                    "category": "risk_alignment",
                    "score": 85.0,
                    "rationale": "Risk controls align with per-trade and portfolio policy",
                    "evidence": ["risk_per_trade_pct=0.005", "max_risk_pct=0.01"],
                },
            ],
            "confidence_tier": "high",
            "confidence_reason": "Aggregate score and component thresholds support high confidence with explicit evidence.",
            "aggregate_score": 79.0,
        },
        "qualification": {
            "state": qualification_state,
            "color": qualification_color,
            "summary": "Opportunity is bounded to paper-trading review and execution scope.",
        },
        "rationale": {
            "summary": "Hard gates pass and bounded component scores support qualification",
            "gate_explanations": [
                "Hard-gate checks passed under the current policy baseline",
            ],
            "score_explanations": [
                "Component scores are bounded and represent distinct evaluation axes",
            ],
            "final_explanation": (
                "Qualification is explicit and not derived from a single opaque score, "
                "and does not imply live-trading approval."
            ),
        },
        "metadata": {
            "analysis_run_id": "run_20260324_0810",
            "source": "deterministic_pipeline",
            "universe": "us_equities",
        },
    }


def test_decision_card_model_validation_representative_payload() -> None:
    card = validate_decision_card(_valid_payload())

    assert isinstance(card, DecisionCard)
    assert card.contract_version == DECISION_CARD_CONTRACT_VERSION
    assert card.hard_gates.has_blocking_failure is False
    assert card.score.aggregate_score == 79.0
    assert [component.category for component in card.score.component_scores] == [
        "backtest_quality",
        "execution_readiness",
        "portfolio_fit",
        "risk_alignment",
        "signal_quality",
    ]


def test_decision_card_serialization_is_deterministic() -> None:
    payload = _valid_payload()
    card_a = validate_decision_card(payload)
    card_b = validate_decision_card(payload)

    serialized_a = serialize_decision_card(card_a)
    serialized_b = serialize_decision_card(card_b)
    assert serialized_a == serialized_b
    assert serialized_a == card_a.to_canonical_json()
    assert f'"contract_version":"{DECISION_CARD_CONTRACT_VERSION}"' in serialized_a


def test_negative_validation_rejects_missing_component_category() -> None:
    payload = _valid_payload()
    payload["score"]["component_scores"] = payload["score"]["component_scores"][:-1]

    with pytest.raises(ValidationError, match="Component score categories must match required set"):
        validate_decision_card(payload)


def test_negative_validation_rejects_gate_fail_without_failure_reason() -> None:
    payload = _valid_payload(qualification_state="reject", qualification_color="red")
    payload["hard_gates"]["gates"][0]["status"] = "fail"
    payload["hard_gates"]["gates"][0]["failure_reason"] = None

    with pytest.raises(ValidationError, match="must define failure_reason"):
        validate_decision_card(payload)


def test_negative_validation_rejects_non_rejected_state_on_blocking_failure() -> None:
    payload = _valid_payload(qualification_state="watch", qualification_color="yellow")
    payload["hard_gates"]["gates"][0]["status"] = "fail"
    payload["hard_gates"]["gates"][0]["failure_reason"] = "Exposure cap would be exceeded"

    with pytest.raises(
        ValidationError,
        match="Blocking hard-gate failures require reject qualification state",
    ):
        validate_decision_card(payload)


@pytest.mark.parametrize(
    ("state", "color"),
    [
        ("paper_approved", "green"),
        ("paper_candidate", "yellow"),
        ("watch", "yellow"),
        ("reject", "red"),
    ],
)
def test_representative_qualification_payloads_validate(state: str, color: str) -> None:
    payload = _valid_payload(qualification_state=state, qualification_color=color)
    if state == "reject":
        payload["hard_gates"]["gates"][0]["status"] = "fail"
        payload["hard_gates"]["gates"][0]["failure_reason"] = "Risk cap breach"
        payload["qualification"]["summary"] = (
            "Opportunity is rejected for paper-trading because a blocking gate failed."
        )
    if state == "watch":
        payload["score"]["confidence_tier"] = "low"
        payload["score"]["confidence_reason"] = (
            "Aggregate score or component threshold evidence is below medium confidence."
        )
        payload["qualification"]["summary"] = (
            "Opportunity requires further evidence before paper-trading qualification."
        )

    card = validate_decision_card(payload)
    assert card.qualification.state == state
    assert card.qualification.color == color


def test_no_competing_decision_card_model_exists() -> None:
    root = Path(__file__).resolve().parents[3]
    model_files = sorted(root.glob("src/cilly_trading/**/*decision*card*.py"))

    assert [path.relative_to(root).as_posix() for path in model_files] == [
        "src/cilly_trading/engine/decision_card_contract.py"
    ]


def test_negative_validation_rejects_confidence_reason_without_evidence_terms() -> None:
    payload = _valid_payload()
    payload["score"]["confidence_reason"] = "High confidence from broad stability."

    with pytest.raises(ValidationError, match="confidence_reason must reference bounded evidence terms"):
        validate_decision_card(payload)


def test_negative_validation_rejects_unsupported_confidence_claim_phrase() -> None:
    payload = _valid_payload()
    payload["score"]["confidence_reason"] = "Aggregate evidence is strong and outcome is guaranteed."

    with pytest.raises(ValidationError, match="confidence_reason contains unsupported claim language"):
        validate_decision_card(payload)


def test_negative_validation_rejects_qualification_summary_outside_paper_scope() -> None:
    payload = _valid_payload()
    payload["qualification"]["summary"] = "Opportunity is production ready for paper-trading execution."

    with pytest.raises(ValidationError, match="qualification.summary contains unsupported claim language"):
        validate_decision_card(payload)


def test_negative_validation_requires_final_explanation_live_trading_boundary() -> None:
    payload = _valid_payload()
    payload["rationale"]["final_explanation"] = "Qualification is explicit and deterministic."

    with pytest.raises(
        ValidationError,
        match="must explicitly state that output does not imply live-trading approval",
    ):
        validate_decision_card(payload)
