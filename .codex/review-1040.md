# Review Package - Issue #1040

## SUMMARY
- Acceptance Criterion 1: Added one deterministic bounded confidence-calibration contract in `src/cilly_trading/engine/decision_card_contract.py` that relates covered `confidence_tier` to covered backtest-realism evidence status and matched paper outcomes.
- Acceptance Criterion 2: The new audit classifies confidence behavior explicitly as `stable`, `weak`, or `failing`, and preserves explicit missing-evidence handling as weak bounded interpretation.
- Acceptance Criterion 3: Determinism is enforced by pure classification functions and regression tests for identical inputs plus API determinism checks.
- Acceptance Criterion 4: Existing execution behavior remains unchanged; the change only adds read-surface metadata and contract logic.
- Acceptance Criterion 5: Documentation and tests keep non-live, non-profitability, and no-readiness boundaries explicit in both constants and governance docs.

## MODIFIED FILES
- src\cilly_trading\engine\decision_card_contract.py
- src\api\services\paper_inspection_service.py
- src\api\services\inspection_service.py
- tests\cilly_trading\engine\test_decision_card_contract.py
- tests\test_api_decision_card_inspection_read.py
- tests\test_sig_p47_score_semantics.py
- docs\governance\signal-quality-bounded-contract.md

## NEW FILES
- None

## FILE CONTENTS
### src\cilly_trading\engine\decision_card_contract.py
```
"""Canonical decision-card contract with hard gates and score semantics."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

DECISION_CARD_CONTRACT_VERSION = "2.0.0"
BOUNDED_TRADER_RELEVANCE_CONTRACT_ID = "bounded_trader_relevance.paper_review.v1"
BOUNDED_TRADER_RELEVANCE_CONTRACT_VERSION = "1.0.0"
QUALIFICATION_MEDIUM_AGGREGATE_THRESHOLD = 60.0
QUALIFICATION_HIGH_AGGREGATE_THRESHOLD = 80.0
ACTION_EXIT_WIN_RATE_MAX = 0.50
ACTION_ENTRY_WIN_RATE_MIN = 0.55

CROSS_STRATEGY_SCORE_COMPARABILITY_BOUNDARY = (
    "Decision-card scores are bounded to within-strategy evaluation for a single opportunity. "
    "Cross-strategy score comparison is not supported; aggregate scores and component scores "
    "from strategies in different comparison groups are not directly comparable."
)

CONFIDENCE_TIER_PRECISION_DISCLAIMER = (
    "Confidence tier is an ordinal classification (low/medium/high) derived from bounded thresholds "
    "and is limited by upstream evidence quality. "
    "It does not imply precise probability, forecast accuracy, or score equality across strategies."
)

UPSTREAM_EVIDENCE_QUALITY_CONFIDENCE_BOUND = (
    "Confidence is bounded by the quality of upstream evidence "
    "(signal, backtest, portfolio-fit, risk) provided to the qualification engine; "
    "limited or low-quality upstream evidence limits confidence regardless of thresholds."
)

QUALIFICATION_PROFILE_ROBUSTNESS_CONTRACT_ID = "qualification_profile_robustness.paper_audit.v1"
QUALIFICATION_PROFILE_ROBUSTNESS_CONTRACT_VERSION = "1.0.0"
QUALIFICATION_PROFILE_ROBUSTNESS_INTERPRETATION_BOUNDARY = (
    "Qualification-profile robustness audit is bounded to deterministic covered, failure-envelope, "
    "and regime slices. Weak or failing slices limit interpretation outside covered conditions and "
    "do not expand live-trading approval, paper profitability, or trader_validation claims."
)
DECISION_TO_PAPER_USEFULNESS_CONTRACT_ID = (
    "decision_evidence_to_paper_outcome_usefulness.paper_audit.v1"
)
DECISION_TO_PAPER_USEFULNESS_CONTRACT_VERSION = "1.0.0"
DECISION_TO_PAPER_USEFULNESS_INTERPRETATION_BOUNDARY = (
    "Decision-to-paper usefulness audit is bounded to non-live explanatory value for covered entry "
    "decisions with explicit paper_trade_id matches. It does not imply trader validation, "
    "profitability forecasting, live-trading readiness, or operational readiness."
)

SIGNAL_QUALITY_STABILITY_CONTRACT_ID = (
    "bounded_signal_quality_stability.paper_audit.v1"
)
SIGNAL_QUALITY_STABILITY_CONTRACT_VERSION = "1.0.0"
SIGNAL_QUALITY_STABILITY_INTERPRETATION_BOUNDARY = (
    "Bounded signal-quality stability audit is bounded to non-live deterministic comparison between "
    "covered decision-card signal-quality evidence and matched paper-trade outcomes. It does not "
    "imply trader validation, profitability forecasting, live-trading readiness, or operational "
    "readiness."
)
SIGNAL_QUALITY_STABILITY_HIGH_THRESHOLD = 70.0
SIGNAL_QUALITY_STABILITY_LOW_THRESHOLD = 50.0
CONFIDENCE_CALIBRATION_CONTRACT_ID = (
    "bounded_confidence_calibration.realism_to_paper.paper_audit.v1"
)
CONFIDENCE_CALIBRATION_CONTRACT_VERSION = "1.0.0"
CONFIDENCE_CALIBRATION_INTERPRETATION_BOUNDARY = (
    "Bounded confidence calibration audit is limited to non-live deterministic interpretation of "
    "decision-card confidence tier against covered backtest-realism evidence completeness and "
    "matched paper-trade outcomes. It does not imply trader validation, profitability forecasting, "
    "live-trading readiness, or operational readiness."
)

END_TO_END_TRACEABILITY_CONTRACT_ID = (
    "signal_to_paper_reconciliation_traceability.paper_audit.v1"
)
END_TO_END_TRACEABILITY_CONTRACT_VERSION = "1.0.0"
END_TO_END_TRACEABILITY_INTERPRETATION_BOUNDARY = (
    "End-to-end traceability chain is bounded to non-live deterministic auditability across "
    "signal/analysis, decision-card, paper-trade, and reconciliation surfaces. It does not imply "
    "trader validation, profitability forecasting, live-trading readiness, or operational readiness."
)
END_TO_END_TRACEABILITY_RECONCILIATION_SURFACE = "/paper/reconciliation"
END_TO_END_TRACEABILITY_DECISION_SURFACE = "/decision-cards"
END_TO_END_TRACEABILITY_PAPER_SURFACE = "/paper/trades"
END_TO_END_TRACEABILITY_SIGNAL_SURFACE = "/signals"

DecisionComponentCategory = Literal[
    "signal_quality",
    "backtest_quality",
    "portfolio_fit",
    "risk_alignment",
    "execution_readiness",
]
DecisionConfidenceTier = Literal["low", "medium", "high"]
HardGateStatus = Literal["pass", "fail"]
QualificationState = Literal["reject", "watch", "paper_candidate", "paper_approved"]
QualificationColor = Literal["green", "yellow", "red"]
DecisionAction = Literal["entry", "exit", "ignore"]
PaperReviewCaseId = Literal[
    "qualification_state_relevance",
    "decision_action_relevance",
    "boundary_scope_relevance",
]
TraderRelevanceEvidenceStatus = Literal["aligned", "weak", "missing"]
QualificationProfileRobustnessStatus = Literal["stable", "weak", "failing"]
QualificationProfileRobustnessSliceType = Literal["covered", "failure_envelope", "regime_slice"]
DecisionToPaperUsefulnessClassification = Literal["explanatory", "weak", "misleading"]
DecisionToPaperUsefulnessMatchStatus = Literal["matched", "open", "missing", "invalid"]
DecisionToPaperUsefulnessMatchMode = Literal["paper_trade_id"]
PaperTradeOutcomeDirection = Literal["favorable", "flat", "adverse", "open", "invalid"]
SignalQualityStabilityClassification = Literal["stable", "weak", "failing"]
BacktestRealismCalibrationStatus = Literal["stable", "weak", "failing", "missing"]
ConfidenceCalibrationClassification = Literal["stable", "weak", "failing"]

REQUIRED_COMPONENT_CATEGORIES: tuple[DecisionComponentCategory, ...] = (
    "signal_quality",
    "backtest_quality",
    "portfolio_fit",
    "risk_alignment",
    "execution_readiness",
)

QUALIFICATION_COLOR_BY_STATE: dict[QualificationState, QualificationColor] = {
    "reject": "red",
    "watch": "yellow",
    "paper_candidate": "yellow",
    "paper_approved": "green",
}

EVIDENCE_CONFIDENCE_REQUIRED_TERMS: tuple[str, ...] = (
    "aggregate",
    "component",
    "threshold",
    "evidence",
)

CLAIM_BOUNDARY_FORBIDDEN_PHRASES: tuple[str, ...] = (
    "live trading ready",
    "live-trading ready",
    "live trading approval",
    "production ready",
    "production-approved",
    "broker execution ready",
    "broker-ready",
    "trader validated",
    "trader-validated",
    "trader validation",
    "guaranteed",
    "guarantee",
    "certain outcome",
    "high certainty",
    "confirmed opportunity",
    "validated outcome",
    "strong certainty",
    "live approval",
    "production readiness",
)

PAPER_REVIEW_CASE_DEFINITIONS: dict[PaperReviewCaseId, dict[str, Any]] = {
    "qualification_state_relevance": {
        "review_question": (
            "Does the output expose deterministic evidence that explains why the qualification state was resolved?"
        ),
        "required_evidence": (
            "qualification_state",
            "paper_scope_summary",
            "state_explanation_evidence",
        ),
    },
    "decision_action_relevance": {
        "review_question": (
            "Does the output expose deterministic evidence that explains why action is entry/exit/ignore?"
        ),
        "required_evidence": (
            "action",
            "bounded_decision_metrics",
            "action_rule_trace",
        ),
    },
    "boundary_scope_relevance": {
        "review_question": (
            "Does the output explicitly keep bounded trader-relevance validation separate from trader_validation, "
            "paper profitability, and live-readiness claims?"
        ),
        "required_evidence": (
            "trader_validation_boundary",
            "paper_profitability_boundary",
            "live_readiness_boundary",
        ),
    },
}


def _qualification_thresholds_from_metadata(metadata: dict[str, Any]) -> tuple[float, float]:
    """Resolve qualification aggregate thresholds from metadata fallback to contract defaults."""
    thresholds = metadata.get("qualification_thresholds")
    if not isinstance(thresholds, dict):
        return QUALIFICATION_MEDIUM_AGGREGATE_THRESHOLD, QUALIFICATION_HIGH_AGGREGATE_THRESHOLD
    medium = thresholds.get("medium_aggregate")
    high = thresholds.get("high_aggregate")
    try:
        medium_value = float(medium)
        high_value = float(high)
    except (TypeError, ValueError):
        return QUALIFICATION_MEDIUM_AGGREGATE_THRESHOLD, QUALIFICATION_HIGH_AGGREGATE_THRESHOLD
    return medium_value, high_value


def _contains_forbidden_claim_phrase(value: str) -> str | None:
    normalized = value.casefold()
    for phrase in CLAIM_BOUNDARY_FORBIDDEN_PHRASES:
        if phrase in normalized:
            return phrase
    return None


def _derive_bounded_win_rate_from_components(component_scores: list[dict[str, Any]]) -> float:
    by_category: dict[str, float] = {}
    for component in component_scores:
        category = component.get("category")
        score = component.get("score")
        if isinstance(category, str):
            try:
                by_category[category] = float(score)
            except (TypeError, ValueError):
                continue
    signal_quality = by_category.get("signal_quality", 0.0)
    backtest_quality = by_category.get("backtest_quality", 0.0)
    bounded = ((signal_quality * 0.60) + (backtest_quality * 0.40)) / 100.0
    return max(0.0, min(1.0, round(bounded, 4)))


def _derive_bounded_expected_value_from_components(
    *,
    component_scores: list[dict[str, Any]],
    win_rate: float,
) -> float:
    by_category: dict[str, float] = {}
    for component in component_scores:
        category = component.get("category")
        score = component.get("score")
        if isinstance(category, str):
            try:
                by_category[category] = float(score)
            except (TypeError, ValueError):
                continue
    risk_alignment = by_category.get("risk_alignment", 0.0)
    execution_readiness = by_category.get("execution_readiness", 0.0)
    reward_multiplier = (risk_alignment + execution_readiness) / 100.0
    bounded_reward_multiplier = max(0.50, min(1.50, reward_multiplier))
    expected_value = (win_rate * bounded_reward_multiplier) - (1.0 - win_rate)
    return max(-1.0, min(1.0, round(expected_value, 4)))


def _derive_decision_action_from_fields(
    *,
    has_blocking_failure: bool,
    qualification_state: str | None,
    confidence_tier: str | None,
    aggregate_score: float | None,
    win_rate: float,
    expected_value: float,
) -> DecisionAction:
    if has_blocking_failure:
        return "ignore"
    if expected_value < 0.0:
        return "exit"
    if qualification_state in {"paper_candidate", "paper_approved"} and win_rate <= ACTION_EXIT_WIN_RATE_MAX:
        return "exit"
    if (
        confidence_tier == "low"
        or aggregate_score is None
        or aggregate_score < QUALIFICATION_MEDIUM_AGGREGATE_THRESHOLD
        or qualification_state in {"reject", "watch"}
    ):
        return "ignore"
    if qualification_state in {"paper_candidate", "paper_approved"} and win_rate >= ACTION_ENTRY_WIN_RATE_MIN:
        return "entry"
    return "ignore"


def _collect_non_empty_texts(values: list[str | None]) -> list[str]:
    return [value.strip() for value in values if isinstance(value, str) and value.strip()]


def _contains_any_phrase(*, texts: list[str], phrases: tuple[str, ...]) -> bool:
    lowered = [text.casefold() for text in texts]
    return any(phrase in text for text in lowered for phrase in phrases)


def _classify_trader_relevance_status(
    checks: dict[str, bool],
) -> TraderRelevanceEvidenceStatus:
    true_count = sum(1 for ok in checks.values() if ok)
    if true_count == len(checks):
        return "aligned"
    if true_count == 0:
        return "missing"
    return "weak"


class HardGateResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    gate_id: str = Field(min_length=1)
    status: HardGateStatus
    blocking: bool = True
    reason: str = Field(min_length=1)
    evidence: list[str] = Field(min_length=1)
    failure_reason: str | None = None

    @field_validator("evidence")
    @classmethod
    def _validate_evidence(cls, value: list[str]) -> list[str]:
        normalized = [item.strip() for item in value if item and item.strip()]
        if not normalized:
            raise ValueError("Hard gate evidence must include at least one non-empty entry")
        return sorted(set(normalized))

    @model_validator(mode="after")
    def _validate_failure_reason(self) -> "HardGateResult":
        if self.status == "fail" and (self.failure_reason is None or not self.failure_reason.strip()):
            raise ValueError("Hard gate failures must define failure_reason")
        if self.status == "pass" and self.failure_reason is not None:
            raise ValueError("Passing hard gates must not define failure_reason")
        return self


class BoundedTraderRelevanceCaseEvaluation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: PaperReviewCaseId
    review_question: str = Field(min_length=16)
    evidence_status: TraderRelevanceEvidenceStatus
    required_evidence: list[str] = Field(min_length=1)
    observed_evidence: list[str]
    evidence_summary: str = Field(min_length=16)


class BoundedTraderRelevanceValidation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_id: str = BOUNDED_TRADER_RELEVANCE_CONTRACT_ID
    contract_version: str = BOUNDED_TRADER_RELEVANCE_CONTRACT_VERSION
    overall_status: TraderRelevanceEvidenceStatus
    evaluations: list[BoundedTraderRelevanceCaseEvaluation] = Field(min_length=1)

    @field_validator("contract_id")
    @classmethod
    def _validate_contract_id(cls, value: str) -> str:
        if value != BOUNDED_TRADER_RELEVANCE_CONTRACT_ID:
            raise ValueError(f"Unsupported bounded trader relevance contract_id: {value}")
        return value

    @field_validator("contract_version")
    @classmethod
    def _validate_contract_version(cls, value: str) -> str:
        if value != BOUNDED_TRADER_RELEVANCE_CONTRACT_VERSION:
            raise ValueError(f"Unsupported bounded trader relevance contract_version: {value}")
        return value

    @field_validator("evaluations")
    @classmethod
    def _validate_evaluations(cls, value: list[BoundedTraderRelevanceCaseEvaluation]) -> list[BoundedTraderRelevanceCaseEvaluation]:
        case_ids = [item.case_id for item in value]
        required_case_ids = sorted(PAPER_REVIEW_CASE_DEFINITIONS.keys())
        if sorted(case_ids) != required_case_ids:
            raise ValueError(
                "Bounded trader relevance evaluations must cover all canonical paper-review cases"
            )
        return sorted(value, key=lambda item: item.case_id)


class BoundedDecisionToPaperUsefulnessMatchReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    match_mode: DecisionToPaperUsefulnessMatchMode
    paper_trade_id: str = Field(min_length=1)


class BoundedPaperTradeOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    trade_id: str = Field(min_length=1)
    position_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    strategy_id: str = Field(min_length=1)
    trade_status: Literal["open", "closed"]
    opened_at_utc: str = Field(min_length=1)
    closed_at_utc: str | None = None
    outcome_direction: PaperTradeOutcomeDirection
    realized_pnl: str | None = None
    unrealized_pnl: str | None = None
    outcome_summary: str = Field(min_length=24)


class BoundedDecisionToPaperUsefulnessAudit(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_id: str = DECISION_TO_PAPER_USEFULNESS_CONTRACT_ID
    contract_version: str = DECISION_TO_PAPER_USEFULNESS_CONTRACT_VERSION
    covered_case_id: str = Field(min_length=1)
    match_reference: BoundedDecisionToPaperUsefulnessMatchReference
    match_status: DecisionToPaperUsefulnessMatchStatus
    matched_outcome: BoundedPaperTradeOutcome | None = None
    usefulness_classification: DecisionToPaperUsefulnessClassification
    usefulness_reason: str = Field(min_length=24)
    interpretation_limit: str = Field(min_length=24)

    @field_validator("contract_id")
    @classmethod
    def _validate_contract_id(cls, value: str) -> str:
        if value != DECISION_TO_PAPER_USEFULNESS_CONTRACT_ID:
            raise ValueError(f"Unsupported decision-to-paper usefulness contract_id: {value}")
        return value

    @field_validator("contract_version")
    @classmethod
    def _validate_contract_version(cls, value: str) -> str:
        if value != DECISION_TO_PAPER_USEFULNESS_CONTRACT_VERSION:
            raise ValueError(
                f"Unsupported decision-to-paper usefulness contract_version: {value}"
            )
        return value

    @model_validator(mode="after")
    def _validate_match_alignment(self) -> "BoundedDecisionToPaperUsefulnessAudit":
        if self.match_status in {"matched", "open", "invalid"} and self.matched_outcome is None:
            raise ValueError(
                "matched_outcome is required when match_status is matched, open, or invalid"
            )
        if self.match_status == "missing" and self.matched_outcome is not None:
            raise ValueError("matched_outcome must be omitted when match_status is missing")
        lowered_limit = self.interpretation_limit.casefold()
        required_phrases = (
            "non-live",
            "trader validation",
            "profitability forecasting",
            "live-trading readiness",
            "operational readiness",
        )
        if not all(phrase in lowered_limit for phrase in required_phrases):
            raise ValueError(
                "interpretation_limit must keep non-live usefulness separate from trader validation, "
                "profitability forecasting, and readiness claims"
            )
        return self


def _classify_decision_to_paper_usefulness(
    *,
    action: str,
    qualification_state: str,
    match_status: DecisionToPaperUsefulnessMatchStatus,
    matched_outcome: BoundedPaperTradeOutcome | None,
) -> tuple[DecisionToPaperUsefulnessClassification, str]:
    if action != "entry":
        return (
            "weak",
            "Contract v1 remains bounded to covered entry decisions, so non-entry decisions stay outside "
            "strong usefulness interpretation.",
        )
    if qualification_state not in {"paper_candidate", "paper_approved"}:
        return (
            "weak",
            "Entry usefulness remains weak because the decision did not resolve to a covered paper-entry "
            "qualification state.",
        )
    if match_status == "missing":
        return (
            "weak",
            "Covered entry decision has no resolved matched paper trade, so usefulness remains unproven in "
            "bounded non-live review.",
        )
    if match_status == "invalid":
        return (
            "misleading",
            "Matched paper trade violates the explicit symbol, strategy, or timing comparison contract, so "
            "the usefulness signal is misleading.",
        )
    if match_status == "open":
        return (
            "weak",
            "Matched paper trade remains open, so bounded usefulness is not yet resolved to an explanatory "
            "or misleading closed outcome.",
        )
    if matched_outcome is None:
        return (
            "weak",
            "Matched paper outcome is unavailable, so bounded usefulness remains weak.",
        )
    if matched_outcome.outcome_direction == "favorable":
        return (
            "explanatory",
            "Covered entry decision matched a subsequent closed paper trade with favorable bounded outcome, "
            "so the surfaced evidence is explanatory in non-live review.",
        )
    if matched_outcome.outcome_direction == "flat":
        return (
            "weak",
            "Covered entry decision matched a closed flat paper trade, so the surfaced evidence remains weak "
            "for bounded usefulness.",
        )
    return (
        "misleading",
        "Covered entry decision matched a subsequent closed paper trade with adverse bounded outcome, so the "
        "surfaced evidence is misleading in non-live review.",
    )


def evaluate_bounded_decision_to_paper_usefulness_audit(
    *,
    covered_case_id: str,
    action: str,
    qualification_state: str,
    match_status: DecisionToPaperUsefulnessMatchStatus,
    match_reference: dict[str, Any],
    matched_outcome: dict[str, Any] | None = None,
) -> BoundedDecisionToPaperUsefulnessAudit:
    normalized_match_reference = BoundedDecisionToPaperUsefulnessMatchReference.model_validate(
        match_reference
    )
    normalized_matched_outcome = (
        BoundedPaperTradeOutcome.model_validate(matched_outcome)
        if matched_outcome is not None
        else None
    )
    usefulness_classification, usefulness_reason = _classify_decision_to_paper_usefulness(
        action=action,
        qualification_state=qualification_state,
        match_status=match_status,
        matched_outcome=normalized_matched_outcome,
    )
    return BoundedDecisionToPaperUsefulnessAudit(
        covered_case_id=covered_case_id,
        match_reference=normalized_match_reference,
        match_status=match_status,
        matched_outcome=normalized_matched_outcome,
        usefulness_classification=usefulness_classification,
        usefulness_reason=usefulness_reason,
        interpretation_limit=DECISION_TO_PAPER_USEFULNESS_INTERPRETATION_BOUNDARY,
    )


class BoundedSignalQualityStabilityAudit(BaseModel):
    """Bounded signal-quality stability audit against matched paper outcomes.

    The audit is deterministic and bounded to non-live evidence comparison only.
    It compares the covered decision-card ``signal_quality`` component score
    against the matched paper-trade outcome resolved through the existing
    decision-to-paper match contract and classifies the covered signal as
    ``stable``, ``weak``, or ``failing``.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_id: str = SIGNAL_QUALITY_STABILITY_CONTRACT_ID
    contract_version: str = SIGNAL_QUALITY_STABILITY_CONTRACT_VERSION
    covered_case_id: str = Field(min_length=1)
    signal_quality_score: float = Field(ge=0.0, le=100.0)
    match_reference: BoundedDecisionToPaperUsefulnessMatchReference | None = None
    match_status: DecisionToPaperUsefulnessMatchStatus
    matched_outcome: BoundedPaperTradeOutcome | None = None
    stability_classification: SignalQualityStabilityClassification
    stability_reason: str = Field(min_length=24)
    interpretation_limit: str = Field(min_length=24)

    @field_validator("contract_id")
    @classmethod
    def _validate_contract_id(cls, value: str) -> str:
        if value != SIGNAL_QUALITY_STABILITY_CONTRACT_ID:
            raise ValueError(f"Unsupported signal-quality stability contract_id: {value}")
        return value

    @field_validator("contract_version")
    @classmethod
    def _validate_contract_version(cls, value: str) -> str:
        if value != SIGNAL_QUALITY_STABILITY_CONTRACT_VERSION:
            raise ValueError(
                f"Unsupported signal-quality stability contract_version: {value}"
            )
        return value

    @model_validator(mode="after")
    def _validate_match_alignment(self) -> "BoundedSignalQualityStabilityAudit":
        if self.match_status == "missing":
            if self.matched_outcome is not None:
                raise ValueError(
                    "matched_outcome must be omitted when match_status is missing"
                )
        else:
            if self.matched_outcome is None:
                raise ValueError(
                    "matched_outcome is required when match_status is matched, open, or invalid"
                )
        lowered_limit = self.interpretation_limit.casefold()
        required_phrases = (
            "non-live",
            "trader validation",
            "profitability forecasting",
            "live-trading readiness",
            "operational readiness",
        )
        if not all(phrase in lowered_limit for phrase in required_phrases):
            raise ValueError(
                "interpretation_limit must keep non-live signal-quality stability separate from "
                "trader validation, profitability forecasting, and readiness claims"
            )
        return self


def _classify_signal_quality_stability(
    *,
    signal_quality_score: float,
    match_status: DecisionToPaperUsefulnessMatchStatus,
    matched_outcome: BoundedPaperTradeOutcome | None,
) -> tuple[SignalQualityStabilityClassification, str]:
    if match_status == "missing":
        return (
            "weak",
            "Covered signal has no matched paper-trade evidence, so bounded signal-quality "
            "stability remains unproven in non-live review.",
        )
    if match_status == "invalid":
        return (
            "failing",
            "Matched paper trade violates the explicit symbol, strategy, or timing comparison "
            "contract, so bounded signal-quality stability is failing in non-live review.",
        )
    if match_status == "open":
        return (
            "weak",
            "Matched paper trade remains open, so bounded signal-quality stability is not yet "
            "resolved against a closed downstream outcome.",
        )
    if matched_outcome is None:
        return (
            "weak",
            "Matched paper outcome is unavailable, so bounded signal-quality stability remains "
            "weak.",
        )
    if matched_outcome.outcome_direction == "favorable":
        if signal_quality_score >= SIGNAL_QUALITY_STABILITY_HIGH_THRESHOLD:
            return (
                "stable",
                "Covered signal-quality score remains at or above the bounded high threshold and "
                "the matched paper trade closed favorable, so bounded signal-quality stability is "
                "stable in non-live review.",
            )
        return (
            "weak",
            "Matched paper trade closed favorable, but the covered signal-quality score is below "
            "the bounded high threshold, so bounded signal-quality stability remains weak in "
            "non-live review.",
        )
    if matched_outcome.outcome_direction == "flat":
        return (
            "weak",
            "Matched paper trade closed flat, so bounded signal-quality stability remains weak "
            "in non-live review.",
        )
    # adverse
    if signal_quality_score >= SIGNAL_QUALITY_STABILITY_HIGH_THRESHOLD:
        return (
            "failing",
            "Covered signal-quality score is at or above the bounded high threshold but the "
            "matched paper trade closed adverse, so bounded signal-quality stability is failing "
            "in non-live review.",
        )
    if signal_quality_score < SIGNAL_QUALITY_STABILITY_LOW_THRESHOLD:
        return (
            "failing",
            "Covered signal-quality score is below the bounded low threshold and the matched "
            "paper trade closed adverse, so bounded signal-quality stability is failing in "
            "non-live review.",
        )
    return (
        "weak",
        "Matched paper trade closed adverse with a covered signal-quality score in the bounded "
        "intermediate band, so bounded signal-quality stability remains weak in non-live review.",
    )


def evaluate_bounded_signal_quality_stability_audit(
    *,
    covered_case_id: str,
    signal_quality_score: float,
    match_status: DecisionToPaperUsefulnessMatchStatus,
    match_reference: dict[str, Any] | None = None,
    matched_outcome: dict[str, Any] | None = None,
) -> BoundedSignalQualityStabilityAudit:
    normalized_match_reference = (
        BoundedDecisionToPaperUsefulnessMatchReference.model_validate(match_reference)
        if match_reference is not None
        else None
    )
    normalized_matched_outcome = (
        BoundedPaperTradeOutcome.model_validate(matched_outcome)
        if matched_outcome is not None
        else None
    )
    classification, reason = _classify_signal_quality_stability(
        signal_quality_score=signal_quality_score,
        match_status=match_status,
        matched_outcome=normalized_matched_outcome,
    )
    return BoundedSignalQualityStabilityAudit(
        covered_case_id=covered_case_id,
        signal_quality_score=signal_quality_score,
        match_reference=normalized_match_reference,
        match_status=match_status,
        matched_outcome=normalized_matched_outcome,
        stability_classification=classification,
        stability_reason=reason,
        interpretation_limit=SIGNAL_QUALITY_STABILITY_INTERPRETATION_BOUNDARY,
    )


class BoundedConfidenceCalibrationAudit(BaseModel):
    """Bounded confidence-tier calibration against realism coverage and paper outcomes."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_id: str = CONFIDENCE_CALIBRATION_CONTRACT_ID
    contract_version: str = CONFIDENCE_CALIBRATION_CONTRACT_VERSION
    covered_case_id: str = Field(min_length=1)
    confidence_tier: DecisionConfidenceTier
    backtest_realism_status: BacktestRealismCalibrationStatus
    backtest_realism_reason: str = Field(min_length=24)
    match_reference: BoundedDecisionToPaperUsefulnessMatchReference | None = None
    match_status: DecisionToPaperUsefulnessMatchStatus
    matched_outcome: BoundedPaperTradeOutcome | None = None
    calibration_classification: ConfidenceCalibrationClassification
    calibration_reason: str = Field(min_length=24)
    interpretation_limit: str = Field(min_length=24)

    @field_validator("contract_id")
    @classmethod
    def _validate_contract_id(cls, value: str) -> str:
        if value != CONFIDENCE_CALIBRATION_CONTRACT_ID:
            raise ValueError(f"Unsupported confidence calibration contract_id: {value}")
        return value

    @field_validator("contract_version")
    @classmethod
    def _validate_contract_version(cls, value: str) -> str:
        if value != CONFIDENCE_CALIBRATION_CONTRACT_VERSION:
            raise ValueError(
                f"Unsupported confidence calibration contract_version: {value}"
            )
        return value

    @model_validator(mode="after")
    def _validate_match_alignment(self) -> "BoundedConfidenceCalibrationAudit":
        if self.match_status == "missing":
            if self.matched_outcome is not None:
                raise ValueError("matched_outcome must be omitted when match_status is missing")
        else:
            if self.matched_outcome is None:
                raise ValueError(
                    "matched_outcome is required when match_status is matched, open, or invalid"
                )
        lowered_limit = self.interpretation_limit.casefold()
        required_phrases = (
            "non-live",
            "trader validation",
            "profitability forecasting",
            "live-trading readiness",
            "operational readiness",
        )
        if not all(phrase in lowered_limit for phrase in required_phrases):
            raise ValueError(
                "interpretation_limit must keep non-live confidence calibration separate from "
                "trader validation, profitability forecasting, and readiness claims"
            )
        return self


def _classify_confidence_calibration(
    *,
    confidence_tier: DecisionConfidenceTier,
    backtest_realism_status: BacktestRealismCalibrationStatus,
    match_status: DecisionToPaperUsefulnessMatchStatus,
    matched_outcome: BoundedPaperTradeOutcome | None,
) -> tuple[ConfidenceCalibrationClassification, str]:
    if backtest_realism_status == "missing" or match_status == "missing":
        return (
            "weak",
            "Covered confidence tier lacks either matched paper evidence or covered backtest-realism "
            "evidence, so calibration remains weak in bounded non-live review.",
        )

    if backtest_realism_status == "failing" or match_status == "invalid":
        if confidence_tier == "low":
            return (
                "stable",
                "Covered confidence tier remains low while realism coverage or paper matching is "
                "failing, so bounded calibration is stable in non-live review.",
            )
        return (
            "failing",
            "Covered confidence tier overstates evidence while realism coverage or paper matching is "
            "failing, so bounded calibration is failing in non-live review.",
        )

    if match_status == "open":
        if confidence_tier == "high":
            return (
                "weak",
                "Covered confidence tier stays high while the matched paper trade remains open, so "
                "bounded calibration is weak until the downstream outcome closes.",
            )
        return (
            "stable",
            "Covered confidence tier remains cautious while the matched paper trade is still open, "
            "so bounded calibration is stable in non-live review.",
        )

    if matched_outcome is None:
        return (
            "weak",
            "Matched paper outcome is unavailable, so bounded confidence calibration remains weak.",
        )

    if matched_outcome.outcome_direction == "adverse":
        if confidence_tier == "low":
            return (
                "stable",
                "Covered confidence tier remains low and the matched paper trade closed adverse, so "
                "bounded calibration is stable in non-live review.",
            )
        return (
            "failing",
            "Covered confidence tier remained above low while the matched paper trade closed adverse, "
            "so bounded calibration is failing in non-live review.",
        )

    if matched_outcome.outcome_direction == "flat":
        if confidence_tier == "high":
            return (
                "weak",
                "Covered confidence tier remains high while the matched paper trade closed flat, so "
                "bounded calibration is weak in non-live review.",
            )
        return (
            "stable",
            "Covered confidence tier stays bounded at medium/low while the matched paper trade closed "
            "flat, so calibration is stable in non-live review.",
        )

    # favorable
    if backtest_realism_status == "stable":
        if confidence_tier == "low":
            return (
                "weak",
                "Covered confidence tier remains low even though realism coverage is stable and the "
                "matched paper trade closed favorable, so bounded calibration is weak in non-live review.",
            )
        return (
            "stable",
            "Covered confidence tier aligns with stable realism coverage and a favorable matched paper "
            "outcome, so bounded calibration is stable in non-live review.",
        )

    # backtest_realism_status == "weak"
    if confidence_tier == "high":
        return (
            "weak",
            "Covered confidence tier remains high while backtest-realism coverage is only weak, so "
            "bounded calibration is weak despite the favorable matched paper outcome.",
        )
    return (
        "stable",
        "Covered confidence tier remains bounded at medium/low while backtest-realism coverage is weak "
        "and the matched paper outcome is favorable, so calibration is stable in non-live review.",
    )


def evaluate_bounded_confidence_calibration_audit(
    *,
    covered_case_id: str,
    confidence_tier: DecisionConfidenceTier,
    backtest_realism_status: BacktestRealismCalibrationStatus,
    backtest_realism_reason: str,
    match_status: DecisionToPaperUsefulnessMatchStatus,
    match_reference: dict[str, Any] | None = None,
    matched_outcome: dict[str, Any] | None = None,
) -> BoundedConfidenceCalibrationAudit:
    normalized_match_reference = (
        BoundedDecisionToPaperUsefulnessMatchReference.model_validate(match_reference)
        if match_reference is not None
        else None
    )
    normalized_matched_outcome = (
        BoundedPaperTradeOutcome.model_validate(matched_outcome)
        if matched_outcome is not None
        else None
    )
    classification, reason = _classify_confidence_calibration(
        confidence_tier=confidence_tier,
        backtest_realism_status=backtest_realism_status,
        match_status=match_status,
        matched_outcome=normalized_matched_outcome,
    )
    return BoundedConfidenceCalibrationAudit(
        covered_case_id=covered_case_id,
        confidence_tier=confidence_tier,
        backtest_realism_status=backtest_realism_status,
        backtest_realism_reason=backtest_realism_reason,
        match_reference=normalized_match_reference,
        match_status=match_status,
        matched_outcome=normalized_matched_outcome,
        calibration_classification=classification,
        calibration_reason=reason,
        interpretation_limit=CONFIDENCE_CALIBRATION_INTERPRETATION_BOUNDARY,
    )


EndToEndTraceabilityLinkageStatus = Literal["matched", "open", "missing", "invalid"]


class BoundedSignalAnalysisStageReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    stage: Literal["signal_analysis"] = "signal_analysis"
    surface: str = END_TO_END_TRACEABILITY_SIGNAL_SURFACE
    analysis_run_id: str | None = None
    symbol: str = Field(min_length=1)
    strategy_id: str = Field(min_length=1)
    linkage_status: EndToEndTraceabilityLinkageStatus


class BoundedDecisionStageReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    stage: Literal["decision_card"] = "decision_card"
    surface: str = END_TO_END_TRACEABILITY_DECISION_SURFACE
    decision_card_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    qualification_state: QualificationState
    action: DecisionAction
    linkage_status: EndToEndTraceabilityLinkageStatus = "matched"


class BoundedPaperStageReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    stage: Literal["paper_trade"] = "paper_trade"
    surface: str = END_TO_END_TRACEABILITY_PAPER_SURFACE
    paper_trade_id: str | None = None
    linkage_status: EndToEndTraceabilityLinkageStatus


class BoundedReconciliationStageReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    stage: Literal["reconciliation"] = "reconciliation"
    surface: str = END_TO_END_TRACEABILITY_RECONCILIATION_SURFACE
    linkage_status: EndToEndTraceabilityLinkageStatus


class BoundedEndToEndTraceabilityChain(BaseModel):
    """One canonical deterministic traceability reference chain.

    Stages: signal/analysis -> decision card -> paper trade -> reconciliation.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_id: str = END_TO_END_TRACEABILITY_CONTRACT_ID
    contract_version: str = END_TO_END_TRACEABILITY_CONTRACT_VERSION
    overall_linkage_status: EndToEndTraceabilityLinkageStatus
    signal_analysis: BoundedSignalAnalysisStageReference
    decision: BoundedDecisionStageReference
    paper: BoundedPaperStageReference
    reconciliation: BoundedReconciliationStageReference
    interpretation_limit: str = Field(min_length=24)

    @field_validator("contract_id")
    @classmethod
    def _validate_contract_id(cls, value: str) -> str:
        if value != END_TO_END_TRACEABILITY_CONTRACT_ID:
            raise ValueError(f"Unsupported end-to-end traceability contract_id: {value}")
        return value

    @field_validator("contract_version")
    @classmethod
    def _validate_contract_version(cls, value: str) -> str:
        if value != END_TO_END_TRACEABILITY_CONTRACT_VERSION:
            raise ValueError(
                f"Unsupported end-to-end traceability contract_version: {value}"
            )
        return value

    @model_validator(mode="after")
    def _validate_chain_alignment(self) -> "BoundedEndToEndTraceabilityChain":
        lowered_limit = self.interpretation_limit.casefold()
        required_phrases = (
            "non-live",
            "trader validation",
            "profitability forecasting",
            "live-trading readiness",
            "operational readiness",
        )
        if not all(phrase in lowered_limit for phrase in required_phrases):
            raise ValueError(
                "interpretation_limit must keep non-live traceability separate from trader "
                "validation, profitability forecasting, and readiness claims"
            )
        if self.paper.paper_trade_id is None and self.paper.linkage_status != "missing":
            raise ValueError(
                "paper.linkage_status must be 'missing' when paper_trade_id is not provided"
            )
        if self.paper.paper_trade_id is not None and self.paper.linkage_status == "missing":
            raise ValueError(
                "paper.linkage_status must not be 'missing' when paper_trade_id is provided"
            )
        # Reconciliation linkage status mirrors paper linkage status: a paper match must be
        # reconcilable; a missing/invalid paper reference cannot anchor a reconciliation match.
        if self.reconciliation.linkage_status != self.paper.linkage_status:
            raise ValueError(
                "reconciliation.linkage_status must equal paper.linkage_status for the bounded chain"
            )
        if self.overall_linkage_status != self.paper.linkage_status:
            raise ValueError(
                "overall_linkage_status must equal paper.linkage_status for the bounded chain"
            )
        return self


def evaluate_bounded_end_to_end_traceability_chain(
    *,
    decision_card_id: str,
    generated_at_utc: str,
    symbol: str,
    strategy_id: str,
    qualification_state: QualificationState,
    action: DecisionAction,
    analysis_run_id: str | None,
    paper_trade_id: str | None,
    paper_match_status: EndToEndTraceabilityLinkageStatus | None,
) -> BoundedEndToEndTraceabilityChain:
    """Build a deterministic end-to-end traceability chain from explicit references.

    ``paper_match_status`` is the bounded linkage status returned by the
    decision-to-paper usefulness audit (matched/open/missing/invalid). When
    ``paper_trade_id`` is None the chain is locked to ``missing``.
    """

    if paper_trade_id is None:
        resolved_status: EndToEndTraceabilityLinkageStatus = "missing"
    elif paper_match_status is None:
        resolved_status = "missing"
    else:
        resolved_status = paper_match_status

    signal_linkage_status: EndToEndTraceabilityLinkageStatus = (
        "matched" if analysis_run_id else "missing"
    )
    return BoundedEndToEndTraceabilityChain(
        overall_linkage_status=resolved_status,
        signal_analysis=BoundedSignalAnalysisStageReference(
            analysis_run_id=analysis_run_id,
            symbol=symbol,
            strategy_id=strategy_id,
            linkage_status=signal_linkage_status,
        ),
        decision=BoundedDecisionStageReference(
            decision_card_id=decision_card_id,
            generated_at_utc=generated_at_utc,
            qualification_state=qualification_state,
            action=action,
        ),
        paper=BoundedPaperStageReference(
            paper_trade_id=paper_trade_id,
            linkage_status=resolved_status,
        ),
        reconciliation=BoundedReconciliationStageReference(
            linkage_status=resolved_status,
        ),
        interpretation_limit=END_TO_END_TRACEABILITY_INTERPRETATION_BOUNDARY,
    )


def evaluate_bounded_trader_relevance_cases(
    *,
    qualification_state: str | None,
    action: str | None,
    win_rate: float | None,
    expected_value: float | None,
    qualification_summary: str | None,
    rationale_summary: str | None = None,
    final_explanation: str | None = None,
    gate_explanations: list[str] | None = None,
    score_explanations: list[str] | None = None,
    qualification_evidence: list[str] | None = None,
    missing_criteria: list[str] | None = None,
    blocking_conditions: list[str] | None = None,
) -> BoundedTraderRelevanceValidation:
    normalized_gate_explanations = list(gate_explanations or [])
    normalized_score_explanations = list(score_explanations or [])
    normalized_qualification_evidence = list(qualification_evidence or [])
    normalized_missing_criteria = list(missing_criteria or [])
    normalized_blocking_conditions = list(blocking_conditions or [])

    all_texts = _collect_non_empty_texts(
        [
            qualification_summary,
            rationale_summary,
            final_explanation,
            *normalized_gate_explanations,
            *normalized_score_explanations,
            *normalized_qualification_evidence,
            *normalized_missing_criteria,
            *normalized_blocking_conditions,
        ]
    )
    qualification_summary_text = (qualification_summary or "").strip()

    case_checks: dict[PaperReviewCaseId, dict[str, bool]] = {
        "qualification_state_relevance": {
            "qualification_state": bool(qualification_state and str(qualification_state).strip()),
            "paper_scope_summary": "paper" in qualification_summary_text.casefold(),
            "state_explanation_evidence": bool(
                normalized_gate_explanations
                or normalized_qualification_evidence
                or normalized_missing_criteria
                or normalized_blocking_conditions
            ),
        },
        "decision_action_relevance": {
            "action": bool(action and str(action).strip()),
            "bounded_decision_metrics": (win_rate is not None and expected_value is not None),
            "action_rule_trace": _contains_any_phrase(
                texts=normalized_score_explanations + normalized_qualification_evidence,
                phrases=("action", "entry", "exit", "ignore", "expected value", "win_rate", "win-rate"),
            ),
        },
        "boundary_scope_relevance": {
            "trader_validation_boundary": _contains_any_phrase(
                texts=all_texts,
                phrases=("trader_validation", "trader validation"),
            ),
            "paper_profitability_boundary": _contains_any_phrase(
                texts=all_texts,
                phrases=("paper profitability", "profitability", "edge claim", "profit claim"),
            ),
            "live_readiness_boundary": _contains_any_phrase(
                texts=all_texts,
                phrases=(
                    "live-trading approval",
                    "live trading readiness",
                    "live readiness",
                    "operational readiness",
                    "broker execution readiness",
                ),
            ),
        },
    }

    evaluations: list[BoundedTraderRelevanceCaseEvaluation] = []
    statuses: list[TraderRelevanceEvidenceStatus] = []
    for case_id in sorted(PAPER_REVIEW_CASE_DEFINITIONS.keys()):
        checks = case_checks[case_id]
        status = _classify_trader_relevance_status(checks=checks)
        statuses.append(status)
        observed = sorted(signal for signal, ok in checks.items() if ok)
        required = list(PAPER_REVIEW_CASE_DEFINITIONS[case_id]["required_evidence"])
        summary = (
            f"Deterministic case={case_id} classified as {status}; "
            f"observed={','.join(observed) if observed else 'none'}."
        )
        evaluations.append(
            BoundedTraderRelevanceCaseEvaluation(
                case_id=case_id,
                review_question=str(PAPER_REVIEW_CASE_DEFINITIONS[case_id]["review_question"]),
                evidence_status=status,
                required_evidence=required,
                observed_evidence=observed,
                evidence_summary=summary,
            )
        )

    if "missing" in statuses:
        overall_status: TraderRelevanceEvidenceStatus = "missing"
    elif "weak" in statuses:
        overall_status = "weak"
    else:
        overall_status = "aligned"

    return BoundedTraderRelevanceValidation(
        overall_status=overall_status,
        evaluations=evaluations,
    )


class QualificationProfileRobustnessSliceResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    slice_id: str = Field(min_length=1)
    slice_type: QualificationProfileRobustnessSliceType
    deterministic_rank: int = Field(ge=1)
    description: str = Field(min_length=16)
    behavior_status: QualificationProfileRobustnessStatus
    qualification_state: QualificationState
    action: DecisionAction
    confidence_tier: DecisionConfidenceTier
    aggregate_score: float = Field(ge=0.0, le=100.0)
    base_aggregate_score: float = Field(ge=0.0, le=100.0)
    win_rate: float = Field(ge=0.0, le=1.0)
    expected_value: float = Field(ge=-1.0, le=1.0)
    has_blocking_failure: bool = False
    applied_adjustments: list[str] = Field(min_length=1)
    finding: str = Field(min_length=24)

    @field_validator("applied_adjustments")
    @classmethod
    def _normalize_adjustments(cls, value: list[str]) -> list[str]:
        normalized = [item.strip() for item in value if item and item.strip()]
        if not normalized:
            raise ValueError("Robustness slice must include at least one adjustment entry")
        return normalized


class QualificationProfileRobustnessAudit(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_id: str = QUALIFICATION_PROFILE_ROBUSTNESS_CONTRACT_ID
    contract_version: str = QUALIFICATION_PROFILE_ROBUSTNESS_CONTRACT_VERSION
    comparison_group: str = Field(min_length=1)
    threshold_profile_id: str = Field(min_length=1)
    stable_slice_ids: list[str] = Field(default_factory=list)
    weak_slice_ids: list[str] = Field(default_factory=list)
    failing_slice_ids: list[str] = Field(default_factory=list)
    slice_results: list[QualificationProfileRobustnessSliceResult] = Field(min_length=1)
    audit_summary: str = Field(min_length=24)
    interpretation_limit: str = Field(min_length=24)

    @field_validator("contract_id")
    @classmethod
    def _validate_contract_id(cls, value: str) -> str:
        if value != QUALIFICATION_PROFILE_ROBUSTNESS_CONTRACT_ID:
            raise ValueError(f"Unsupported qualification-profile robustness contract_id: {value}")
        return value

    @field_validator("contract_version")
    @classmethod
    def _validate_contract_version(cls, value: str) -> str:
        if value != QUALIFICATION_PROFILE_ROBUSTNESS_CONTRACT_VERSION:
            raise ValueError(
                f"Unsupported qualification-profile robustness contract_version: {value}"
            )
        return value

    @field_validator("stable_slice_ids", "weak_slice_ids", "failing_slice_ids")
    @classmethod
    def _normalize_slice_id_lists(cls, value: list[str]) -> list[str]:
        normalized = sorted({item.strip() for item in value if item and item.strip()})
        return normalized

    @field_validator("slice_results")
    @classmethod
    def _validate_slice_results(
        cls, value: list[QualificationProfileRobustnessSliceResult]
    ) -> list[QualificationProfileRobustnessSliceResult]:
        ordered = sorted(value, key=lambda item: (item.deterministic_rank, item.slice_id))
        slice_ids = [item.slice_id for item in ordered]
        if len(slice_ids) != len(set(slice_ids)):
            raise ValueError("Robustness audit slice_results must use unique slice identifiers")
        return ordered

    @model_validator(mode="after")
    def _validate_summary_alignment(self) -> "QualificationProfileRobustnessAudit":
        expected_by_status = {
            "stable": sorted(
                item.slice_id for item in self.slice_results if item.behavior_status == "stable"
            ),
            "weak": sorted(
                item.slice_id for item in self.slice_results if item.behavior_status == "weak"
            ),
            "failing": sorted(
                item.slice_id for item in self.slice_results if item.behavior_status == "failing"
            ),
        }
        if self.stable_slice_ids != expected_by_status["stable"]:
            raise ValueError("stable_slice_ids must match slice_results behavior_status=stable")
        if self.weak_slice_ids != expected_by_status["weak"]:
            raise ValueError("weak_slice_ids must match slice_results behavior_status=weak")
        if self.failing_slice_ids != expected_by_status["failing"]:
            raise ValueError("failing_slice_ids must match slice_results behavior_status=failing")
        phrase = _contains_forbidden_claim_phrase(self.audit_summary)
        if phrase is not None:
            raise ValueError(f"audit_summary contains unsupported claim language: {phrase}")
        phrase = _contains_forbidden_claim_phrase(self.interpretation_limit)
        if phrase is not None:
            raise ValueError(f"interpretation_limit contains unsupported claim language: {phrase}")
        if "covered conditions" not in self.interpretation_limit.casefold():
            raise ValueError(
                "interpretation_limit must explain how robustness findings limit interpretation "
                "outside covered conditions"
            )
        return self


class HardGateEvaluation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    policy_version: str = Field(min_length=1)
    gates: list[HardGateResult] = Field(min_length=1)

    @field_validator("gates")
    @classmethod
    def _normalize_gates(cls, value: list[HardGateResult]) -> list[HardGateResult]:
        gate_ids = [gate.gate_id for gate in value]
        if len(set(gate_ids)) != len(gate_ids):
            raise ValueError("Hard gate IDs must be unique")
        return sorted(value, key=lambda gate: gate.gate_id)

    @property
    def has_blocking_failure(self) -> bool:
        return any(gate.blocking and gate.status == "fail" for gate in self.gates)


class ComponentScore(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    category: DecisionComponentCategory
    score: float = Field(ge=0.0, le=100.0)
    rationale: str = Field(min_length=8)
    evidence: list[str] = Field(min_length=1)

    @field_validator("evidence")
    @classmethod
    def _validate_evidence(cls, value: list[str]) -> list[str]:
        normalized = [item.strip() for item in value if item and item.strip()]
        if not normalized:
            raise ValueError("Component score evidence must include at least one non-empty entry")
        return sorted(set(normalized))


class ScoreEvaluation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    component_scores: list[ComponentScore] = Field(min_length=1)
    confidence_tier: DecisionConfidenceTier
    confidence_reason: str = Field(min_length=8)
    aggregate_score: float = Field(ge=0.0, le=100.0)
    win_rate: float = Field(ge=0.0, le=1.0)
    expected_value: float = Field(ge=-1.0, le=1.0)

    @field_validator("component_scores")
    @classmethod
    def _validate_component_coverage(cls, value: list[ComponentScore]) -> list[ComponentScore]:
        categories = [component.category for component in value]
        if len(set(categories)) != len(categories):
            raise ValueError("Component score categories must be unique")
        if set(categories) != set(REQUIRED_COMPONENT_CATEGORIES):
            missing = sorted(set(REQUIRED_COMPONENT_CATEGORIES) - set(categories))
            extra = sorted(set(categories) - set(REQUIRED_COMPONENT_CATEGORIES))
            details = []
            if missing:
                details.append(f"missing={','.join(missing)}")
            if extra:
                details.append(f"extra={','.join(extra)}")
            raise ValueError(
                "Component score categories must match required set "
                f"({'; '.join(details)})"
            )
        return sorted(value, key=lambda component: component.category)

    @field_validator("confidence_reason")
    @classmethod
    def _validate_confidence_reason_claim_boundary(cls, value: str) -> str:
        reason = value.strip()
        phrase = _contains_forbidden_claim_phrase(reason)
        if phrase is not None:
            raise ValueError(
                f"confidence_reason contains unsupported claim language: {phrase}"
            )
        lowered = reason.casefold()
        if not any(term in lowered for term in EVIDENCE_CONFIDENCE_REQUIRED_TERMS):
            raise ValueError(
                "confidence_reason must reference bounded evidence terms "
                "(aggregate/component/threshold/evidence)"
            )
        return reason


class Qualification(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    state: QualificationState
    color: QualificationColor
    summary: str = Field(min_length=8)

    @model_validator(mode="after")
    def _validate_color_mapping(self) -> "Qualification":
        expected_color = QUALIFICATION_COLOR_BY_STATE[self.state]
        if self.color != expected_color:
            raise ValueError(
                f"Qualification color must match state mapping: {self.state}->{expected_color}"
            )
        phrase = _contains_forbidden_claim_phrase(self.summary)
        if phrase is not None:
            raise ValueError(
                f"qualification.summary contains unsupported claim language: {phrase}"
            )
        if "paper" not in self.summary.casefold():
            raise ValueError("qualification.summary must stay bounded to paper-trading scope")
        return self


class DecisionRationale(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    summary: str = Field(min_length=16)
    gate_explanations: list[str] = Field(min_length=1)
    score_explanations: list[str] = Field(min_length=1)
    final_explanation: str = Field(min_length=16)

    @field_validator("gate_explanations", "score_explanations")
    @classmethod
    def _normalize_explanations(cls, value: list[str]) -> list[str]:
        normalized = [item.strip() for item in value if item and item.strip()]
        if not normalized:
            raise ValueError("Rationale explanation lists must include non-empty values")
        return normalized

    @model_validator(mode="after")
    def _validate_claim_boundary_language(self) -> "DecisionRationale":
        phrase = _contains_forbidden_claim_phrase(self.summary)
        if phrase is not None:
            raise ValueError(f"rationale.summary contains unsupported claim language: {phrase}")
        phrase = _contains_forbidden_claim_phrase(self.final_explanation)
        if phrase is not None:
            raise ValueError(
                f"rationale.final_explanation contains unsupported claim language: {phrase}"
            )
        if "does not imply live-trading approval" not in self.final_explanation.casefold():
            raise ValueError(
                "rationale.final_explanation must explicitly state that output does not imply "
                "live-trading approval"
            )
        return self


class DecisionCard(BaseModel):
    """Canonical decision-card entity for qualification decisions."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: str = DECISION_CARD_CONTRACT_VERSION
    decision_card_id: str = Field(min_length=1)
    generated_at_utc: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    strategy_id: str = Field(min_length=1)
    hard_gates: HardGateEvaluation
    score: ScoreEvaluation
    action: DecisionAction
    qualification: Qualification
    rationale: DecisionRationale
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _hydrate_compatibility_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        payload = dict(data)
        score_payload = dict(payload.get("score") or {})
        component_scores = score_payload.get("component_scores")
        if not isinstance(component_scores, list):
            component_scores = []

        win_rate_value = score_payload.get("win_rate")
        if win_rate_value is None:
            win_rate = _derive_bounded_win_rate_from_components(component_scores)
            score_payload["win_rate"] = win_rate
        else:
            win_rate = float(win_rate_value)

        expected_value_value = score_payload.get("expected_value")
        if expected_value_value is None:
            expected_value = _derive_bounded_expected_value_from_components(
                component_scores=component_scores,
                win_rate=win_rate,
            )
            score_payload["expected_value"] = expected_value
        else:
            expected_value = float(expected_value_value)

        payload["score"] = score_payload
        if payload.get("action") is None:
            hard_gates_payload = dict(payload.get("hard_gates") or {})
            gate_items = hard_gates_payload.get("gates")
            has_blocking_failure = False
            if isinstance(gate_items, list):
                has_blocking_failure = any(
                    isinstance(gate, dict)
                    and gate.get("status") == "fail"
                    and gate.get("blocking", True) is True
                    for gate in gate_items
                )
            qualification_payload = dict(payload.get("qualification") or {})
            qualification_state = qualification_payload.get("state")
            confidence_tier = score_payload.get("confidence_tier")
            aggregate_score_value = score_payload.get("aggregate_score")
            aggregate_score = (
                float(aggregate_score_value) if aggregate_score_value is not None else None
            )
            payload["action"] = _derive_decision_action_from_fields(
                has_blocking_failure=has_blocking_failure,
                qualification_state=qualification_state,
                confidence_tier=confidence_tier,
                aggregate_score=aggregate_score,
                win_rate=win_rate,
                expected_value=expected_value,
            )
        return payload

    @field_validator("contract_version")
    @classmethod
    def _validate_contract_version(cls, value: str) -> str:
        if value != DECISION_CARD_CONTRACT_VERSION:
            raise ValueError(f"Unsupported decision-card contract_version: {value}")
        return value

    @field_validator("generated_at_utc")
    @classmethod
    def _validate_generated_at_utc(cls, value: str) -> str:
        if value.endswith("Z"):
            iso_value = value.replace("Z", "+00:00")
        else:
            iso_value = value
        try:
            timestamp = datetime.fromisoformat(iso_value)
        except ValueError as exc:
            raise ValueError("generated_at_utc must be ISO-8601 compatible") from exc
        if timestamp.tzinfo is None:
            raise ValueError("generated_at_utc must include timezone information")
        return value

    @field_validator("metadata")
    @classmethod
    def _validate_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError("metadata must be an object")
        for key in value:
            if not isinstance(key, str):
                raise ValueError("metadata keys must be strings")
        normalized = dict(sorted(value.items()))
        robustness_audit = normalized.get("qualification_profile_robustness_audit")
        if robustness_audit is not None:
            if not isinstance(robustness_audit, dict):
                raise ValueError("qualification_profile_robustness_audit metadata must be an object")
            normalized["qualification_profile_robustness_audit"] = (
                QualificationProfileRobustnessAudit.model_validate(robustness_audit).model_dump(
                    mode="python"
                )
            )
        return normalized

    @model_validator(mode="after")
    def _validate_qualification_semantics(self) -> "DecisionCard":
        expected_state = self._expected_qualification_state()
        if self.qualification.state != expected_state:
            raise ValueError(
                "Qualification state must match deterministic resolution "
                f"(expected={expected_state}, actual={self.qualification.state})"
            )
        if self.hard_gates.has_blocking_failure and self.qualification.color != "red":
            raise ValueError("Blocking hard-gate failures require red qualification color")
        if self.action == "entry" and self.score.expected_value < 0.0:
            raise ValueError("Negative expected value must not resolve to entry action")
        expected_action = self._expected_decision_action()
        if self.action != expected_action:
            raise ValueError(
                "Decision action must match deterministic resolution "
                f"(expected={expected_action}, actual={self.action})"
            )
        return self

    def _expected_qualification_state(self) -> QualificationState:
        medium_threshold, high_threshold = _qualification_thresholds_from_metadata(self.metadata)
        if self.hard_gates.has_blocking_failure:
            return "reject"
        if (
            self.score.confidence_tier == "low"
            or self.score.aggregate_score < medium_threshold
        ):
            return "watch"
        if (
            self.score.confidence_tier == "high"
            and self.score.aggregate_score >= high_threshold
        ):
            return "paper_approved"
        return "paper_candidate"

    def _expected_decision_action(self) -> DecisionAction:
        medium_threshold, _ = _qualification_thresholds_from_metadata(self.metadata)
        if self.hard_gates.has_blocking_failure:
            return "ignore"
        if self.score.expected_value < 0.0:
            return "exit"
        if (
            self.qualification.state in {"paper_candidate", "paper_approved"}
            and self.score.win_rate <= ACTION_EXIT_WIN_RATE_MAX
        ):
            return "exit"
        if (
            self.score.confidence_tier == "low"
            or self.score.aggregate_score < medium_threshold
            or self.qualification.state in {"reject", "watch"}
        ):
            return "ignore"
        if (
            self.qualification.state in {"paper_candidate", "paper_approved"}
            and self.score.win_rate >= ACTION_ENTRY_WIN_RATE_MIN
        ):
            return "entry"
        return "ignore"

    def to_canonical_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="python")

    def to_canonical_json(self) -> str:
        return json.dumps(
            self.to_canonical_payload(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )


def validate_decision_card(payload: dict[str, Any]) -> DecisionCard:
    """Validate and return a canonical decision card instance."""
    return DecisionCard.model_validate(payload)


def serialize_decision_card(card: DecisionCard) -> str:
    """Return deterministic JSON serialization for a decision card."""
    return card.to_canonical_json()


__all__ = [
    "DECISION_CARD_CONTRACT_VERSION",
    "BOUNDED_TRADER_RELEVANCE_CONTRACT_ID",
    "BOUNDED_TRADER_RELEVANCE_CONTRACT_VERSION",
    "DECISION_TO_PAPER_USEFULNESS_CONTRACT_ID",
    "DECISION_TO_PAPER_USEFULNESS_CONTRACT_VERSION",
    "DECISION_TO_PAPER_USEFULNESS_INTERPRETATION_BOUNDARY",
    "SIGNAL_QUALITY_STABILITY_CONTRACT_ID",
    "SIGNAL_QUALITY_STABILITY_CONTRACT_VERSION",
    "SIGNAL_QUALITY_STABILITY_INTERPRETATION_BOUNDARY",
    "SIGNAL_QUALITY_STABILITY_HIGH_THRESHOLD",
    "SIGNAL_QUALITY_STABILITY_LOW_THRESHOLD",
    "END_TO_END_TRACEABILITY_CONTRACT_ID",
    "END_TO_END_TRACEABILITY_CONTRACT_VERSION",
    "END_TO_END_TRACEABILITY_INTERPRETATION_BOUNDARY",
    "END_TO_END_TRACEABILITY_RECONCILIATION_SURFACE",
    "END_TO_END_TRACEABILITY_DECISION_SURFACE",
    "END_TO_END_TRACEABILITY_PAPER_SURFACE",
    "END_TO_END_TRACEABILITY_SIGNAL_SURFACE",
    "PAPER_REVIEW_CASE_DEFINITIONS",
    "CROSS_STRATEGY_SCORE_COMPARABILITY_BOUNDARY",
    "CONFIDENCE_TIER_PRECISION_DISCLAIMER",
    "QUALIFICATION_PROFILE_ROBUSTNESS_CONTRACT_ID",
    "QUALIFICATION_PROFILE_ROBUSTNESS_CONTRACT_VERSION",
    "QUALIFICATION_PROFILE_ROBUSTNESS_INTERPRETATION_BOUNDARY",
    "UPSTREAM_EVIDENCE_QUALITY_CONFIDENCE_BOUND",
    "QUALIFICATION_HIGH_AGGREGATE_THRESHOLD",
    "QUALIFICATION_MEDIUM_AGGREGATE_THRESHOLD",
    "REQUIRED_COMPONENT_CATEGORIES",
    "ACTION_ENTRY_WIN_RATE_MIN",
    "ACTION_EXIT_WIN_RATE_MAX",
    "QUALIFICATION_COLOR_BY_STATE",
    "BoundedDecisionStageReference",
    "BoundedDecisionToPaperUsefulnessAudit",
    "BoundedDecisionToPaperUsefulnessMatchReference",
    "BoundedEndToEndTraceabilityChain",
    "BoundedPaperStageReference",
    "BoundedPaperTradeOutcome",
    "BoundedReconciliationStageReference",
    "BoundedSignalAnalysisStageReference",
    "BoundedSignalQualityStabilityAudit",
    "BoundedTraderRelevanceCaseEvaluation",
    "BoundedTraderRelevanceValidation",
    "ComponentScore",
    "DecisionAction",
    "DecisionCard",
    "DecisionRationale",
    "EndToEndTraceabilityLinkageStatus",
    "SignalQualityStabilityClassification",
    "HardGateEvaluation",
    "HardGateResult",
    "QualificationProfileRobustnessAudit",
    "QualificationProfileRobustnessSliceResult",
    "Qualification",
    "ScoreEvaluation",
    "evaluate_bounded_decision_to_paper_usefulness_audit",
    "evaluate_bounded_end_to_end_traceability_chain",
    "evaluate_bounded_signal_quality_stability_audit",
    "evaluate_bounded_trader_relevance_cases",
    "serialize_decision_card",
    "validate_decision_card",
]

```

### src\api\services\paper_inspection_service.py
```
"""Paper inspection service — all state derived from canonical execution repository.

State authority: SqliteCanonicalExecutionRepository is the sole source of truth.
See ``cilly_trading.portfolio.paper_state_authority`` for the full contract.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal, Optional, Sequence

from fastapi import HTTPException
from pydantic import ValidationError

from cilly_trading.engine.decision_card_contract import (
    BoundedDecisionToPaperUsefulnessMatchReference,
    BacktestRealismCalibrationStatus,
    evaluate_bounded_confidence_calibration_audit,
    evaluate_bounded_decision_to_paper_usefulness_audit,
    evaluate_bounded_signal_quality_stability_audit,
)
from cilly_trading.models import ExecutionEvent, Order, Position, Trade


def paginate_items(items: list[object], *, limit: int, offset: int) -> tuple[list[object], int]:
    total = len(items)
    return items[offset : offset + limit], total


def resolve_paper_starting_cash() -> Decimal:
    raw_value = os.getenv("CILLY_PAPER_ACCOUNT_STARTING_CASH", "100000")
    try:
        value = Decimal(raw_value)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="paper_account_starting_cash_invalid") from exc
    if value < Decimal("0"):
        raise HTTPException(status_code=500, detail="paper_account_starting_cash_invalid")
    return value


def sum_decimals(values: list[Decimal]) -> Decimal:
    return sum(values, Decimal("0"))


@dataclass(frozen=True)
class PortfolioInspectionPositionState:
    strategy_id: str
    symbol: str
    size: Decimal
    average_price: Decimal
    unrealized_pnl: Decimal


@dataclass(frozen=True)
class _AggregatedPortfolioPosition:
    strategy_id: str
    symbol: str
    size: Decimal
    weighted_notional: Decimal
    unrealized_pnl: Decimal


@dataclass(frozen=True)
class BoundedPaperSimulationState:
    """Immutable snapshot of paper state derived from the canonical execution repository.

    Every field is computed deterministically from ``core_orders``,
    ``core_execution_events``, and ``core_trades``.  No alternative state
    source is used.  See ``cilly_trading.portfolio.paper_state_authority``.
    """

    orders: tuple[Order, ...]
    execution_events: tuple[ExecutionEvent, ...]
    trades: tuple[Trade, ...]
    positions: tuple[Position, ...]
    account: dict[str, object]
    portfolio_positions: tuple[PortfolioInspectionPositionState, ...]
    reconciliation_mismatches: tuple[dict[str, Optional[str]], ...]


def build_paper_account_state(
    *,
    paper_trades: list[Trade],
    paper_positions: list[Position],
) -> dict[str, object]:
    starting_cash = resolve_paper_starting_cash()
    realized_pnl = sum_decimals([trade.realized_pnl or Decimal("0") for trade in paper_trades])
    unrealized_pnl = sum_decimals([trade.unrealized_pnl or Decimal("0") for trade in paper_trades])
    total_pnl = realized_pnl + unrealized_pnl
    cash = starting_cash + realized_pnl
    equity = cash + unrealized_pnl
    open_positions = sum(1 for position in paper_positions if position.status == "open")
    open_trades = sum(1 for trade in paper_trades if trade.status == "open")
    closed_trades = sum(1 for trade in paper_trades if trade.status == "closed")

    as_of_candidates = [
        value
        for value in [
            *[trade.closed_at for trade in paper_trades],
            *[trade.opened_at for trade in paper_trades],
        ]
        if value is not None
    ]
    as_of = max(as_of_candidates) if as_of_candidates else None

    return {
        "starting_cash": starting_cash,
        "cash": cash,
        "equity": equity,
        "realized_pnl": realized_pnl,
        "unrealized_pnl": unrealized_pnl,
        "total_pnl": total_pnl,
        "open_positions": open_positions,
        "open_trades": open_trades,
        "closed_trades": closed_trades,
        "as_of": as_of,
    }


def _ensure_unique_ids(
    *,
    items: Sequence[object],
    entity_name: str,
    id_attr: str,
) -> None:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for item in items:
        value = getattr(item, id_attr, None)
        if not isinstance(value, str):
            continue
        if value in seen:
            duplicates.add(value)
        seen.add(value)

    if duplicates:
        detail = f"bounded_simulation_state_duplicate_{entity_name}_id"
        raise HTTPException(status_code=500, detail=detail)


def validate_bounded_paper_simulation_state(
    *,
    orders: Sequence[Order],
    execution_events: Sequence[ExecutionEvent],
    trades: Sequence[Trade],
    positions: Sequence[Position],
    portfolio_positions: Sequence[PortfolioInspectionPositionState],
) -> None:
    _ensure_unique_ids(items=orders, entity_name="order", id_attr="order_id")
    _ensure_unique_ids(items=execution_events, entity_name="execution_event", id_attr="event_id")
    _ensure_unique_ids(items=trades, entity_name="trade", id_attr="trade_id")
    _ensure_unique_ids(items=positions, entity_name="position", id_attr="position_id")

    for item in portfolio_positions:
        if item.size < Decimal("0"):
            raise HTTPException(status_code=500, detail="bounded_simulation_state_negative_portfolio_size")
        if item.average_price < Decimal("0"):
            raise HTTPException(
                status_code=500,
                detail="bounded_simulation_state_negative_portfolio_average_price",
            )


def build_paper_reconciliation_mismatches(
    *,
    orders: list[Order],
    execution_events: list[ExecutionEvent],
    trades: list[Trade],
    positions: list[Position],
    account: dict[str, object],
) -> list[dict[str, Optional[str]]]:
    mismatches: list[dict[str, Optional[str]]] = []
    orders_by_id = {order.order_id: order for order in orders}
    execution_events_by_id = {event.event_id: event for event in execution_events}
    trades_by_id = {trade.trade_id: trade for trade in trades}
    positions_by_id = {position.position_id: position for position in positions}

    for event in execution_events:
        if event.order_id not in orders_by_id:
            mismatches.append(
                {
                    "code": "execution_event_order_missing",
                    "message": f"execution event references unknown order_id={event.order_id}",
                    "entity_type": "execution_event",
                    "entity_id": event.event_id,
                }
            )

    for trade in trades:
        if trade.position_id not in positions_by_id:
            mismatches.append(
                {
                    "code": "trade_position_missing",
                    "message": f"trade references unknown position_id={trade.position_id}",
                    "entity_type": "trade",
                    "entity_id": trade.trade_id,
                }
            )

        for order_id in [*trade.opening_order_ids, *trade.closing_order_ids]:
            order = orders_by_id.get(order_id)
            if order is None:
                mismatches.append(
                    {
                        "code": "trade_order_missing",
                        "message": f"trade references unknown order_id={order_id}",
                        "entity_type": "trade",
                        "entity_id": trade.trade_id,
                    }
                )
                continue
            if order.trade_id is not None and order.trade_id != trade.trade_id:
                mismatches.append(
                    {
                        "code": "trade_order_trade_mismatch",
                        "message": f"order trade_id={order.trade_id} does not match trade_id={trade.trade_id}",
                        "entity_type": "trade",
                        "entity_id": trade.trade_id,
                    }
                )

        for event_id in trade.execution_event_ids:
            event = execution_events_by_id.get(event_id)
            if event is None:
                mismatches.append(
                    {
                        "code": "trade_execution_event_missing",
                        "message": f"trade references unknown execution_event_id={event_id}",
                        "entity_type": "trade",
                        "entity_id": trade.trade_id,
                    }
                )
                continue
            if event.trade_id is not None and event.trade_id != trade.trade_id:
                mismatches.append(
                    {
                        "code": "trade_execution_event_trade_mismatch",
                        "message": f"execution event trade_id={event.trade_id} does not match trade_id={trade.trade_id}",
                        "entity_type": "trade",
                        "entity_id": trade.trade_id,
                    }
                )

    for position in positions:
        for trade_id in position.trade_ids:
            trade = trades_by_id.get(trade_id)
            if trade is None:
                mismatches.append(
                    {
                        "code": "position_trade_missing",
                        "message": f"position references unknown trade_id={trade_id}",
                        "entity_type": "position",
                        "entity_id": position.position_id,
                    }
                )
                continue
            if trade.position_id != position.position_id:
                mismatches.append(
                    {
                        "code": "position_trade_position_mismatch",
                        "message": f"trade position_id={trade.position_id} does not match position_id={position.position_id}",
                        "entity_type": "position",
                        "entity_id": position.position_id,
                    }
                )

        for order_id in position.order_ids:
            order = orders_by_id.get(order_id)
            if order is None:
                mismatches.append(
                    {
                        "code": "position_order_missing",
                        "message": f"position references unknown order_id={order_id}",
                        "entity_type": "position",
                        "entity_id": position.position_id,
                    }
                )
                continue
            if order.position_id is not None and order.position_id != position.position_id:
                mismatches.append(
                    {
                        "code": "position_order_position_mismatch",
                        "message": f"order position_id={order.position_id} does not match position_id={position.position_id}",
                        "entity_type": "position",
                        "entity_id": position.position_id,
                    }
                )

        for event_id in position.execution_event_ids:
            event = execution_events_by_id.get(event_id)
            if event is None:
                mismatches.append(
                    {
                        "code": "position_execution_event_missing",
                        "message": f"position references unknown execution_event_id={event_id}",
                        "entity_type": "position",
                        "entity_id": position.position_id,
                    }
                )
                continue
            if event.position_id is not None and event.position_id != position.position_id:
                mismatches.append(
                    {
                        "code": "position_execution_event_position_mismatch",
                        "message": f"execution event position_id={event.position_id} does not match position_id={position.position_id}",
                        "entity_type": "position",
                        "entity_id": position.position_id,
                    }
                )

    expected_open_trades = sum(1 for trade in trades if trade.status == "open")
    expected_closed_trades = sum(1 for trade in trades if trade.status == "closed")
    expected_open_positions = sum(1 for position in positions if position.status == "open")
    expected_realized_pnl = sum_decimals([trade.realized_pnl or Decimal("0") for trade in trades])
    expected_unrealized_pnl = sum_decimals([trade.unrealized_pnl or Decimal("0") for trade in trades])
    expected_total_pnl = expected_realized_pnl + expected_unrealized_pnl
    expected_cash = account["starting_cash"] + expected_realized_pnl
    expected_equity = expected_cash + expected_unrealized_pnl

    if account["open_trades"] != expected_open_trades:
        mismatches.append(
            {
                "code": "paper_account_open_trades_mismatch",
                "message": f"open_trades={account['open_trades']} expected={expected_open_trades}",
                "entity_type": "paper_account",
                "entity_id": "account",
            }
        )
    if account["closed_trades"] != expected_closed_trades:
        mismatches.append(
            {
                "code": "paper_account_closed_trades_mismatch",
                "message": f"closed_trades={account['closed_trades']} expected={expected_closed_trades}",
                "entity_type": "paper_account",
                "entity_id": "account",
            }
        )
    if account["open_positions"] != expected_open_positions:
        mismatches.append(
            {
                "code": "paper_account_open_positions_mismatch",
                "message": f"open_positions={account['open_positions']} expected={expected_open_positions}",
                "entity_type": "paper_account",
                "entity_id": "account",
            }
        )
    if account["realized_pnl"] != expected_realized_pnl:
        mismatches.append(
            {
                "code": "paper_account_realized_pnl_mismatch",
                "message": f"realized_pnl={account['realized_pnl']} expected={expected_realized_pnl}",
                "entity_type": "paper_account",
                "entity_id": "account",
            }
        )
    if account["unrealized_pnl"] != expected_unrealized_pnl:
        mismatches.append(
            {
                "code": "paper_account_unrealized_pnl_mismatch",
                "message": f"unrealized_pnl={account['unrealized_pnl']} expected={expected_unrealized_pnl}",
                "entity_type": "paper_account",
                "entity_id": "account",
            }
        )
    if account["total_pnl"] != expected_total_pnl:
        mismatches.append(
            {
                "code": "paper_account_total_pnl_mismatch",
                "message": f"total_pnl={account['total_pnl']} expected={expected_total_pnl}",
                "entity_type": "paper_account",
                "entity_id": "account",
            }
        )
    if account["cash"] != expected_cash:
        mismatches.append(
            {
                "code": "paper_account_cash_mismatch",
                "message": f"cash={account['cash']} expected={expected_cash}",
                "entity_type": "paper_account",
                "entity_id": "account",
            }
        )
    if account["equity"] != expected_equity:
        mismatches.append(
            {
                "code": "paper_account_equity_mismatch",
                "message": f"equity={account['equity']} expected={expected_equity}",
                "entity_type": "paper_account",
                "entity_id": "account",
            }
        )

    return sorted(
        mismatches,
        key=lambda mismatch: (
            mismatch["code"] or "",
            mismatch["entity_type"] or "",
            mismatch["entity_id"] or "",
            mismatch["message"] or "",
        ),
    )


def weighted_average(*, values: list[tuple[Decimal, Decimal]]) -> Optional[Decimal]:
    total_weight = sum_decimals([weight for _, weight in values])
    if total_weight <= Decimal("0"):
        return None
    weighted_sum = sum_decimals([value * weight for value, weight in values])
    return weighted_sum / total_weight


def build_portfolio_positions_from_trades(
    *,
    trades: Sequence[Trade],
) -> list[PortfolioInspectionPositionState]:
    aggregates: dict[tuple[str, str], _AggregatedPortfolioPosition] = {}
    for trade in trades:
        if trade.status != "open":
            continue
        if trade.quantity_opened <= Decimal("0"):
            continue
        if trade.average_entry_price <= Decimal("0"):
            continue
        remaining_quantity = trade.quantity_opened - trade.quantity_closed
        if remaining_quantity <= Decimal("0"):
            continue

        key = (trade.strategy_id, trade.symbol)
        existing = aggregates.get(key)
        remaining_notional = remaining_quantity * trade.average_entry_price
        trade_unrealized_pnl = trade.unrealized_pnl or Decimal("0")

        if existing is None:
            aggregates[key] = _AggregatedPortfolioPosition(
                strategy_id=trade.strategy_id,
                symbol=trade.symbol,
                size=remaining_quantity,
                weighted_notional=remaining_notional,
                unrealized_pnl=trade_unrealized_pnl,
            )
            continue

        aggregates[key] = _AggregatedPortfolioPosition(
            strategy_id=existing.strategy_id,
            symbol=existing.symbol,
            size=existing.size + remaining_quantity,
            weighted_notional=existing.weighted_notional + remaining_notional,
            unrealized_pnl=existing.unrealized_pnl + trade_unrealized_pnl,
        )

    positions: list[PortfolioInspectionPositionState] = []
    for aggregate in aggregates.values():
        if aggregate.size <= Decimal("0"):
            continue
        average_price = aggregate.weighted_notional / aggregate.size
        positions.append(
            PortfolioInspectionPositionState(
                strategy_id=aggregate.strategy_id,
                symbol=aggregate.symbol,
                size=aggregate.size,
                average_price=average_price,
                unrealized_pnl=aggregate.unrealized_pnl,
            )
        )

    return sorted(
        positions,
        key=lambda item: (
            item.symbol,
            item.strategy_id,
            item.size,
            item.average_price,
            item.unrealized_pnl,
        ),
    )


def _filter_trades(
    *,
    trades: Sequence[Trade],
    strategy_id: Optional[str],
    symbol: Optional[str],
    position_id: Optional[str],
) -> list[Trade]:
    filtered = list(trades)
    if strategy_id is not None:
        filtered = [item for item in filtered if item.strategy_id == strategy_id]
    if symbol is not None:
        filtered = [item for item in filtered if item.symbol == symbol]
    if position_id is not None:
        filtered = [item for item in filtered if item.position_id == position_id]
    return filtered


def _filter_orders(
    *,
    orders: Sequence[Order],
    strategy_id: Optional[str],
    symbol: Optional[str],
    target_position_ids: set[str],
) -> list[Order]:
    filtered = list(orders)
    if strategy_id is not None:
        filtered = [item for item in filtered if item.strategy_id == strategy_id]
    if symbol is not None:
        filtered = [item for item in filtered if item.symbol == symbol]
    if not target_position_ids:
        return []
    return [
        item for item in filtered if item.position_id is not None and item.position_id in target_position_ids
    ]


def _filter_execution_events(
    *,
    events: Sequence[ExecutionEvent],
    strategy_id: Optional[str],
    symbol: Optional[str],
    target_position_ids: set[str],
) -> list[ExecutionEvent]:
    filtered = list(events)
    if strategy_id is not None:
        filtered = [item for item in filtered if item.strategy_id == strategy_id]
    if symbol is not None:
        filtered = [item for item in filtered if item.symbol == symbol]
    if not target_position_ids:
        return []
    return [
        item for item in filtered if item.position_id is not None and item.position_id in target_position_ids
    ]


def build_trading_core_positions(
    *,
    canonical_execution_repo: Any,
    strategy_id: Optional[str] = None,
    symbol: Optional[str] = None,
    position_id: Optional[str] = None,
    trades: Optional[list[Trade]] = None,
    orders: Optional[list[Order]] = None,
    events: Optional[list[ExecutionEvent]] = None,
) -> list[Position]:
    if trades is None:
        trades = canonical_execution_repo.list_trades(
            strategy_id=strategy_id,
            symbol=symbol,
            position_id=position_id,
            limit=1_000_000,
            offset=0,
        )
    else:
        trades = _filter_trades(
            trades=trades,
            strategy_id=strategy_id,
            symbol=symbol,
            position_id=position_id,
        )
    if not trades:
        return []

    target_position_ids = {trade.position_id for trade in trades}
    if orders is None:
        orders = canonical_execution_repo.list_orders(
            strategy_id=strategy_id,
            symbol=symbol,
            limit=1_000_000,
            offset=0,
        )
    else:
        orders = _filter_orders(
            orders=orders,
            strategy_id=strategy_id,
            symbol=symbol,
            target_position_ids=target_position_ids,
        )

    if events is None:
        events = canonical_execution_repo.list_execution_events(
            strategy_id=strategy_id,
            symbol=symbol,
            limit=1_000_000,
            offset=0,
        )
    else:
        events = _filter_execution_events(
            events=events,
            strategy_id=strategy_id,
            symbol=symbol,
            target_position_ids=target_position_ids,
        )

    orders_by_position: dict[str, list[Order]] = {}
    events_by_position: dict[str, list[ExecutionEvent]] = {}
    trades_by_position: dict[str, list[Trade]] = {}

    for trade in trades:
        trades_by_position.setdefault(trade.position_id, []).append(trade)
    for order in orders:
        if order.position_id is None:
            continue
        orders_by_position.setdefault(order.position_id, []).append(order)
    for event in events:
        if event.position_id is None:
            continue
        events_by_position.setdefault(event.position_id, []).append(event)

    positions: list[Position] = []
    for current_position_id in sorted(target_position_ids):
        position_trades = trades_by_position.get(current_position_id, [])
        if not position_trades:
            continue

        position_orders = orders_by_position.get(current_position_id, [])
        position_events = events_by_position.get(current_position_id, [])

        strategy_ids = {trade.strategy_id for trade in position_trades}
        symbols = {trade.symbol for trade in position_trades}
        directions = {trade.direction for trade in position_trades}
        if len(strategy_ids) != 1 or len(symbols) != 1 or len(directions) != 1:
            raise HTTPException(status_code=500, detail="trading_core_position_inconsistent")

        quantity_opened = sum_decimals([trade.quantity_opened for trade in position_trades])
        quantity_closed = sum_decimals([trade.quantity_closed for trade in position_trades])
        net_quantity = quantity_opened - quantity_closed

        opened_at = min(trade.opened_at for trade in position_trades)
        closed_at_candidates = [trade.closed_at for trade in position_trades if trade.closed_at is not None]

        if quantity_opened == Decimal("0") and quantity_closed == Decimal("0"):
            status: Literal["flat", "open", "closed"] = "flat"
        elif net_quantity == Decimal("0"):
            status = "closed"
        else:
            status = "open"

        average_entry_price = weighted_average(
            values=[(trade.average_entry_price, trade.quantity_opened) for trade in position_trades]
        ) or Decimal("0")

        average_exit_price = weighted_average(
            values=[
                (trade.average_exit_price, trade.quantity_closed)
                for trade in position_trades
                if trade.average_exit_price is not None and trade.quantity_closed > Decimal("0")
            ]
        )

        realized_pnl_values = [trade.realized_pnl for trade in position_trades if trade.realized_pnl is not None]
        realized_pnl = sum_decimals(realized_pnl_values) if realized_pnl_values else None

        order_ids = sorted(
            set(
                [order.order_id for order in position_orders]
                + [order_id for trade in position_trades for order_id in trade.opening_order_ids]
                + [order_id for trade in position_trades for order_id in trade.closing_order_ids]
            )
        )
        execution_event_ids = sorted(
            set(
                [event.event_id for event in position_events]
                + [event_id for trade in position_trades for event_id in trade.execution_event_ids]
            )
        )
        trade_ids = sorted([trade.trade_id for trade in position_trades])

        positions.append(
            Position.model_validate(
                {
                    "position_id": current_position_id,
                    "strategy_id": next(iter(strategy_ids)),
                    "symbol": next(iter(symbols)),
                    "direction": next(iter(directions)),
                    "status": status,
                    "opened_at": opened_at,
                    "closed_at": max(closed_at_candidates) if status == "closed" and closed_at_candidates else None,
                    "quantity_opened": quantity_opened,
                    "quantity_closed": quantity_closed,
                    "net_quantity": net_quantity,
                    "average_entry_price": average_entry_price,
                    "average_exit_price": average_exit_price,
                    "realized_pnl": realized_pnl if status == "closed" else None,
                    "order_ids": order_ids,
                    "execution_event_ids": execution_event_ids,
                    "trade_ids": trade_ids,
                }
            )
        )

    return sorted(
        positions,
        key=lambda item: (
            item.opened_at,
            item.position_id,
        ),
    )


def build_bounded_paper_simulation_state(
    *,
    canonical_execution_repo: Any,
) -> BoundedPaperSimulationState:
    orders = canonical_execution_repo.list_orders(limit=1_000_000, offset=0)
    execution_events = canonical_execution_repo.list_execution_events(limit=1_000_000, offset=0)
    trades = canonical_execution_repo.list_trades(limit=1_000_000, offset=0)
    positions = build_trading_core_positions(
        canonical_execution_repo=canonical_execution_repo,
        trades=list(trades),
        orders=list(orders),
        events=list(execution_events),
    )
    account = build_paper_account_state(
        paper_trades=list(trades),
        paper_positions=positions,
    )
    portfolio_positions = build_portfolio_positions_from_trades(trades=trades)
    mismatches = build_paper_reconciliation_mismatches(
        orders=list(orders),
        execution_events=list(execution_events),
        trades=list(trades),
        positions=positions,
        account=account,
    )

    validate_bounded_paper_simulation_state(
        orders=orders,
        execution_events=execution_events,
        trades=trades,
        positions=positions,
        portfolio_positions=portfolio_positions,
    )

    return BoundedPaperSimulationState(
        orders=tuple(orders),
        execution_events=tuple(execution_events),
        trades=tuple(trades),
        positions=tuple(positions),
        account=account,
        portfolio_positions=tuple(portfolio_positions),
        reconciliation_mismatches=tuple(mismatches),
    )


def resolve_runtime_canonical_execution_repo() -> Any | None:
    try:
        import api.main as api_main
    except Exception:
        return None
    return getattr(api_main, "canonical_execution_repo", None)


def _parse_iso_datetime(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00") if value.endswith("Z") else value
    return datetime.fromisoformat(normalized)


def _format_decimal(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return str(value)


def _build_paper_trade_outcome_payload(
    *,
    trade: Trade,
    expected_symbol: str,
    expected_strategy_id: str,
    decision_generated_at_utc: str,
) -> tuple[Literal["matched", "open", "invalid"], dict[str, Any]]:
    try:
        decision_at = _parse_iso_datetime(decision_generated_at_utc)
        opened_at = _parse_iso_datetime(trade.opened_at)
    except ValueError:
        return (
            "invalid",
            {
                "trade_id": trade.trade_id,
                "position_id": trade.position_id,
                "symbol": trade.symbol,
                "strategy_id": trade.strategy_id,
                "trade_status": trade.status,
                "opened_at_utc": trade.opened_at,
                "closed_at_utc": trade.closed_at,
                "outcome_direction": "invalid",
                "realized_pnl": _format_decimal(trade.realized_pnl),
                "unrealized_pnl": _format_decimal(trade.unrealized_pnl),
                "outcome_summary": (
                    "Matched paper trade could not satisfy deterministic timestamp parsing for bounded "
                    "decision-to-paper usefulness review."
                ),
            },
        )

    if trade.symbol != expected_symbol or trade.strategy_id != expected_strategy_id or opened_at < decision_at:
        return (
            "invalid",
            {
                "trade_id": trade.trade_id,
                "position_id": trade.position_id,
                "symbol": trade.symbol,
                "strategy_id": trade.strategy_id,
                "trade_status": trade.status,
                "opened_at_utc": trade.opened_at,
                "closed_at_utc": trade.closed_at,
                "outcome_direction": "invalid",
                "realized_pnl": _format_decimal(trade.realized_pnl),
                "unrealized_pnl": _format_decimal(trade.unrealized_pnl),
                "outcome_summary": (
                    "Matched paper trade violates the explicit symbol, strategy, or subsequent-timing "
                    "comparison contract."
                ),
            },
        )

    if trade.status == "open":
        return (
            "open",
            {
                "trade_id": trade.trade_id,
                "position_id": trade.position_id,
                "symbol": trade.symbol,
                "strategy_id": trade.strategy_id,
                "trade_status": trade.status,
                "opened_at_utc": trade.opened_at,
                "closed_at_utc": trade.closed_at,
                "outcome_direction": "open",
                "realized_pnl": _format_decimal(trade.realized_pnl),
                "unrealized_pnl": _format_decimal(trade.unrealized_pnl),
                "outcome_summary": (
                    "Matched paper trade remains open, so the bounded non-live outcome is not yet closed."
                ),
            },
        )

    realized_pnl = trade.realized_pnl or Decimal("0")
    if realized_pnl > Decimal("0"):
        outcome_direction = "favorable"
    elif realized_pnl < Decimal("0"):
        outcome_direction = "adverse"
    else:
        outcome_direction = "flat"
    return (
        "matched",
        {
            "trade_id": trade.trade_id,
            "position_id": trade.position_id,
            "symbol": trade.symbol,
            "strategy_id": trade.strategy_id,
            "trade_status": trade.status,
            "opened_at_utc": trade.opened_at,
            "closed_at_utc": trade.closed_at,
            "outcome_direction": outcome_direction,
            "realized_pnl": _format_decimal(trade.realized_pnl),
            "unrealized_pnl": _format_decimal(trade.unrealized_pnl),
            "outcome_summary": (
                "Matched paper trade closed and produced a deterministic bounded paper outcome for "
                "decision-to-paper usefulness review."
            ),
        },
    )


def build_bounded_decision_to_paper_usefulness_audit(
    *,
    canonical_execution_repo: Any | None,
    decision_card_id: str,
    generated_at_utc: str,
    symbol: str,
    strategy_id: str,
    action: str,
    qualification_state: str,
    match_reference: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(match_reference, dict):
        return None

    try:
        normalized_match_reference = BoundedDecisionToPaperUsefulnessMatchReference.model_validate(
            match_reference
        )
    except ValidationError:
        return None

    trade: Trade | None = None
    if canonical_execution_repo is not None:
        try:
            trade = canonical_execution_repo.get_trade(normalized_match_reference.paper_trade_id)
        except Exception:
            trade = None

    match_status: Literal["matched", "open", "missing", "invalid"] = "missing"
    matched_outcome: dict[str, Any] | None = None
    if trade is not None:
        match_status, matched_outcome = _build_paper_trade_outcome_payload(
            trade=trade,
            expected_symbol=symbol,
            expected_strategy_id=strategy_id,
            decision_generated_at_utc=generated_at_utc,
        )

    audit = evaluate_bounded_decision_to_paper_usefulness_audit(
        covered_case_id=decision_card_id,
        action=action,
        qualification_state=qualification_state,
        match_status=match_status,
        match_reference=normalized_match_reference.model_dump(mode="python"),
        matched_outcome=matched_outcome,
    )
    return audit.model_dump(mode="python")


def resolve_bounded_paper_linkage_status(
    *,
    canonical_execution_repo: Any | None,
    generated_at_utc: str,
    symbol: str,
    strategy_id: str,
    match_reference: dict[str, Any] | None,
) -> tuple[Literal["matched", "open", "missing", "invalid"], str | None]:
    """Return the bounded paper linkage status and resolved paper_trade_id.

    The status mirrors the decision-to-paper usefulness contract semantics
    (matched/open/missing/invalid) so the end-to-end traceability chain can
    expose explicit, deterministic linkage status across stages.
    """

    if not isinstance(match_reference, dict):
        return "missing", None

    try:
        normalized = BoundedDecisionToPaperUsefulnessMatchReference.model_validate(
            match_reference
        )
    except ValidationError:
        return "invalid", None

    paper_trade_id = normalized.paper_trade_id
    if canonical_execution_repo is None:
        return "missing", paper_trade_id

    try:
        trade = canonical_execution_repo.get_trade(paper_trade_id)
    except Exception:
        trade = None

    if trade is None:
        return "missing", paper_trade_id

    status, _ = _build_paper_trade_outcome_payload(
        trade=trade,
        expected_symbol=symbol,
        expected_strategy_id=strategy_id,
        decision_generated_at_utc=generated_at_utc,
    )
    return status, paper_trade_id


def build_bounded_signal_quality_stability_audit(
    *,
    canonical_execution_repo: Any | None,
    decision_card_id: str,
    generated_at_utc: str,
    symbol: str,
    strategy_id: str,
    signal_quality_score: float | None,
    match_reference: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Build the bounded signal-quality stability audit payload.

    The audit deterministically classifies the covered signal-quality score
    against the matched paper-trade outcome resolved through the existing
    decision-to-paper match contract. Returns ``None`` when no covered
    signal-quality score is available so the audit stays bounded to covered
    evidence only.
    """

    if signal_quality_score is None:
        return None

    normalized_match_reference: BoundedDecisionToPaperUsefulnessMatchReference | None = None
    if isinstance(match_reference, dict):
        try:
            normalized_match_reference = (
                BoundedDecisionToPaperUsefulnessMatchReference.model_validate(match_reference)
            )
        except ValidationError:
            normalized_match_reference = None

    match_status: Literal["matched", "open", "missing", "invalid"] = "missing"
    matched_outcome: dict[str, Any] | None = None
    if normalized_match_reference is not None:
        trade: Trade | None = None
        if canonical_execution_repo is not None:
            try:
                trade = canonical_execution_repo.get_trade(
                    normalized_match_reference.paper_trade_id
                )
            except Exception:
                trade = None
        if trade is not None:
            match_status, matched_outcome = _build_paper_trade_outcome_payload(
                trade=trade,
                expected_symbol=symbol,
                expected_strategy_id=strategy_id,
                decision_generated_at_utc=generated_at_utc,
            )

    audit = evaluate_bounded_signal_quality_stability_audit(
        covered_case_id=decision_card_id,
        signal_quality_score=float(signal_quality_score),
        match_status=match_status,
        match_reference=(
            normalized_match_reference.model_dump(mode="python")
            if normalized_match_reference is not None
            else None
        ),
        matched_outcome=matched_outcome,
    )
    return audit.model_dump(mode="python")


def classify_backtest_realism_calibration_status(
    realism_sensitivity_matrix: dict[str, Any] | None,
) -> tuple[BacktestRealismCalibrationStatus, str]:
    """Classify bounded backtest-realism evidence completeness for confidence calibration."""

    if not isinstance(realism_sensitivity_matrix, dict):
        return (
            "missing",
            "Covered backtest-realism sensitivity evidence is not available, so confidence "
            "calibration cannot move beyond weak bounded interpretation.",
        )

    if realism_sensitivity_matrix.get("deterministic") is not True:
        return (
            "failing",
            "Backtest-realism sensitivity evidence is present but not marked deterministic, so "
            "confidence calibration fails bounded realism review.",
        )

    profiles = realism_sensitivity_matrix.get("profiles")
    if not isinstance(profiles, list):
        return (
            "failing",
            "Backtest-realism sensitivity evidence is malformed because the profile list is missing, "
            "so confidence calibration fails bounded realism review.",
        )

    profiles_by_id = {
        profile.get("profile_id"): profile for profile in profiles if isinstance(profile, dict)
    }
    baseline = profiles_by_id.get("configured_baseline")
    cost_free = profiles_by_id.get("cost_free_reference")
    cost_stress = profiles_by_id.get("bounded_cost_stress")
    if baseline is None or cost_free is None or cost_stress is None:
        return (
            "weak",
            "Backtest-realism sensitivity evidence is present but missing one or more canonical "
            "profiles, so confidence calibration remains weak under bounded realism review.",
        )

    cost_free_summary = cost_free.get("summary")
    baseline_summary = baseline.get("summary")
    cost_stress_summary = cost_stress.get("summary")
    if not all(isinstance(item, dict) for item in (cost_free_summary, baseline_summary, cost_stress_summary)):
        return (
            "failing",
            "Backtest-realism sensitivity evidence is present but profile summaries are malformed, so "
            "confidence calibration fails bounded realism review.",
        )

    if (
        cost_free_summary.get("total_transaction_cost") != 0.0
        or cost_free_summary.get("total_commission") != 0.0
        or cost_free_summary.get("total_slippage_cost") != 0.0
    ):
        return (
            "failing",
            "Backtest-realism sensitivity evidence violates the cost-free reference boundary, so "
            "confidence calibration fails bounded realism review.",
        )

    for key in ("total_transaction_cost", "total_commission", "total_slippage_cost"):
        baseline_value = baseline_summary.get(key)
        stress_value = cost_stress_summary.get(key)
        if not isinstance(baseline_value, (int, float)) or not isinstance(stress_value, (int, float)):
            return (
                "weak",
                "Backtest-realism sensitivity evidence is present but bounded cost fields are "
                "incomplete, so confidence calibration remains weak under realism review.",
            )
        if float(stress_value) < float(baseline_value):
            return (
                "failing",
                "Backtest-realism sensitivity evidence violates bounded cost-stress directionality, "
                "so confidence calibration fails realism review.",
            )

    return (
        "stable",
        "Backtest-realism sensitivity evidence includes deterministic baseline, cost-free, and bounded "
        "cost-stress profiles with canonical directionality, so confidence calibration has stable "
        "bounded realism coverage.",
    )


def build_bounded_confidence_calibration_audit(
    *,
    canonical_execution_repo: Any | None,
    decision_card_id: str,
    generated_at_utc: str,
    symbol: str,
    strategy_id: str,
    confidence_tier: Literal["low", "medium", "high"],
    realism_sensitivity_matrix: dict[str, Any] | None,
    match_reference: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build bounded confidence calibration against realism coverage and paper outcomes."""

    backtest_realism_status, backtest_realism_reason = classify_backtest_realism_calibration_status(
        realism_sensitivity_matrix
    )

    normalized_match_reference: BoundedDecisionToPaperUsefulnessMatchReference | None = None
    if isinstance(match_reference, dict):
        try:
            normalized_match_reference = (
                BoundedDecisionToPaperUsefulnessMatchReference.model_validate(match_reference)
            )
        except ValidationError:
            normalized_match_reference = None

    match_status: Literal["matched", "open", "missing", "invalid"] = "missing"
    matched_outcome: dict[str, Any] | None = None
    if normalized_match_reference is not None:
        trade: Trade | None = None
        if canonical_execution_repo is not None:
            try:
                trade = canonical_execution_repo.get_trade(
                    normalized_match_reference.paper_trade_id
                )
            except Exception:
                trade = None
        if trade is not None:
            match_status, matched_outcome = _build_paper_trade_outcome_payload(
                trade=trade,
                expected_symbol=symbol,
                expected_strategy_id=strategy_id,
                decision_generated_at_utc=generated_at_utc,
            )

    audit = evaluate_bounded_confidence_calibration_audit(
        covered_case_id=decision_card_id,
        confidence_tier=confidence_tier,
        backtest_realism_status=backtest_realism_status,
        backtest_realism_reason=backtest_realism_reason,
        match_status=match_status,
        match_reference=(
            normalized_match_reference.model_dump(mode="python")
            if normalized_match_reference is not None
            else None
        ),
        matched_outcome=matched_outcome,
    )
    return audit.model_dump(mode="python")

```

### src\api\services\inspection_service.py
```
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from fastapi import HTTPException
from pydantic import ValidationError

from cilly_trading.engine.backtest_handoff_contract import build_professional_review_contract
from cilly_trading.engine.decision_card_contract import (
    ACTION_ENTRY_WIN_RATE_MIN,
    ACTION_EXIT_WIN_RATE_MAX,
    QUALIFICATION_HIGH_AGGREGATE_THRESHOLD,
    QUALIFICATION_MEDIUM_AGGREGATE_THRESHOLD,
    evaluate_bounded_end_to_end_traceability_chain,
    evaluate_bounded_trader_relevance_cases,
    validate_decision_card,
)
from cilly_trading.models import ExecutionEvent, Order, Position, SignalReadItemDTO, SignalReadResponseDTO, Trade
from cilly_trading.non_live_evaluation_contract import normalize_risk_rejection_reason_code

from ..models import (
    BacktestArtifactContentResponse,
    BacktestArtifactItemResponse,
    BacktestArtifactListResponse,
    BacktestReadBoundaryResponse,
    StrategyReadinessEvidenceResponse,
    StrategyReadinessEvidenceStateResponse,
    DecisionCardComponentScoreInspectionResponse,
    DecisionCardHardGateInspectionResponse,
    DecisionCardInspectionItemResponse,
    DecisionCardInspectionQuery,
    DecisionCardInspectionResponse,
    DecisionTraceResponse,
    ExecutionOrderEventItemResponse,
    ExecutionOrdersReadQuery,
    ExecutionOrdersReadResponse,
    IngestionRunItemResponse,
    JournalArtifactContentResponse,
    JournalArtifactItemResponse,
    JournalArtifactListResponse,
    PaperAccountReadResponse,
    PaperAccountStateResponse,
    PaperOperatorWorkflowBoundaryResponse,
    PaperOperatorWorkflowReadResponse,
    PaperOperatorWorkflowStepResponse,
    PaperOperatorWorkflowSurfaceResponse,
    PaperOperatorWorkflowValidationCheckResponse,
    PaperOperatorWorkflowValidationResponse,
    PaperPositionsReadQuery,
    PaperPositionsReadResponse,
    PaperReconciliationMismatchResponse,
    PaperReconciliationReadResponse,
    PaperReconciliationSummaryResponse,
    PaperTradesReadQuery,
    PaperTradesReadResponse,
    PortfolioPositionResponse,
    PortfolioPositionsResponse,
    SignalDecisionSurfaceBoundaryResponse,
    SignalDecisionSurfaceItemResponse,
    SignalDecisionSurfaceResponse,
    ScreenerResultItem,
    ScreenerResultsQuery,
    ScreenerResultsResponse,
    SignalsReadQuery,
    TradingCoreExecutionEventsReadQuery,
    TradingCoreExecutionEventsReadResponse,
    TradingCoreOrdersReadQuery,
    TradingCoreOrdersReadResponse,
    TradingCorePositionsReadQuery,
    TradingCorePositionsReadResponse,
    TradingCoreTradesReadQuery,
    TradingCoreTradesReadResponse,
)
from . import paper_inspection_service
from .analysis_service import build_strategy_metadata_response


BACKTEST_WORKFLOW_ID = "ui_bounded_backtest_entry_read"
SIGNAL_DECISION_SURFACE_WORKFLOW_ID = "ui_signal_decision_surface_v1"
SIGNAL_DECISION_BLOCKED_SCORE_THRESHOLD = 40.0
SIGNAL_DECISION_CANDIDATE_SCORE_THRESHOLD = 70.0
SIGNAL_DECISION_QUALIFICATION_POLICY_VERSION = "professional_non_live_signal_qualification.v1"
GOVERNED_BACKTEST_ARTIFACT_NAMES = frozenset(
    {
        "backtest-result.json",
        "backtest-result.sha256",
        "metrics-result.json",
        "trade-ledger.json",
        "trade-ledger.sha256",
        "equity-curve.json",
        "equity-curve.sha256",
        "performance-report.json",
        "performance-report.sha256",
    }
)


@dataclass
class InspectionServiceDependencies:
    analysis_run_repo: Any
    signal_repo: Any
    order_event_repo: Any
    canonical_execution_repo: Any
    journal_artifacts_root: Path
    default_strategy_configs: Dict[str, Dict[str, Any]]


def paginate_items(items: list[Any], *, limit: int, offset: int) -> tuple[list[Any], int]:
    page, total = paper_inspection_service.paginate_items(items=items, limit=limit, offset=offset)
    return list(page), total


def build_paper_account_state(
    *,
    paper_trades: list[Trade],
    paper_positions: list[Position],
) -> PaperAccountStateResponse:
    payload = paper_inspection_service.build_paper_account_state(
        paper_trades=paper_trades,
        paper_positions=paper_positions,
    )
    return PaperAccountStateResponse(**payload)


def build_paper_reconciliation_mismatches(
    *,
    orders: list[Order],
    execution_events: list[ExecutionEvent],
    trades: list[Trade],
    positions: list[Position],
    account: PaperAccountStateResponse,
) -> list[PaperReconciliationMismatchResponse]:
    payload = paper_inspection_service.build_paper_reconciliation_mismatches(
        orders=orders,
        execution_events=execution_events,
        trades=trades,
        positions=positions,
        account=account.model_dump(mode="python"),
    )
    return [PaperReconciliationMismatchResponse(**item) for item in payload]


def build_trading_core_positions(
    *,
    canonical_execution_repo: Any,
    strategy_id: Optional[str] = None,
    symbol: Optional[str] = None,
    position_id: Optional[str] = None,
) -> list[Position]:
    return paper_inspection_service.build_trading_core_positions(
        canonical_execution_repo=canonical_execution_repo,
        strategy_id=strategy_id,
        symbol=symbol,
        position_id=position_id,
    )


def portfolio_position_response(
    position: paper_inspection_service.PortfolioInspectionPositionState,
) -> PortfolioPositionResponse:
    return PortfolioPositionResponse(
        symbol=position.symbol,
        size=float(position.size),
        average_price=float(position.average_price),
        unrealized_pnl=float(position.unrealized_pnl),
        strategy_id=position.strategy_id,
    )


def load_bounded_paper_simulation_state(
    *,
    deps: InspectionServiceDependencies,
) -> paper_inspection_service.BoundedPaperSimulationState:
    return paper_inspection_service.build_bounded_paper_simulation_state(
        canonical_execution_repo=deps.canonical_execution_repo,
    )


def read_portfolio_positions(
    *,
    deps: InspectionServiceDependencies,
) -> PortfolioPositionsResponse:
    state = load_bounded_paper_simulation_state(deps=deps)
    items = [portfolio_position_response(position) for position in state.portfolio_positions]
    return PortfolioPositionsResponse(positions=items, total=len(items))


def read_paper_account(
    *,
    deps: InspectionServiceDependencies,
) -> PaperAccountReadResponse:
    state = load_bounded_paper_simulation_state(deps=deps)
    return PaperAccountReadResponse(
        account=PaperAccountStateResponse(**state.account),
    )


def read_paper_trades(
    *,
    params: PaperTradesReadQuery,
    deps: InspectionServiceDependencies,
) -> PaperTradesReadResponse:
    if params.trade_id:
        trade = deps.canonical_execution_repo.get_trade(params.trade_id)
        all_items = [] if trade is None else [trade]
        if params.strategy_id is not None:
            all_items = [item for item in all_items if item.strategy_id == params.strategy_id]
        if params.symbol is not None:
            all_items = [item for item in all_items if item.symbol == params.symbol]
        if params.position_id is not None:
            all_items = [item for item in all_items if item.position_id == params.position_id]
    else:
        all_items = deps.canonical_execution_repo.list_trades(
            strategy_id=params.strategy_id,
            symbol=params.symbol,
            position_id=params.position_id,
            limit=1_000_000,
            offset=0,
        )

    page, total = paginate_items(all_items, limit=params.limit, offset=params.offset)
    return PaperTradesReadResponse(
        items=page,
        limit=params.limit,
        offset=params.offset,
        total=total,
    )


def read_paper_positions(
    *,
    params: PaperPositionsReadQuery,
    deps: InspectionServiceDependencies,
) -> PaperPositionsReadResponse:
    state = load_bounded_paper_simulation_state(deps=deps)
    all_items = list(state.positions)
    if params.strategy_id is not None:
        all_items = [item for item in all_items if item.strategy_id == params.strategy_id]
    if params.symbol is not None:
        all_items = [item for item in all_items if item.symbol == params.symbol]
    if params.position_id is not None:
        all_items = [item for item in all_items if item.position_id == params.position_id]

    page, total = paginate_items(all_items, limit=params.limit, offset=params.offset)
    return PaperPositionsReadResponse(
        items=page,
        limit=params.limit,
        offset=params.offset,
        total=total,
    )


def read_paper_reconciliation(
    *,
    deps: InspectionServiceDependencies,
) -> PaperReconciliationReadResponse:
    state = load_bounded_paper_simulation_state(deps=deps)
    orders = list(state.orders)
    execution_events = list(state.execution_events)
    trades = list(state.trades)
    positions = list(state.positions)
    account = PaperAccountStateResponse(**state.account)
    mismatch_items = [
        PaperReconciliationMismatchResponse(**item)
        for item in state.reconciliation_mismatches
    ]
    return PaperReconciliationReadResponse(
        ok=not mismatch_items,
        summary=PaperReconciliationSummaryResponse(
            orders=len(orders),
            execution_events=len(execution_events),
            trades=len(trades),
            positions=len(positions),
            open_trades=sum(1 for trade in trades if trade.status == "open"),
            closed_trades=sum(1 for trade in trades if trade.status == "closed"),
            open_positions=sum(1 for position in positions if position.status == "open"),
            mismatches=len(mismatch_items),
        ),
        account=account,
        mismatch_items=mismatch_items,
    )


def read_paper_operator_workflow(
    *,
    deps: InspectionServiceDependencies,
) -> PaperOperatorWorkflowReadResponse:
    core_orders_items = deps.canonical_execution_repo.list_orders(limit=1_000_000, offset=0)
    core_events_items = deps.canonical_execution_repo.list_execution_events(limit=1_000_000, offset=0)
    core_trades_items = deps.canonical_execution_repo.list_trades(limit=1_000_000, offset=0)
    core_positions_items = build_trading_core_positions(
        canonical_execution_repo=deps.canonical_execution_repo,
        strategy_id=None,
        symbol=None,
        position_id=None,
    )
    paper_trades_items = deps.canonical_execution_repo.list_trades(limit=1_000_000, offset=0)
    paper_positions_items = build_trading_core_positions(
        canonical_execution_repo=deps.canonical_execution_repo,
        strategy_id=None,
        symbol=None,
        position_id=None,
    )
    reconciliation = read_paper_reconciliation(deps=deps)

    checks = [
        PaperOperatorWorkflowValidationCheckResponse(
            code="portfolio_to_paper_reconciliation_ok",
            ok=reconciliation.ok,
            expected="true",
            actual=str(reconciliation.ok).lower(),
        ),
        PaperOperatorWorkflowValidationCheckResponse(
            code="portfolio_to_paper_reconciliation_mismatches_zero",
            ok=reconciliation.summary.mismatches == 0,
            expected="0",
            actual=str(reconciliation.summary.mismatches),
        ),
        PaperOperatorWorkflowValidationCheckResponse(
            code="portfolio_to_paper_trades_match_canonical_trades",
            ok=paper_trades_items == core_trades_items,
            expected="true",
            actual=str(paper_trades_items == core_trades_items).lower(),
        ),
        PaperOperatorWorkflowValidationCheckResponse(
            code="portfolio_to_paper_positions_match_canonical_positions",
            ok=paper_positions_items == core_positions_items,
            expected="true",
            actual=str(paper_positions_items == core_positions_items).lower(),
        ),
    ]

    return PaperOperatorWorkflowReadResponse(
        boundary=PaperOperatorWorkflowBoundaryResponse(
            workflow_id="phase44_bounded_paper_operator",
            description=(
                "One read-only decision-to-paper and portfolio-to-paper handoff contract that "
                "validates bounded paper-readiness inputs across canonical inspection and "
                "reconciliation surfaces."
            ),
            in_scope=[
                "covered decision-card usefulness audit against explicit matched paper-trade outcomes",
                "explicit portfolio-to-paper handoff inputs from canonical orders, execution events, trades, and positions",
                "paper-facing account, trade, and position views derived from canonical portfolio evidence",
                "reconciliation validation with mismatch accounting",
                "bounded paper-readiness review with no unsupported upstream claim expansion",
            ],
            out_of_scope=[
                "live-trading readiness or approval",
                "broker execution readiness or approval",
                "broad dashboard expansion",
                "production trading operations",
            ],
        ),
        steps=[
            PaperOperatorWorkflowStepResponse(
                step=1,
                action="Inspect canonical order lifecycle entities that anchor the portfolio handoff.",
                endpoint="GET /trading-core/orders",
                expected_result=f"Canonical order evidence is readable (items={len(core_orders_items)}).",
            ),
            PaperOperatorWorkflowStepResponse(
                step=2,
                action="Inspect canonical execution lifecycle events that support the portfolio handoff.",
                endpoint="GET /trading-core/execution-events",
                expected_result=(
                    f"Canonical execution-event evidence is readable (items={len(core_events_items)})."
                ),
            ),
            PaperOperatorWorkflowStepResponse(
                step=3,
                action="Inspect canonical trade and position state that defines portfolio readiness.",
                endpoint="GET /trading-core/trades + GET /trading-core/positions",
                expected_result=(
                    f"Canonical portfolio evidence is readable (trades={len(core_trades_items)}, "
                    f"positions={len(core_positions_items)})."
                ),
            ),
            PaperOperatorWorkflowStepResponse(
                step=4,
                action="Inspect paper-facing views derived from the canonical portfolio handoff.",
                endpoint="GET /paper/trades + GET /paper/positions + GET /paper/account",
                expected_result=(
                    f"Paper-readiness views are readable (trades={len(paper_trades_items)}, "
                    f"positions={len(paper_positions_items)})."
                ),
            ),
            PaperOperatorWorkflowStepResponse(
                step=5,
                action="Run reconciliation and require zero mismatches before paper-readiness review.",
                endpoint="GET /paper/reconciliation",
                expected_result=(
                    f"Paper-readiness reconciliation ok={str(reconciliation.ok).lower()} mismatches="
                    f"{reconciliation.summary.mismatches}."
                ),
            ),
            PaperOperatorWorkflowStepResponse(
                step=6,
                action=(
                    "Inspect covered decision cards for bounded usefulness classifications against "
                    "explicit matched paper-trade outcomes."
                ),
                endpoint="GET /decision-cards",
                expected_result=(
                    "Covered decision-card outputs expose bounded usefulness classifications in "
                    "metadata without trader-validation or readiness claims."
                ),
            ),
        ],
        surfaces=PaperOperatorWorkflowSurfaceResponse(
            canonical_inspection=[
                "/decision-cards",
                "/trading-core/orders",
                "/trading-core/execution-events",
                "/trading-core/trades",
                "/trading-core/positions",
            ],
            paper_inspection=[
                "/paper/trades",
                "/paper/positions",
                "/paper/account",
            ],
            reconciliation="/paper/reconciliation",
        ),
        validation=PaperOperatorWorkflowValidationResponse(
            ok=all(check.ok for check in checks),
            checks=checks,
        ),
    )


def read_ingestion_runs(
    *,
    limit: int,
    deps: InspectionServiceDependencies,
) -> List[IngestionRunItemResponse]:
    rows = deps.analysis_run_repo.list_ingestion_runs(limit=limit)
    return [IngestionRunItemResponse(**row) for row in rows]


def read_signals(
    *,
    params: SignalsReadQuery,
    deps: InspectionServiceDependencies,
) -> SignalReadResponseDTO:
    items, total = deps.signal_repo.read_signals(
        symbol=params.symbol,
        strategy=params.strategy,
        timeframe=params.timeframe,
        ingestion_run_id=params.ingestion_run_id,
        from_=params.from_,
        to=params.to,
        sort=params.sort,
        limit=params.limit,
        offset=params.offset,
    )

    response_items: List[SignalReadItemDTO] = []
    for signal in items:
        response_items.append(
            SignalReadItemDTO(
                symbol=signal["symbol"],
                strategy=signal["strategy"],
                direction=signal["direction"],
                score=signal["score"],
                created_at=signal["timestamp"],
                stage=signal["stage"],
                entry_zone=signal.get("entry_zone"),
                confirmation_rule=signal.get("confirmation_rule"),
                timeframe=signal["timeframe"],
                market_type=signal["market_type"],
                data_source=signal["data_source"],
            )
        )

    return SignalReadResponseDTO(
        items=response_items,
        limit=params.limit,
        offset=params.offset,
        total=total,
    )


def read_signals_raw(
    *,
    params: SignalsReadQuery,
    deps: InspectionServiceDependencies,
) -> SignalReadResponseDTO:
    items, total = deps.signal_repo.read_signals_raw(
        symbol=params.symbol,
        strategy=params.strategy,
        timeframe=params.timeframe,
        ingestion_run_id=params.ingestion_run_id,
        from_=params.from_,
        to=params.to,
        sort=params.sort,
        limit=params.limit,
        offset=params.offset,
    )

    response_items: List[SignalReadItemDTO] = []
    for signal in items:
        response_items.append(
            SignalReadItemDTO(
                symbol=signal["symbol"],
                strategy=signal["strategy"],
                direction=signal["direction"],
                score=signal["score"],
                created_at=signal["timestamp"],
                stage=signal["stage"],
                entry_zone=signal.get("entry_zone"),
                confirmation_rule=signal.get("confirmation_rule"),
                timeframe=signal["timeframe"],
                market_type=signal["market_type"],
                data_source=signal["data_source"],
            )
        )

    return SignalReadResponseDTO(
        items=response_items,
        limit=params.limit,
        offset=params.offset,
        total=total,
    )


def _build_signal_decision_surface_boundary() -> SignalDecisionSurfaceBoundaryResponse:
    return SignalDecisionSurfaceBoundaryResponse(
        mode="non_live_signal_decision_surface",
        technical_decision_state_statement=(
            "This surface provides bounded technical decision-state visibility for non-live signal review only."
        ),
        trader_validation_statement=(
            "Technical decision states are not trader validation and must not be interpreted as trader approval."
        ),
        operational_readiness_statement=(
            "Technical decision states do not establish operational readiness, live trading readiness, or "
            "broker execution readiness."
        ),
        strategy_readiness_evidence=StrategyReadinessEvidenceResponse(
            bounded_scope=(
                "One bounded API/UI evidence scope for non-live technical signal decision support on /ui."
            ),
            technical=StrategyReadinessEvidenceStateResponse(
                gate="technical_implementation",
                status="technical_in_progress",
                evidence_scope=(
                    "Technical decision-state classification and professional qualification-evidence surfacing for reviewed signals."
                ),
                non_inference_note=(
                    "Technical decision-state evidence does not imply trader validation or operational readiness."
                ),
            ),
            trader_validation=StrategyReadinessEvidenceStateResponse(
                gate="trader_validation",
                status="trader_validation_not_started",
                evidence_scope=(
                    "Trader validation evidence is outside this bounded technical decision-state contract."
                ),
                non_inference_note=(
                    "Trader validation status cannot be inferred from technical decision-state output."
                ),
            ),
            operational_readiness=StrategyReadinessEvidenceStateResponse(
                gate="operational_readiness",
                status="operational_not_started",
                evidence_scope=(
                    "Operational-readiness evidence is outside this bounded technical decision-state contract."
                ),
                non_inference_note=(
                    "Operational-readiness status cannot be inferred from technical decision-state output."
                ),
            ),
            inferred_readiness_claim="prohibited",
        ),
        in_scope=[
            "bounded technical decision-state classification for reviewed signals",
            "professional non-live qualification criteria over stage, score, confirmation-rule, and entry-zone evidence",
            "explicit qualification evidence with rationale including score contribution and stage assessment",
            "explicit missing criteria and blocking-condition visibility",
            "deterministic bounded trader-relevance case evaluation for qualification and action outputs",
        ],
        out_of_scope=[
            "trader validation outcomes",
            "paper profitability or edge claims",
            "operational readiness outcomes",
            "live trading and broker execution decisions",
        ],
    )


def _build_signal_decision_surface_item(signal: Dict[str, Any]) -> SignalDecisionSurfaceItemResponse:
    score = float(signal.get("score") or 0.0)
    stage = str(signal.get("stage") or "")
    confirmation_rule = str(signal.get("confirmation_rule") or "").strip()
    entry_zone_raw = signal.get("entry_zone")
    entry_zone = entry_zone_raw if isinstance(entry_zone_raw, dict) else None

    qualification_evidence: List[str] = []
    missing_criteria: List[str] = []
    blocking_conditions: List[str] = []

    if score < SIGNAL_DECISION_BLOCKED_SCORE_THRESHOLD:
        blocking_conditions.append(
            f"Blocking score condition: score={score:.2f} below blocking threshold "
            f"{SIGNAL_DECISION_BLOCKED_SCORE_THRESHOLD:.2f}."
        )
    else:
        qualification_evidence.append(
            f"Score hard-floor evidence: score={score:.2f} meets blocking threshold "
            f"{SIGNAL_DECISION_BLOCKED_SCORE_THRESHOLD:.2f}."
        )

    if stage == "entry_confirmed":
        qualification_evidence.append("Stage evidence: stage=entry_confirmed satisfies progression stage criterion.")
    else:
        missing_criteria.append(
            f"Missing stage evidence: stage={stage or 'unknown'}; requires entry_confirmed."
        )

    if score < SIGNAL_DECISION_CANDIDATE_SCORE_THRESHOLD:
        missing_criteria.append(
            f"Missing score evidence: score={score:.2f} below candidate threshold "
            f"{SIGNAL_DECISION_CANDIDATE_SCORE_THRESHOLD:.2f}."
        )
    else:
        qualification_evidence.append(
            f"Score quality evidence: score={score:.2f} meets candidate threshold "
            f"{SIGNAL_DECISION_CANDIDATE_SCORE_THRESHOLD:.2f}."
        )

    if confirmation_rule:
        qualification_evidence.append(
            f"Confirmation-rule evidence: confirmation_rule={confirmation_rule} is explicitly available."
        )
    else:
        missing_criteria.append(
            "Missing confirmation-rule evidence: confirmation_rule must be present for professional qualification."
        )

    entry_zone_from_raw = entry_zone.get("from_") if entry_zone is not None else None
    entry_zone_to_raw = entry_zone.get("to") if entry_zone is not None else None
    try:
        entry_zone_from = float(entry_zone_from_raw) if entry_zone_from_raw is not None else None
        entry_zone_to = float(entry_zone_to_raw) if entry_zone_to_raw is not None else None
    except (TypeError, ValueError):
        entry_zone_from = None
        entry_zone_to = None

    if entry_zone_from is None or entry_zone_to is None:
        missing_criteria.append(
            "Missing entry-zone evidence: entry_zone.from_ and entry_zone.to must be present."
        )
    elif entry_zone_from >= entry_zone_to:
        blocking_conditions.append(
            "Blocking entry-zone condition: entry_zone.from_ must be lower than entry_zone.to."
        )
    else:
        qualification_evidence.append(
            f"Entry-zone evidence: entry_zone.from_={entry_zone_from:.4f} and entry_zone.to={entry_zone_to:.4f} are valid."
        )

    if blocking_conditions:
        decision_state: Literal["blocked", "watch", "paper_candidate"] = "blocked"
        rationale_summary = (
            "Blocked: one or more professional technical qualification blocking conditions failed for this non-live surface."
        )
        score_contribution = (
            f"Score {score:.2f} contributes blocking evidence against further technical progression."
        )
    elif missing_criteria:
        decision_state = "watch"
        rationale_summary = (
            "Watch: partial professional technical qualification evidence is present, but required criteria are still missing."
        )
        score_contribution = (
            f"Score {score:.2f} contributes partial evidence and keeps this signal in watch state."
        )
    else:
        decision_state = "paper_candidate"
        rationale_summary = (
            "Paper candidate: professional non-live technical qualification criteria are satisfied for bounded review progression."
        )
        score_contribution = (
            f"Score {score:.2f} contributes positive evidence for paper_candidate technical state."
        )

    stage_assessment = (
        "Stage entry_confirmed satisfies the technical stage criterion."
        if stage == "entry_confirmed"
        else f"Stage {stage or 'unknown'} does not satisfy required entry_confirmed stage criterion."
    )

    aggregate_score = score
    if aggregate_score >= QUALIFICATION_HIGH_AGGREGATE_THRESHOLD:
        confidence_tier = "high"
    elif aggregate_score >= QUALIFICATION_MEDIUM_AGGREGATE_THRESHOLD:
        confidence_tier = "medium"
    else:
        confidence_tier = "low"

    has_blocking_failure = bool(blocking_conditions)
    if has_blocking_failure:
        qualification_state: Literal["reject", "watch", "paper_candidate", "paper_approved"] = "reject"
    elif missing_criteria:
        qualification_state = "watch"
    elif confidence_tier == "high" and aggregate_score >= QUALIFICATION_HIGH_AGGREGATE_THRESHOLD:
        qualification_state = "paper_approved"
    else:
        qualification_state = "paper_candidate"

    win_rate = max(0.0, min(1.0, round(score / 100.0, 4)))
    reward_multiplier = max(0.50, min(1.50, (score + score) / 100.0))
    expected_value = max(-1.0, min(1.0, round((win_rate * reward_multiplier) - (1.0 - win_rate), 4)))

    if has_blocking_failure:
        action: Literal["entry", "exit", "ignore"] = "ignore"
    elif expected_value < 0.0:
        action = "exit"
    elif qualification_state in {"paper_candidate", "paper_approved"} and win_rate <= ACTION_EXIT_WIN_RATE_MAX:
        action = "exit"
    elif (
        confidence_tier == "low"
        or aggregate_score < QUALIFICATION_MEDIUM_AGGREGATE_THRESHOLD
        or qualification_state in {"reject", "watch"}
    ):
        action = "ignore"
    elif qualification_state in {"paper_candidate", "paper_approved"} and win_rate >= ACTION_ENTRY_WIN_RATE_MIN:
        action = "entry"
    else:
        action = "ignore"

    boundary_statement = (
        "Boundary evidence: this deterministic decision output is bounded trader-relevance validation only; "
        "it is not trader_validation evidence, not paper profitability evidence, and not live-trading readiness evidence."
    )
    trader_relevance_validation = evaluate_bounded_trader_relevance_cases(
        qualification_state=qualification_state,
        action=action,
        win_rate=win_rate,
        expected_value=expected_value,
        qualification_summary=(
            "Qualification output remains explicitly bounded to paper-trading scope for technical review."
        ),
        rationale_summary=rationale_summary,
        final_explanation=boundary_statement,
        qualification_evidence=qualification_evidence + [boundary_statement],
        missing_criteria=missing_criteria,
        blocking_conditions=blocking_conditions,
    )
    trader_relevance_case_status = ", ".join(
        f"{item.case_id}={item.evidence_status}"
        for item in trader_relevance_validation.evaluations
    )
    qualification_evidence.append(
        "Bounded trader-relevance case review "
        f"(contract={trader_relevance_validation.contract_id}, "
        f"version={trader_relevance_validation.contract_version}, "
        f"overall={trader_relevance_validation.overall_status}): "
        f"{trader_relevance_case_status}."
    )
    qualification_evidence.append(boundary_statement)

    return SignalDecisionSurfaceItemResponse(
        symbol=str(signal.get("symbol") or ""),
        strategy=str(signal.get("strategy") or ""),
        direction=str(signal.get("direction") or ""),
        score=score,
        created_at=str(signal.get("timestamp") or ""),
        stage=stage,
        timeframe=str(signal.get("timeframe") or ""),
        market_type=str(signal.get("market_type") or ""),
        data_source=str(signal.get("data_source") or ""),
        decision_state=decision_state,
        qualification_state=qualification_state,
        action=action,
        win_rate=win_rate,
        expected_value=expected_value,
        qualification_policy_version=SIGNAL_DECISION_QUALIFICATION_POLICY_VERSION,
        rationale_summary=rationale_summary,
        qualification_evidence=qualification_evidence,
        score_contribution=score_contribution,
        stage_assessment=stage_assessment,
        missing_criteria=missing_criteria,
        blocking_conditions=blocking_conditions,
    )


def read_signal_decision_surface(
    *,
    params: SignalsReadQuery,
    deps: InspectionServiceDependencies,
) -> SignalDecisionSurfaceResponse:
    items, total = deps.signal_repo.read_signals(
        symbol=params.symbol,
        strategy=params.strategy,
        timeframe=params.timeframe,
        ingestion_run_id=params.ingestion_run_id,
        from_=params.from_,
        to=params.to,
        sort=params.sort,
        limit=params.limit,
        offset=params.offset,
    )

    decision_items = [_build_signal_decision_surface_item(signal) for signal in items]
    return SignalDecisionSurfaceResponse(
        workflow_id=SIGNAL_DECISION_SURFACE_WORKFLOW_ID,
        boundary=_build_signal_decision_surface_boundary(),
        items=decision_items,
        limit=params.limit,
        offset=params.offset,
        total=total,
    )


def read_execution_orders(
    *,
    params: ExecutionOrdersReadQuery,
    deps: InspectionServiceDependencies,
) -> ExecutionOrdersReadResponse:
    items, total = deps.order_event_repo.read_order_events(
        symbol=params.symbol,
        strategy=params.strategy,
        run_id=params.run_id,
        order_id=params.order_id,
        limit=params.limit,
        offset=params.offset,
    )

    response_items = [ExecutionOrderEventItemResponse(**item) for item in items]
    return ExecutionOrdersReadResponse(
        items=response_items,
        limit=params.limit,
        offset=params.offset,
        total=total,
    )


def read_trading_core_orders(
    *,
    params: TradingCoreOrdersReadQuery,
    deps: InspectionServiceDependencies,
) -> TradingCoreOrdersReadResponse:
    if params.order_id:
        order = deps.canonical_execution_repo.get_order(params.order_id)
        all_items = [] if order is None else [order]
        if params.strategy_id is not None:
            all_items = [item for item in all_items if item.strategy_id == params.strategy_id]
        if params.symbol is not None:
            all_items = [item for item in all_items if item.symbol == params.symbol]
    else:
        all_items = deps.canonical_execution_repo.list_orders(
            strategy_id=params.strategy_id,
            symbol=params.symbol,
            limit=1_000_000,
            offset=0,
        )

    page, total = paginate_items(all_items, limit=params.limit, offset=params.offset)
    return TradingCoreOrdersReadResponse(
        items=page,
        limit=params.limit,
        offset=params.offset,
        total=total,
    )


def read_trading_core_execution_events(
    *,
    params: TradingCoreExecutionEventsReadQuery,
    deps: InspectionServiceDependencies,
) -> TradingCoreExecutionEventsReadResponse:
    all_items = deps.canonical_execution_repo.list_execution_events(
        strategy_id=params.strategy_id,
        symbol=params.symbol,
        order_id=params.order_id,
        trade_id=params.trade_id,
        limit=1_000_000,
        offset=0,
    )
    page, total = paginate_items(all_items, limit=params.limit, offset=params.offset)
    return TradingCoreExecutionEventsReadResponse(
        items=page,
        limit=params.limit,
        offset=params.offset,
        total=total,
    )


def read_trading_core_trades(
    *,
    params: TradingCoreTradesReadQuery,
    deps: InspectionServiceDependencies,
) -> TradingCoreTradesReadResponse:
    if params.trade_id:
        trade = deps.canonical_execution_repo.get_trade(params.trade_id)
        all_items = [] if trade is None else [trade]
        if params.strategy_id is not None:
            all_items = [item for item in all_items if item.strategy_id == params.strategy_id]
        if params.symbol is not None:
            all_items = [item for item in all_items if item.symbol == params.symbol]
        if params.position_id is not None:
            all_items = [item for item in all_items if item.position_id == params.position_id]
    else:
        all_items = deps.canonical_execution_repo.list_trades(
            strategy_id=params.strategy_id,
            symbol=params.symbol,
            position_id=params.position_id,
            limit=1_000_000,
            offset=0,
        )

    page, total = paginate_items(all_items, limit=params.limit, offset=params.offset)
    return TradingCoreTradesReadResponse(
        items=page,
        limit=params.limit,
        offset=params.offset,
        total=total,
    )


def read_trading_core_positions(
    *,
    params: TradingCorePositionsReadQuery,
    deps: InspectionServiceDependencies,
) -> TradingCorePositionsReadResponse:
    all_items = build_trading_core_positions(
        canonical_execution_repo=deps.canonical_execution_repo,
        strategy_id=params.strategy_id,
        symbol=params.symbol,
        position_id=params.position_id,
    )
    page, total = paginate_items(all_items, limit=params.limit, offset=params.offset)
    return TradingCorePositionsReadResponse(
        items=page,
        limit=params.limit,
        offset=params.offset,
        total=total,
    )


def read_screener_results(
    *,
    params: ScreenerResultsQuery,
    deps: InspectionServiceDependencies,
) -> ScreenerResultsResponse:
    items, total = deps.signal_repo.read_screener_results(
        strategy=params.strategy,
        timeframe=params.timeframe,
        min_score=params.min_score,
        limit=params.limit,
        offset=params.offset,
    )
    response_items = [ScreenerResultItem(**item) for item in items]

    return ScreenerResultsResponse(
        items=response_items,
        limit=params.limit,
        offset=params.offset,
        total=total,
    )


def iter_journal_artifact_files(*, journal_artifacts_root: Path) -> List[tuple[str, Path]]:
    if not journal_artifacts_root.exists() or not journal_artifacts_root.is_dir():
        return []

    artifact_files: List[tuple[str, Path]] = []
    for run_dir in journal_artifacts_root.iterdir():
        if not run_dir.is_dir():
            continue
        run_id = run_dir.name
        for artifact_file in run_dir.iterdir():
            if artifact_file.is_file():
                artifact_files.append((run_id, artifact_file))
    return artifact_files


def resolve_journal_artifact_path(
    *,
    run_id: str,
    artifact_name: str,
    journal_artifacts_root: Path,
) -> Path:
    if "/" in run_id or "\\" in run_id:
        raise HTTPException(status_code=404, detail="journal_artifact_not_found")
    if "/" in artifact_name or "\\" in artifact_name:
        raise HTTPException(status_code=404, detail="journal_artifact_not_found")

    candidate = journal_artifacts_root / run_id / artifact_name
    try:
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="journal_artifact_not_found") from None

    expected_parent = (journal_artifacts_root / run_id).resolve()
    if resolved.parent != expected_parent or not resolved.is_file():
        raise HTTPException(status_code=404, detail="journal_artifact_not_found")

    return resolved


def read_journal_artifact_content(path: Path) -> tuple[Literal["json", "text"], Any]:
    raw_text = path.read_text(encoding="utf-8")
    try:
        return "json", json.loads(raw_text)
    except json.JSONDecodeError:
        return "text", raw_text


def extract_trace_entries(content: Any) -> tuple[Optional[str], List[Dict[str, Any]]]:
    trace_id: Optional[str] = None
    entries: list[Any] = []

    if isinstance(content, dict):
        trace_id_value = content.get("trace_id")
        if isinstance(trace_id_value, str):
            trace_id = trace_id_value

        candidate = None
        if "decision_trace" in content:
            candidate = content.get("decision_trace")
        elif "trace_entries" in content:
            candidate = content.get("trace_entries")
        elif "entries" in content:
            candidate = content.get("entries")

        if isinstance(candidate, dict):
            maybe_trace_id = candidate.get("trace_id")
            if isinstance(maybe_trace_id, str):
                trace_id = maybe_trace_id
            maybe_entries = candidate.get("entries")
            if isinstance(maybe_entries, list):
                entries = maybe_entries
        elif isinstance(candidate, list):
            entries = candidate
    elif isinstance(content, list):
        entries = content

    normalized_entries: List[Dict[str, Any]] = []
    for entry in entries:
        if isinstance(entry, dict):
            normalized_entries.append(entry)
        else:
            normalized_entries.append({"value": entry})
    return trace_id, normalized_entries


def _normalize_trace_reason_codes(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized_entries: List[Dict[str, Any]] = []
    candidate_fields = (
        "normalized_reason_code",
        "reason_code",
        "reason",
        "failure_reason",
        "rejection_reason",
        "risk_reason",
        "risk_reason_code",
    )

    for entry in entries:
        normalized_entry = dict(entry)
        candidate: str | None = None
        for field in candidate_fields:
            value = normalized_entry.get(field)
            if isinstance(value, str) and value.strip():
                candidate = value.strip()
                break
        if candidate is not None:
            try:
                normalized_entry["normalized_reason_code"] = (
                    normalize_risk_rejection_reason_code(candidate)
                )
            except ValueError:
                pass
        normalized_entries.append(normalized_entry)

    return normalized_entries


def extract_decision_card_candidates(content: Any) -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []

    def _walk(node: Any) -> None:
        if isinstance(node, dict):
            if {
                "contract_version",
                "decision_card_id",
                "generated_at_utc",
                "hard_gates",
                "score",
                "qualification",
                "rationale",
            }.issubset(node.keys()):
                candidates.append(node)
            for value in node.values():
                if isinstance(value, (dict, list)):
                    _walk(value)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(content)
    return candidates


def matches_decision_card_review_state(
    *,
    qualification_state: str,
    review_state: Optional[Literal["ranked", "blocked", "approved"]],
) -> bool:
    if review_state is None:
        return True
    if review_state == "blocked":
        return qualification_state == "reject"
    if review_state == "approved":
        return qualification_state == "paper_approved"
    return qualification_state != "reject"


def decision_card_item_sort_key(
    item: DecisionCardInspectionItemResponse,
    *,
    sort: Literal["generated_at_desc", "generated_at_asc"],
) -> tuple[float, str, str, str]:
    generated_at = datetime.fromisoformat(
        item.generated_at_utc.replace("Z", "+00:00")
        if item.generated_at_utc.endswith("Z")
        else item.generated_at_utc
    )
    timestamp = generated_at.timestamp()
    if sort == "generated_at_desc":
        timestamp = -timestamp
    return (timestamp, item.decision_card_id, item.run_id, item.artifact_name)


def _extract_realism_sensitivity_matrix(content: Any) -> dict[str, Any] | None:
    if isinstance(content, dict):
        metrics_baseline = content.get("metrics_baseline")
        if isinstance(metrics_baseline, dict):
            matrix = metrics_baseline.get("realism_sensitivity_matrix")
            if isinstance(matrix, dict):
                return matrix
        for value in content.values():
            matrix = _extract_realism_sensitivity_matrix(value)
            if matrix is not None:
                return matrix
        return None
    if isinstance(content, list):
        for value in content:
            matrix = _extract_realism_sensitivity_matrix(value)
            if matrix is not None:
                return matrix
    return None


def _load_run_realism_sensitivity_matrix(run_dir: Path) -> dict[str, Any] | None:
    if not run_dir.exists():
        return None

    for artifact_path in sorted(run_dir.iterdir(), key=lambda path: path.name):
        if artifact_path.suffix.casefold() != ".json" or not artifact_path.is_file():
            continue
        content_type, content = read_journal_artifact_content(artifact_path)
        if content_type != "json":
            continue
        matrix = _extract_realism_sensitivity_matrix(content)
        if matrix is not None:
            return matrix
    return None


def build_decision_card_inspection_items(
    *,
    params: DecisionCardInspectionQuery,
    journal_artifacts_root: Path,
) -> List[DecisionCardInspectionItemResponse]:
    items: List[DecisionCardInspectionItemResponse] = []
    seen: set[tuple[str, str, str, str]] = set()
    run_realism_cache: dict[str, dict[str, Any] | None] = {}

    for run_id, artifact_path in iter_journal_artifact_files(
        journal_artifacts_root=journal_artifacts_root
    ):
        if params.run_id is not None and run_id != params.run_id:
            continue

        content_type, content = read_journal_artifact_content(artifact_path)
        if content_type != "json":
            continue

        for candidate in extract_decision_card_candidates(content):
            try:
                card = validate_decision_card(candidate)
            except (ValidationError, ValueError):
                continue

            if params.decision_card_id is not None and card.decision_card_id != params.decision_card_id:
                continue
            if params.symbol is not None and card.symbol != params.symbol:
                continue
            if params.strategy_id is not None and card.strategy_id != params.strategy_id:
                continue
            if (
                params.qualification_state is not None
                and card.qualification.state != params.qualification_state
            ):
                continue
            if not matches_decision_card_review_state(
                qualification_state=card.qualification.state,
                review_state=params.review_state,
            ):
                continue

            dedupe_key = (
                run_id,
                artifact_path.name,
                card.decision_card_id,
                card.to_canonical_json(),
            )
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)

            metadata = dict(card.metadata)
            canonical_repo = paper_inspection_service.resolve_runtime_canonical_execution_repo()
            if run_id not in run_realism_cache:
                run_realism_cache[run_id] = _load_run_realism_sensitivity_matrix(
                    artifact_path.parent
                )
            realism_sensitivity_matrix = run_realism_cache[run_id]
            match_reference = metadata.get("bounded_decision_to_paper_match")
            usefulness_audit = paper_inspection_service.build_bounded_decision_to_paper_usefulness_audit(
                canonical_execution_repo=canonical_repo,
                decision_card_id=card.decision_card_id,
                generated_at_utc=card.generated_at_utc,
                symbol=card.symbol,
                strategy_id=card.strategy_id,
                action=card.action,
                qualification_state=card.qualification.state,
                match_reference=match_reference,
            )
            if usefulness_audit is not None:
                metadata["bounded_decision_to_paper_usefulness_audit"] = usefulness_audit

            signal_quality_score: float | None = None
            for component in card.score.component_scores:
                if component.category == "signal_quality":
                    signal_quality_score = float(component.score)
                    break
            stability_audit = (
                paper_inspection_service.build_bounded_signal_quality_stability_audit(
                    canonical_execution_repo=canonical_repo,
                    decision_card_id=card.decision_card_id,
                    generated_at_utc=card.generated_at_utc,
                    symbol=card.symbol,
                    strategy_id=card.strategy_id,
                    signal_quality_score=signal_quality_score,
                    match_reference=match_reference,
                )
            )
            if stability_audit is not None:
                metadata["bounded_signal_quality_stability_audit"] = stability_audit

            metadata["bounded_confidence_calibration_audit"] = (
                paper_inspection_service.build_bounded_confidence_calibration_audit(
                    canonical_execution_repo=canonical_repo,
                    decision_card_id=card.decision_card_id,
                    generated_at_utc=card.generated_at_utc,
                    symbol=card.symbol,
                    strategy_id=card.strategy_id,
                    confidence_tier=card.score.confidence_tier,
                    realism_sensitivity_matrix=realism_sensitivity_matrix,
                    match_reference=match_reference,
                )
            )

            paper_match_status, paper_trade_id = (
                paper_inspection_service.resolve_bounded_paper_linkage_status(
                    canonical_execution_repo=canonical_repo,
                    generated_at_utc=card.generated_at_utc,
                    symbol=card.symbol,
                    strategy_id=card.strategy_id,
                    match_reference=match_reference,
                )
            )
            analysis_run_id_meta = card.metadata.get("analysis_run_id")
            analysis_run_id = (
                analysis_run_id_meta
                if isinstance(analysis_run_id_meta, str) and len(analysis_run_id_meta) > 0
                else None
            )
            traceability_chain = evaluate_bounded_end_to_end_traceability_chain(
                decision_card_id=card.decision_card_id,
                generated_at_utc=card.generated_at_utc,
                symbol=card.symbol,
                strategy_id=card.strategy_id,
                qualification_state=card.qualification.state,
                action=card.action,
                analysis_run_id=analysis_run_id,
                paper_trade_id=paper_trade_id,
                paper_match_status=paper_match_status,
            )

            items.append(
                DecisionCardInspectionItemResponse(
                    run_id=run_id,
                    artifact_name=artifact_path.name,
                    decision_card_id=card.decision_card_id,
                    generated_at_utc=card.generated_at_utc,
                    symbol=card.symbol,
                    strategy_id=card.strategy_id,
                    qualification_state=card.qualification.state,
                    action=card.action,
                    win_rate=card.score.win_rate,
                    expected_value=card.score.expected_value,
                    qualification_color=card.qualification.color,
                    qualification_summary=card.qualification.summary,
                    aggregate_score=card.score.aggregate_score,
                    confidence_tier=card.score.confidence_tier,
                    hard_gate_policy_version=card.hard_gates.policy_version,
                    hard_gate_blocking_failure=card.hard_gates.has_blocking_failure,
                    hard_gates=[
                        DecisionCardHardGateInspectionResponse(**gate.model_dump(mode="python"))
                        for gate in card.hard_gates.gates
                    ],
                    component_scores=[
                        DecisionCardComponentScoreInspectionResponse(
                            **component.model_dump(mode="python")
                        )
                        for component in card.score.component_scores
                    ],
                    rationale_summary=card.rationale.summary,
                    gate_explanations=list(card.rationale.gate_explanations),
                    score_explanations=list(card.rationale.score_explanations),
                    final_explanation=card.rationale.final_explanation,
                    metadata=metadata,
                    traceability_chain=traceability_chain.model_dump(mode="python"),
                )
            )

    items.sort(key=lambda item: decision_card_item_sort_key(item, sort=params.sort))
    return items


def read_journal_artifacts(
    *,
    limit: int,
    offset: int,
    journal_artifacts_root: Path,
) -> JournalArtifactListResponse:
    files = iter_journal_artifact_files(journal_artifacts_root=journal_artifacts_root)
    files.sort(key=lambda item: item[1].stat().st_mtime, reverse=True)

    total = len(files)
    page = files[offset : offset + limit]
    items: List[JournalArtifactItemResponse] = []
    for run_id, path in page:
        stat = path.stat()
        items.append(
            JournalArtifactItemResponse(
                run_id=run_id,
                artifact_name=path.name,
                size_bytes=stat.st_size,
                modified_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            )
        )

    return JournalArtifactListResponse(items=items, total=total)


def read_journal_artifact_file_content(
    *,
    run_id: str,
    artifact_name: str,
    journal_artifacts_root: Path,
) -> JournalArtifactContentResponse:
    path = resolve_journal_artifact_path(
        run_id=run_id,
        artifact_name=artifact_name,
        journal_artifacts_root=journal_artifacts_root,
    )
    content_type, content = read_journal_artifact_content(path)
    return JournalArtifactContentResponse(
        run_id=run_id,
        artifact_name=artifact_name,
        content_type=content_type,
        content=content,
    )


def _build_backtest_read_boundary() -> BacktestReadBoundaryResponse:
    review_contract = build_professional_review_contract()
    return BacktestReadBoundaryResponse(
        mode="non_live_backtest_read_only",
        review_contract_id=review_contract["contract_id"],
        review_contract_version=review_contract["contract_version"],
        review_required_evidence=list(review_contract["required_visible_evidence"]),
        review_comparison_axes=list(review_contract["comparison_axes"]),
        decision_relevance_statement=review_contract["decision_relevance_statement"],
        readiness_non_inference_statement=review_contract["readiness_non_inference_statement"],
        technical_availability_statement=(
            "This flow only confirms technical availability of governed backtest artifacts."
        ),
        trader_validation_statement=(
            "Technical artifact availability is not trader validation and must not be interpreted "
            "as strategy approval."
        ),
        operational_readiness_statement=(
            "Backtest artifact visibility is not operational readiness evidence for live or broker "
            "execution."
        ),
        strategy_readiness_evidence=StrategyReadinessEvidenceResponse(
            bounded_scope=(
                "One bounded API/UI evidence surfacing scope for governed non-live backtest "
                "artifact inspection."
            ),
            technical=StrategyReadinessEvidenceStateResponse(
                gate="technical_implementation",
                status="technical_in_progress",
                evidence_scope=(
                    "API/UI contract and test evidence for read-only governed backtest artifact "
                    "visibility."
                ),
                non_inference_note=(
                    "Technical evidence does not imply trader validation, operational readiness, "
                    "live trading, or production readiness."
                ),
            ),
            trader_validation=StrategyReadinessEvidenceStateResponse(
                gate="trader_validation",
                status="trader_validation_not_started",
                evidence_scope=(
                    "Trader-owned validation evidence is outside this API/UI technical contract."
                ),
                non_inference_note=(
                    "Trader validation status cannot be inferred from technical artifact "
                    "visibility."
                ),
            ),
            operational_readiness=StrategyReadinessEvidenceStateResponse(
                gate="operational_readiness",
                status="operational_not_started",
                evidence_scope=(
                    "Operational-readiness evidence is outside this API/UI technical contract and "
                    "requires governed runbook acceptance artifacts."
                ),
                non_inference_note=(
                    "Operational-readiness status cannot be inferred from technical or "
                    "trader-validation evidence fields."
                ),
            ),
            inferred_readiness_claim="prohibited",
        ),
        in_scope=[
            "read-only listing of governed backtest artifacts",
            "read-only artifact content preview for governed backtest artifacts",
            "bounded non-live technical inspection through /ui",
        ],
        out_of_scope=[
            "live trading and broker connectivity",
            "order execution enablement",
            "trader validation and operational readiness claims",
        ],
    )


def _is_governed_backtest_artifact_name(artifact_name: str) -> bool:
    return artifact_name in GOVERNED_BACKTEST_ARTIFACT_NAMES


def read_backtest_artifacts(
    *,
    limit: int,
    offset: int,
    run_id: Optional[str],
    journal_artifacts_root: Path,
) -> BacktestArtifactListResponse:
    files = iter_journal_artifact_files(journal_artifacts_root=journal_artifacts_root)
    filtered: List[tuple[str, Path]] = []
    for item_run_id, path in files:
        if run_id is not None and item_run_id != run_id:
            continue
        if not _is_governed_backtest_artifact_name(path.name):
            continue
        filtered.append((item_run_id, path))
    filtered.sort(key=lambda item: item[1].stat().st_mtime, reverse=True)

    total = len(filtered)
    page = filtered[offset : offset + limit]
    items: List[BacktestArtifactItemResponse] = []
    for item_run_id, path in page:
        stat = path.stat()
        items.append(
            BacktestArtifactItemResponse(
                run_id=item_run_id,
                artifact_name=path.name,
                size_bytes=stat.st_size,
                modified_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            )
        )

    return BacktestArtifactListResponse(
        workflow_id=BACKTEST_WORKFLOW_ID,
        boundary=_build_backtest_read_boundary(),
        items=items,
        limit=limit,
        offset=offset,
        total=total,
    )


def read_backtest_artifact_content(
    *,
    run_id: str,
    artifact_name: str,
    journal_artifacts_root: Path,
) -> BacktestArtifactContentResponse:
    if not _is_governed_backtest_artifact_name(artifact_name):
        raise HTTPException(status_code=404, detail="backtest_artifact_not_found")
    path = resolve_journal_artifact_path(
        run_id=run_id,
        artifact_name=artifact_name,
        journal_artifacts_root=journal_artifacts_root,
    )
    content_type, content = read_journal_artifact_content(path)
    return BacktestArtifactContentResponse(
        workflow_id=BACKTEST_WORKFLOW_ID,
        boundary=_build_backtest_read_boundary(),
        run_id=run_id,
        artifact_name=artifact_name,
        content_type=content_type,
        content=content,
    )


def read_decision_trace(
    *,
    run_id: str,
    artifact_name: str,
    journal_artifacts_root: Path,
) -> DecisionTraceResponse:
    path = resolve_journal_artifact_path(
        run_id=run_id,
        artifact_name=artifact_name,
        journal_artifacts_root=journal_artifacts_root,
    )
    _, content = read_journal_artifact_content(path)
    trace_id, entries = extract_trace_entries(content)
    entries = _normalize_trace_reason_codes(entries)
    return DecisionTraceResponse(
        run_id=run_id,
        artifact_name=artifact_name,
        trace_id=trace_id,
        entries=entries,
        total_entries=len(entries),
    )


def read_decision_cards(
    *,
    params: DecisionCardInspectionQuery,
    journal_artifacts_root: Path,
) -> DecisionCardInspectionResponse:
    all_items = build_decision_card_inspection_items(
        params=params,
        journal_artifacts_root=journal_artifacts_root,
    )
    page, total = paginate_items(all_items, limit=params.limit, offset=params.offset)
    return DecisionCardInspectionResponse(
        items=page,
        limit=params.limit,
        offset=params.offset,
        total=total,
    )


def read_strategy_metadata(
    *,
    default_strategy_configs: Dict[str, Dict[str, Any]],
) -> Any:
    return build_strategy_metadata_response(default_strategy_configs=default_strategy_configs)

```

### tests\cilly_trading\engine\test_decision_card_contract.py
```
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from cilly_trading.engine.decision_card_contract import (
    CONFIDENCE_CALIBRATION_CONTRACT_ID,
    CONFIDENCE_CALIBRATION_CONTRACT_VERSION,
    DECISION_CARD_CONTRACT_VERSION,
    BoundedConfidenceCalibrationAudit,
    DecisionCard,
    evaluate_bounded_confidence_calibration_audit,
    serialize_decision_card,
    validate_decision_card,
)


def _valid_payload(
    *,
    qualification_state: str = "paper_candidate",
    qualification_color: str = "yellow",
    action: str = "entry",
) -> dict[str, Any]:
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
            "win_rate": 0.58,
            "expected_value": 0.0564,
        },
        "action": action,
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
    assert card.score.win_rate == 0.58
    assert card.score.expected_value == 0.0564
    assert card.action == "entry"
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

    with pytest.raises(ValidationError, match="Qualification state must match deterministic resolution"):
        validate_decision_card(payload)


@pytest.mark.parametrize(
    ("state", "color", "action"),
    [
        ("paper_approved", "green", "entry"),
        ("paper_candidate", "yellow", "entry"),
        ("watch", "yellow", "ignore"),
        ("reject", "red", "ignore"),
    ],
)
def test_representative_qualification_payloads_validate(state: str, color: str, action: str) -> None:
    payload = _valid_payload(qualification_state=state, qualification_color=color, action=action)
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
        payload["score"]["aggregate_score"] = 58.0
        payload["qualification"]["summary"] = (
            "Opportunity requires further evidence before paper-trading qualification."
        )
    if state == "paper_approved":
        payload["score"]["component_scores"] = [
            {
                "category": "execution_readiness",
                "score": 82.0,
                "rationale": "Execution assumptions remain deterministic and bounded",
                "evidence": ["slippage_bps=9", "commission_per_order=1.00"],
            },
            {
                "category": "portfolio_fit",
                "score": 84.0,
                "rationale": "Portfolio concentration constraints remain satisfied",
                "evidence": ["sector_weight_pct=0.18", "sector_limit_pct=0.25"],
            },
            {
                "category": "signal_quality",
                "score": 88.0,
                "rationale": "Signal quality remains consistent across recent windows",
                "evidence": ["signal_hit_rate=0.64", "window_days=90"],
            },
            {
                "category": "backtest_quality",
                "score": 84.0,
                "rationale": "Backtest quality supports bounded forward expectation",
                "evidence": ["sharpe=1.48", "profit_factor=1.68"],
            },
            {
                "category": "risk_alignment",
                "score": 90.0,
                "rationale": "Risk controls align with per-trade and portfolio policy",
                "evidence": ["risk_per_trade_pct=0.005", "max_risk_pct=0.01"],
            },
        ]
        payload["score"]["aggregate_score"] = 86.2
        payload["score"]["win_rate"] = 0.66
        payload["score"]["expected_value"] = 0.2872
        payload["score"]["confidence_tier"] = "high"
        payload["score"]["confidence_reason"] = (
            "Aggregate score and component thresholds satisfy high confidence with explicit evidence."
        )
        payload["qualification"]["summary"] = "Opportunity is approved for bounded paper-trading only."

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


def test_negative_validation_rejects_reject_without_blocking_failure() -> None:
    payload = _valid_payload(qualification_state="reject", qualification_color="red")

    with pytest.raises(ValidationError, match="Qualification state must match deterministic resolution"):
        validate_decision_card(payload)


def test_non_blocking_gate_failure_does_not_force_reject() -> None:
    payload = _valid_payload(qualification_state="paper_candidate", qualification_color="yellow")
    payload["hard_gates"]["gates"][0]["status"] = "fail"
    payload["hard_gates"]["gates"][0]["blocking"] = False
    payload["hard_gates"]["gates"][0]["failure_reason"] = "Observed drift requires monitoring"

    card = validate_decision_card(payload)
    assert card.hard_gates.has_blocking_failure is False
    assert card.qualification.state == "paper_candidate"


def test_confidence_inflation_phrases_are_rejected() -> None:
    for phrase in ("high certainty", "confirmed opportunity", "validated outcome", "strong certainty"):
        payload = _valid_payload()
        payload["score"]["confidence_reason"] = (
            f"Aggregate component threshold evidence supports outcome with {phrase}."
        )
        with pytest.raises(ValidationError, match="confidence_reason contains unsupported claim language"):
            validate_decision_card(payload)


def test_negative_validation_rejects_negative_expected_value_entry_action() -> None:
    payload = _valid_payload(action="entry")
    payload["score"]["expected_value"] = -0.01

    with pytest.raises(ValidationError, match="Negative expected value must not resolve to entry action"):
        validate_decision_card(payload)


def test_negative_validation_rejects_action_that_violates_deterministic_resolution() -> None:
    payload = _valid_payload(qualification_state="watch", qualification_color="yellow", action="entry")
    payload["score"]["confidence_tier"] = "low"
    payload["score"]["aggregate_score"] = 55.0

    with pytest.raises(ValidationError, match="Decision action must match deterministic resolution"):
        validate_decision_card(payload)


@pytest.mark.parametrize("forbidden_phrase", ["trader validation", "live approval", "production readiness"])
def test_negative_validation_rejects_additional_forbidden_claim_phrases(forbidden_phrase: str) -> None:
    payload = _valid_payload()
    payload["score"]["confidence_reason"] = (
        f"Aggregate component threshold evidence supports confidence without {forbidden_phrase}."
    )

    with pytest.raises(ValidationError, match="confidence_reason contains unsupported claim language"):
        validate_decision_card(payload)


@pytest.mark.parametrize(
    ("confidence_tier", "realism_status", "match_status", "outcome_direction", "expected"),
    [
        ("high", "stable", "matched", "favorable", "stable"),
        ("high", "stable", "matched", "adverse", "failing"),
        ("high", "weak", "matched", "favorable", "weak"),
        ("medium", "weak", "matched", "favorable", "stable"),
        ("low", "failing", "matched", "adverse", "stable"),
        ("low", "stable", "matched", "favorable", "weak"),
        ("medium", "missing", "missing", None, "weak"),
    ],
)
def test_bounded_confidence_calibration_bucket_regression(
    confidence_tier: str,
    realism_status: str,
    match_status: str,
    outcome_direction: str | None,
    expected: str,
) -> None:
    matched_outcome = None
    match_reference = None
    if match_status != "missing":
        match_reference = {"match_mode": "paper_trade_id", "paper_trade_id": "tr-1"}
        matched_outcome = {
            "trade_id": "tr-1",
            "position_id": "pos-1",
            "symbol": "AAPL",
            "strategy_id": "RSI2",
            "trade_status": "open" if match_status == "open" else "closed",
            "opened_at_utc": "2026-04-01T08:05:00Z",
            "closed_at_utc": None if match_status == "open" else "2026-04-01T08:45:00Z",
            "outcome_direction": outcome_direction or "open",
            "realized_pnl": "1.50" if outcome_direction == "favorable" else "-1.50",
            "unrealized_pnl": None,
            "outcome_summary": "Matched paper trade contributes deterministic bounded calibration evidence.",
        }

    audit = evaluate_bounded_confidence_calibration_audit(
        covered_case_id="dc-calibration",
        confidence_tier=confidence_tier,
        backtest_realism_status=realism_status,
        backtest_realism_reason="Backtest realism coverage remains bounded for deterministic calibration review.",
        match_status=match_status,
        match_reference=match_reference,
        matched_outcome=matched_outcome,
    )

    assert isinstance(audit, BoundedConfidenceCalibrationAudit)
    assert audit.contract_id == CONFIDENCE_CALIBRATION_CONTRACT_ID
    assert audit.contract_version == CONFIDENCE_CALIBRATION_CONTRACT_VERSION
    assert audit.calibration_classification == expected


def test_bounded_confidence_calibration_is_deterministic_for_identical_inputs() -> None:
    common = {
        "covered_case_id": "dc-calibration",
        "confidence_tier": "high",
        "backtest_realism_status": "stable",
        "backtest_realism_reason": (
            "Backtest realism coverage remains bounded for deterministic calibration review."
        ),
        "match_status": "matched",
        "match_reference": {"match_mode": "paper_trade_id", "paper_trade_id": "tr-1"},
        "matched_outcome": {
            "trade_id": "tr-1",
            "position_id": "pos-1",
            "symbol": "AAPL",
            "strategy_id": "RSI2",
            "trade_status": "closed",
            "opened_at_utc": "2026-04-01T08:05:00Z",
            "closed_at_utc": "2026-04-01T08:45:00Z",
            "outcome_direction": "favorable",
            "realized_pnl": "1.50",
            "unrealized_pnl": None,
            "outcome_summary": "Matched paper trade contributes deterministic bounded calibration evidence.",
        },
    }

    first = evaluate_bounded_confidence_calibration_audit(**common)
    second = evaluate_bounded_confidence_calibration_audit(**common)

    assert first.model_dump() == second.model_dump()

```

### tests\test_api_decision_card_inspection_read.py
```
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

import api.main as api_main
from cilly_trading.models import Trade
from cilly_trading.engine.decision_card_contract import REQUIRED_COMPONENT_CATEGORIES
from cilly_trading.repositories.execution_core_sqlite import SqliteCanonicalExecutionRepository
from tests.utils.json_schema_validator import validate_json_schema

READ_ONLY_HEADERS = {api_main.ROLE_HEADER_NAME: "read_only"}


def _write_artifact(root: Path, run_id: str, artifact_name: str, payload: Any) -> None:
    run_dir = root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / artifact_name).write_text(json.dumps(payload), encoding="utf-8")


def _repo(tmp_path: Path) -> SqliteCanonicalExecutionRepository:
    return SqliteCanonicalExecutionRepository(db_path=tmp_path / "decision-card-inspection.db")


def _trade(
    trade_id: str,
    *,
    strategy_id: str,
    symbol: str,
    status: str,
    opened_at: str,
    closed_at: str | None,
    realized_pnl: str | None,
    unrealized_pnl: str | None,
) -> Trade:
    return Trade.model_validate(
        {
            "trade_id": trade_id,
            "position_id": f"pos-{trade_id}",
            "strategy_id": strategy_id,
            "symbol": symbol,
            "direction": "long",
            "status": status,
            "opened_at": opened_at,
            "closed_at": closed_at,
            "quantity_opened": Decimal("1"),
            "quantity_closed": Decimal("1") if status == "closed" else Decimal("0"),
            "average_entry_price": Decimal("100"),
            "average_exit_price": Decimal("101") if status == "closed" else None,
            "realized_pnl": Decimal(realized_pnl) if realized_pnl is not None else None,
            "unrealized_pnl": Decimal(unrealized_pnl) if unrealized_pnl is not None else None,
            "opening_order_ids": [f"ord-{trade_id}"],
            "closing_order_ids": [f"ord-{trade_id}"] if status == "closed" else [],
            "execution_event_ids": [f"evt-{trade_id}"],
        }
    )


def _decision_card_payload(
    *,
    decision_card_id: str,
    generated_at_utc: str,
    symbol: str,
    strategy_id: str,
    qualification_state: str,
    paper_trade_id: str | None = None,
) -> dict[str, Any]:
    color_by_state = {
        "reject": "red",
        "watch": "yellow",
        "paper_candidate": "yellow",
        "paper_approved": "green",
    }
    gates = [
        {
            "gate_id": "drawdown_safety",
            "status": "pass",
            "blocking": True,
            "reason": "Drawdown remains within threshold",
            "evidence": ["max_dd=0.08", "threshold=0.12"],
            "failure_reason": None,
        },
        {
            "gate_id": "portfolio_exposure_cap",
            "status": "pass",
            "blocking": True,
            "reason": "Exposure remains within policy bounds",
            "evidence": ["gross_exposure=0.41", "cap=0.60"],
            "failure_reason": None,
        },
    ]
    if qualification_state == "reject":
        gates[0] = {
            "gate_id": "drawdown_safety",
            "status": "fail",
            "blocking": True,
            "reason": "Drawdown guard failed",
            "evidence": ["max_dd=0.15", "threshold=0.12"],
            "failure_reason": "Max drawdown breached policy threshold",
        }
    confidence_tier = "high"
    confidence_reason = "Aggregate and minimum component scores satisfy high thresholds."
    aggregate_score = 84.15
    if qualification_state == "watch":
        confidence_tier = "low"
        confidence_reason = (
            "Aggregate score or component threshold evidence is below medium-confidence thresholds."
        )
        aggregate_score = 55.0
    elif qualification_state == "paper_candidate":
        confidence_tier = "medium"
        confidence_reason = (
            "Aggregate score and component threshold evidence satisfy medium-confidence thresholds."
        )
        aggregate_score = 72.0

    qualification_summary = "Opportunity requires further evidence before paper-trading qualification."
    if qualification_state == "reject":
        qualification_summary = "Opportunity is rejected for paper-trading because a blocking gate failed."
    elif qualification_state == "paper_approved":
        qualification_summary = "Opportunity is approved for bounded paper-trading only."

    payload = {
        "contract_version": "2.0.0",
        "decision_card_id": decision_card_id,
        "generated_at_utc": generated_at_utc,
        "symbol": symbol,
        "strategy_id": strategy_id,
        "hard_gates": {
            "policy_version": "hard-gates.v1",
            "gates": gates,
        },
        "score": {
            "component_scores": [
                {
                    "category": "signal_quality",
                    "score": 88.0,
                    "rationale": "Signal quality remains stable across the review window",
                    "evidence": ["hit_rate=0.64", "window=120d"],
                },
                {
                    "category": "backtest_quality",
                    "score": 84.0,
                    "rationale": "Backtest quality remains bounded and reproducible",
                    "evidence": ["sharpe=1.40", "profit_factor=1.60"],
                },
                {
                    "category": "portfolio_fit",
                    "score": 79.0,
                    "rationale": "Portfolio fit remains inside concentration limits",
                    "evidence": ["sector=0.17", "corr_cluster=0.42"],
                },
                {
                    "category": "risk_alignment",
                    "score": 86.0,
                    "rationale": "Risk alignment is within configured guardrail bounds",
                    "evidence": ["risk_trade=0.005", "max_dd=0.10"],
                },
                {
                    "category": "execution_readiness",
                    "score": 77.0,
                    "rationale": "Execution readiness remains consistent with assumptions",
                    "evidence": ["slippage_bps=9", "commission=1.00"],
                },
            ],
            "confidence_tier": confidence_tier,
            "confidence_reason": confidence_reason,
            "aggregate_score": aggregate_score,
        },
        "qualification": {
            "state": qualification_state,
            "color": color_by_state[qualification_state],
            "summary": qualification_summary,
        },
        "rationale": {
            "summary": "Qualification is resolved from explicit hard gates, bounded scores, and confidence rules.",
            "gate_explanations": [
                "Gate drawdown_safety was evaluated with explicit threshold evidence.",
                "Gate portfolio_exposure_cap was evaluated with explicit exposure evidence.",
            ],
            "score_explanations": [
                "Component scores are integrated by deterministic category ordering.",
                "Aggregate score uses fixed weights and bounded confidence tiers.",
            ],
            "final_explanation": "Action state is deterministic and does not imply live-trading approval.",
        },
        "metadata": {
            "analysis_run_id": "run-abc",
            "source": "qualification_engine",
        },
    }
    if paper_trade_id is not None:
        payload["metadata"]["bounded_decision_to_paper_match"] = {
            "match_mode": "paper_trade_id",
            "paper_trade_id": paper_trade_id,
        }
    return payload


def _backtest_artifact_payload(*, unstable: bool = False) -> dict[str, Any]:
    baseline_cost = 12.0
    stress_cost = 18.0 if not unstable else 10.0
    return {
        "metrics_baseline": {
            "realism_sensitivity_matrix": {
                "matrix_version": "1.0.0",
                "deterministic": True,
                "baseline_profile_id": "configured_baseline",
                "profile_order": [
                    "configured_baseline",
                    "cost_free_reference",
                    "bounded_cost_stress",
                ],
                "profiles": [
                    {
                        "profile_id": "configured_baseline",
                        "summary": {
                            "total_transaction_cost": baseline_cost,
                            "total_commission": 6.0,
                            "total_slippage_cost": 6.0,
                        },
                    },
                    {
                        "profile_id": "cost_free_reference",
                        "summary": {
                            "total_transaction_cost": 0.0,
                            "total_commission": 0.0,
                            "total_slippage_cost": 0.0,
                        },
                    },
                    {
                        "profile_id": "bounded_cost_stress",
                        "summary": {
                            "total_transaction_cost": stress_cost,
                            "total_commission": 9.0 if not unstable else 5.0,
                            "total_slippage_cost": 9.0 if not unstable else 5.0,
                        },
                    },
                ],
            }
        }
    }


def _client(
    monkeypatch,
    artifacts_root: Path,
    repo: SqliteCanonicalExecutionRepository | None = None,
) -> TestClient:
    if repo is None:
        repo = _repo(artifacts_root.parent)
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")
    monkeypatch.setattr(api_main, "JOURNAL_ARTIFACTS_ROOT", artifacts_root)
    monkeypatch.setattr(api_main, "canonical_execution_repo", repo)
    return TestClient(api_main.app)


def test_decision_card_inspection_endpoint_is_exposed_and_schema_valid(
    monkeypatch, tmp_path: Path
) -> None:
    artifacts_root = tmp_path / "runs" / "phase6"
    _write_artifact(
        artifacts_root,
        run_id="run-1",
        artifact_name="decision_card.json",
        payload=_decision_card_payload(
            decision_card_id="dc-001",
            generated_at_utc="2026-03-24T08:00:00Z",
            symbol="AAPL",
            strategy_id="RSI2",
            qualification_state="paper_approved",
        ),
    )

    with _client(monkeypatch, artifacts_root) as client:
        response = client.get("/decision-cards", headers=READ_ONLY_HEADERS)
        openapi = client.get("/openapi.json").json()

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["decision_card_id"] == "dc-001"
    assert payload["items"][0]["action"] == "entry"
    assert payload["items"][0]["win_rate"] == 0.864
    assert payload["items"][0]["expected_value"] == 1.0
    assert payload["items"][0]["hard_gates"]
    assert payload["items"][0]["component_scores"]
    assert {item["category"] for item in payload["items"][0]["component_scores"]} == set(
        REQUIRED_COMPONENT_CATEGORIES
    )
    assert payload["items"][0]["qualification_summary"] == "Opportunity is approved for bounded paper-trading only."
    assert (
        payload["items"][0]["rationale_summary"]
        == "Qualification is resolved from explicit hard gates, bounded scores, and confidence rules."
    )
    assert payload["items"][0]["gate_explanations"]
    assert payload["items"][0]["score_explanations"]
    assert payload["items"][0]["final_explanation"] == (
        "Action state is deterministic and does not imply live-trading approval."
    )
    assert "/decision-cards" in openapi["paths"]
    get_spec = openapi["paths"]["/decision-cards"]["get"]
    assert set(openapi["paths"]["/decision-cards"].keys()) == {"get"}
    assert "Read-only decision inspection surface aligned to the canonical decision contract" in (
        get_spec["description"]
    )

    errors = validate_json_schema(payload, api_main.DecisionCardInspectionResponse.model_json_schema())
    assert errors == []


def test_decision_card_inspection_ordering_and_filtering_are_deterministic(
    monkeypatch, tmp_path: Path
) -> None:
    artifacts_root = tmp_path / "runs" / "phase6"
    _write_artifact(
        artifacts_root,
        run_id="run-a",
        artifact_name="dc-1.json",
        payload=_decision_card_payload(
            decision_card_id="dc-001",
            generated_at_utc="2026-03-24T08:00:00Z",
            symbol="AAPL",
            strategy_id="RSI2",
            qualification_state="paper_approved",
        ),
    )
    _write_artifact(
        artifacts_root,
        run_id="run-a",
        artifact_name="dc-2.json",
        payload=_decision_card_payload(
            decision_card_id="dc-002",
            generated_at_utc="2026-03-24T09:00:00Z",
            symbol="MSFT",
            strategy_id="RSI2",
            qualification_state="reject",
        ),
    )
    _write_artifact(
        artifacts_root,
        run_id="run-b",
        artifact_name="dc-3.json",
        payload=_decision_card_payload(
            decision_card_id="dc-003",
            generated_at_utc="2026-03-24T09:00:00Z",
            symbol="AAPL",
            strategy_id="TURTLE",
            qualification_state="paper_candidate",
        ),
    )

    with _client(monkeypatch, artifacts_root) as client:
        first = client.get("/decision-cards", headers=READ_ONLY_HEADERS)
        second = client.get("/decision-cards", headers=READ_ONLY_HEADERS)
        aapl = client.get(
            "/decision-cards",
            headers=READ_ONLY_HEADERS,
            params={"symbol": "AAPL"},
        )
        rejected = client.get(
            "/decision-cards",
            headers=READ_ONLY_HEADERS,
            params={"qualification_state": "reject"},
        )
        approved = client.get(
            "/decision-cards",
            headers=READ_ONLY_HEADERS,
            params={"review_state": "approved"},
        )
        ranked = client.get(
            "/decision-cards",
            headers=READ_ONLY_HEADERS,
            params={"review_state": "ranked"},
        )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert [item["decision_card_id"] for item in first.json()["items"]] == [
        "dc-002",
        "dc-003",
        "dc-001",
    ]

    assert [item["decision_card_id"] for item in aapl.json()["items"]] == ["dc-003", "dc-001"]
    assert [item["decision_card_id"] for item in rejected.json()["items"]] == ["dc-002"]
    assert [item["decision_card_id"] for item in approved.json()["items"]] == ["dc-001"]
    assert [item["decision_card_id"] for item in ranked.json()["items"]] == ["dc-003", "dc-001"]


def test_decision_card_inspection_empty_and_error_cases(monkeypatch, tmp_path: Path) -> None:
    artifacts_root = tmp_path / "runs" / "phase6"

    with _client(monkeypatch, artifacts_root) as client:
        empty = client.get("/decision-cards", headers=READ_ONLY_HEADERS)
        unauthorized = client.get("/decision-cards")
        invalid_limit = client.get(
            "/decision-cards",
            headers=READ_ONLY_HEADERS,
            params={"limit": 0},
        )
        invalid_review_state = client.get(
            "/decision-cards",
            headers=READ_ONLY_HEADERS,
            params={"review_state": "unknown"},
        )

    assert empty.status_code == 200
    assert empty.json() == {"items": [], "limit": 50, "offset": 0, "total": 0}
    assert unauthorized.status_code == 401
    assert unauthorized.json() == {"detail": "unauthorized"}
    assert invalid_limit.status_code == 422
    assert invalid_review_state.status_code == 422


def test_decision_card_inspection_regression_ignores_non_contract_artifacts(
    monkeypatch, tmp_path: Path
) -> None:
    artifacts_root = tmp_path / "runs" / "phase6"
    _write_artifact(
        artifacts_root,
        run_id="run-1",
        artifact_name="invalid.json",
        payload={"decision_card": {"decision_card_id": "missing-fields"}},
    )
    (artifacts_root / "run-1" / "notes.txt").write_text("not json", encoding="utf-8")
    _write_artifact(
        artifacts_root,
        run_id="run-2",
        artifact_name="valid.json",
        payload={
            "decision_cards": [
                _decision_card_payload(
                    decision_card_id="dc-010",
                    generated_at_utc="2026-03-24T11:00:00Z",
                    symbol="NVDA",
                    strategy_id="TURTLE",
                    qualification_state="watch",
                )
            ]
        },
    )

    with _client(monkeypatch, artifacts_root) as client:
        response = client.get("/decision-cards", headers=READ_ONLY_HEADERS)

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert [item["decision_card_id"] for item in payload["items"]] == ["dc-010"]


def test_decision_card_inspection_persists_deterministic_bounded_usefulness_audit(
    monkeypatch, tmp_path: Path
) -> None:
    artifacts_root = tmp_path / "runs" / "phase6"
    repo = _repo(tmp_path)
    repo.save_trade(
        _trade(
            "trade-exp",
            strategy_id="RSI2",
            symbol="AAPL",
            status="closed",
            opened_at="2026-03-24T08:05:00Z",
            closed_at="2026-03-24T08:45:00Z",
            realized_pnl="1.50",
            unrealized_pnl=None,
        )
    )
    repo.save_trade(
        _trade(
            "trade-weak",
            strategy_id="RSI2",
            symbol="MSFT",
            status="open",
            opened_at="2026-03-24T09:05:00Z",
            closed_at=None,
            realized_pnl=None,
            unrealized_pnl="0.25",
        )
    )
    repo.save_trade(
        _trade(
            "trade-misleading",
            strategy_id="TURTLE",
            symbol="NVDA",
            status="closed",
            opened_at="2026-03-24T10:05:00Z",
            closed_at="2026-03-24T10:35:00Z",
            realized_pnl="-2.00",
            unrealized_pnl=None,
        )
    )

    _write_artifact(
        artifacts_root,
        run_id="run-usefulness",
        artifact_name="dc-exp.json",
        payload=_decision_card_payload(
            decision_card_id="dc-exp",
            generated_at_utc="2026-03-24T08:00:00Z",
            symbol="AAPL",
            strategy_id="RSI2",
            qualification_state="paper_approved",
            paper_trade_id="trade-exp",
        ),
    )
    _write_artifact(
        artifacts_root,
        run_id="run-usefulness",
        artifact_name="dc-weak.json",
        payload=_decision_card_payload(
            decision_card_id="dc-weak",
            generated_at_utc="2026-03-24T09:00:00Z",
            symbol="MSFT",
            strategy_id="RSI2",
            qualification_state="paper_approved",
            paper_trade_id="trade-weak",
        ),
    )
    _write_artifact(
        artifacts_root,
        run_id="run-usefulness",
        artifact_name="dc-misleading.json",
        payload=_decision_card_payload(
            decision_card_id="dc-misleading",
            generated_at_utc="2026-03-24T10:00:00Z",
            symbol="NVDA",
            strategy_id="TURTLE",
            qualification_state="paper_approved",
            paper_trade_id="trade-misleading",
        ),
    )

    with _client(monkeypatch, artifacts_root, repo=repo) as client:
        first = client.get("/decision-cards", headers=READ_ONLY_HEADERS)
        second = client.get("/decision-cards", headers=READ_ONLY_HEADERS)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()

    by_id = {item["decision_card_id"]: item for item in first.json()["items"]}

    explanatory_audit = by_id["dc-exp"]["metadata"]["bounded_decision_to_paper_usefulness_audit"]
    assert explanatory_audit["contract_id"] == "decision_evidence_to_paper_outcome_usefulness.paper_audit.v1"
    assert explanatory_audit["match_reference"] == {
        "match_mode": "paper_trade_id",
        "paper_trade_id": "trade-exp",
    }
    assert explanatory_audit["match_status"] == "matched"
    assert explanatory_audit["usefulness_classification"] == "explanatory"
    assert explanatory_audit["matched_outcome"]["outcome_direction"] == "favorable"
    assert "non-live" in explanatory_audit["interpretation_limit"]

    weak_audit = by_id["dc-weak"]["metadata"]["bounded_decision_to_paper_usefulness_audit"]
    assert weak_audit["match_status"] == "open"
    assert weak_audit["usefulness_classification"] == "weak"
    assert weak_audit["matched_outcome"]["outcome_direction"] == "open"

    misleading_audit = by_id["dc-misleading"]["metadata"]["bounded_decision_to_paper_usefulness_audit"]
    assert misleading_audit["match_status"] == "matched"
    assert misleading_audit["usefulness_classification"] == "misleading"
    assert misleading_audit["matched_outcome"]["outcome_direction"] == "adverse"


def test_decision_card_inspection_exposes_end_to_end_traceability_chain(
    monkeypatch, tmp_path: Path
) -> None:
    artifacts_root = tmp_path / "runs" / "phase6"
    repo = _repo(tmp_path)
    repo.save_trade(
        _trade(
            "trade-matched",
            strategy_id="RSI2",
            symbol="AAPL",
            status="closed",
            opened_at="2026-03-24T08:05:00Z",
            closed_at="2026-03-24T08:45:00Z",
            realized_pnl="1.50",
            unrealized_pnl=None,
        )
    )
    repo.save_trade(
        _trade(
            "trade-open",
            strategy_id="RSI2",
            symbol="MSFT",
            status="open",
            opened_at="2026-03-24T09:05:00Z",
            closed_at=None,
            realized_pnl=None,
            unrealized_pnl="0.25",
        )
    )
    repo.save_trade(
        _trade(
            "trade-invalid",
            strategy_id="OTHER",
            symbol="NVDA",
            status="closed",
            opened_at="2026-03-24T10:05:00Z",
            closed_at="2026-03-24T10:35:00Z",
            realized_pnl="0.50",
            unrealized_pnl=None,
        )
    )

    _write_artifact(
        artifacts_root,
        run_id="run-trace",
        artifact_name="dc-matched.json",
        payload=_decision_card_payload(
            decision_card_id="dc-matched",
            generated_at_utc="2026-03-24T08:00:00Z",
            symbol="AAPL",
            strategy_id="RSI2",
            qualification_state="paper_approved",
            paper_trade_id="trade-matched",
        ),
    )
    _write_artifact(
        artifacts_root,
        run_id="run-trace",
        artifact_name="dc-open.json",
        payload=_decision_card_payload(
            decision_card_id="dc-open",
            generated_at_utc="2026-03-24T09:00:00Z",
            symbol="MSFT",
            strategy_id="RSI2",
            qualification_state="paper_approved",
            paper_trade_id="trade-open",
        ),
    )
    _write_artifact(
        artifacts_root,
        run_id="run-trace",
        artifact_name="dc-missing.json",
        payload=_decision_card_payload(
            decision_card_id="dc-missing",
            generated_at_utc="2026-03-24T11:00:00Z",
            symbol="GOOG",
            strategy_id="RSI2",
            qualification_state="paper_approved",
            paper_trade_id=None,
        ),
    )
    _write_artifact(
        artifacts_root,
        run_id="run-trace",
        artifact_name="dc-invalid.json",
        payload=_decision_card_payload(
            decision_card_id="dc-invalid",
            generated_at_utc="2026-03-24T10:00:00Z",
            symbol="NVDA",
            strategy_id="TURTLE",
            qualification_state="paper_approved",
            paper_trade_id="trade-invalid",
        ),
    )

    with _client(monkeypatch, artifacts_root, repo=repo) as client:
        first = client.get("/decision-cards", headers=READ_ONLY_HEADERS)
        second = client.get("/decision-cards", headers=READ_ONLY_HEADERS)

    assert first.status_code == 200
    assert first.json() == second.json()

    by_id = {item["decision_card_id"]: item for item in first.json()["items"]}

    matched = by_id["dc-matched"]["traceability_chain"]
    assert matched["contract_id"] == "signal_to_paper_reconciliation_traceability.paper_audit.v1"
    assert matched["contract_version"] == "1.0.0"
    assert matched["overall_linkage_status"] == "matched"
    assert matched["signal_analysis"] == {
        "stage": "signal_analysis",
        "surface": "/signals",
        "analysis_run_id": "run-abc",
        "symbol": "AAPL",
        "strategy_id": "RSI2",
        "linkage_status": "matched",
    }
    assert matched["decision"] == {
        "stage": "decision_card",
        "surface": "/decision-cards",
        "decision_card_id": "dc-matched",
        "generated_at_utc": "2026-03-24T08:00:00Z",
        "qualification_state": "paper_approved",
        "action": "entry",
        "linkage_status": "matched",
    }
    assert matched["paper"] == {
        "stage": "paper_trade",
        "surface": "/paper/trades",
        "paper_trade_id": "trade-matched",
        "linkage_status": "matched",
    }
    assert matched["reconciliation"] == {
        "stage": "reconciliation",
        "surface": "/paper/reconciliation",
        "linkage_status": "matched",
    }
    assert "non-live" in matched["interpretation_limit"]

    open_chain = by_id["dc-open"]["traceability_chain"]
    assert open_chain["overall_linkage_status"] == "open"
    assert open_chain["paper"]["linkage_status"] == "open"
    assert open_chain["reconciliation"]["linkage_status"] == "open"

    missing = by_id["dc-missing"]["traceability_chain"]
    assert missing["overall_linkage_status"] == "missing"
    assert missing["paper"]["paper_trade_id"] is None
    assert missing["paper"]["linkage_status"] == "missing"
    assert missing["reconciliation"]["linkage_status"] == "missing"

    invalid = by_id["dc-invalid"]["traceability_chain"]
    assert invalid["overall_linkage_status"] == "invalid"
    assert invalid["paper"]["paper_trade_id"] == "trade-invalid"
    assert invalid["paper"]["linkage_status"] == "invalid"
    assert invalid["reconciliation"]["linkage_status"] == "invalid"


def test_decision_card_inspection_traceability_chain_marks_missing_analysis_run_id(
    monkeypatch, tmp_path: Path
) -> None:
    artifacts_root = tmp_path / "runs" / "phase6"
    payload = _decision_card_payload(
        decision_card_id="dc-no-analysis",
        generated_at_utc="2026-03-24T08:00:00Z",
        symbol="AAPL",
        strategy_id="RSI2",
        qualification_state="paper_approved",
    )
    payload["metadata"].pop("analysis_run_id", None)
    _write_artifact(
        artifacts_root,
        run_id="run-no-analysis",
        artifact_name="dc.json",
        payload=payload,
    )

    with _client(monkeypatch, artifacts_root) as client:
        response = client.get("/decision-cards", headers=READ_ONLY_HEADERS)

    assert response.status_code == 200
    chain = response.json()["items"][0]["traceability_chain"]
    assert chain["signal_analysis"]["analysis_run_id"] is None
    assert chain["signal_analysis"]["linkage_status"] == "missing"
    assert chain["overall_linkage_status"] == "missing"


def test_decision_card_inspection_persists_deterministic_signal_quality_stability_audit(
    monkeypatch, tmp_path: Path
) -> None:
    artifacts_root = tmp_path / "runs" / "phase6"
    repo = _repo(tmp_path)
    repo.save_trade(
        _trade(
            "trade-stable",
            strategy_id="RSI2",
            symbol="AAPL",
            status="closed",
            opened_at="2026-03-24T08:05:00Z",
            closed_at="2026-03-24T08:45:00Z",
            realized_pnl="1.50",
            unrealized_pnl=None,
        )
    )
    repo.save_trade(
        _trade(
            "trade-failing",
            strategy_id="TURTLE",
            symbol="NVDA",
            status="closed",
            opened_at="2026-03-24T10:05:00Z",
            closed_at="2026-03-24T10:35:00Z",
            realized_pnl="-2.00",
            unrealized_pnl=None,
        )
    )
    repo.save_trade(
        _trade(
            "trade-weak-open",
            strategy_id="RSI2",
            symbol="MSFT",
            status="open",
            opened_at="2026-03-24T09:05:00Z",
            closed_at=None,
            realized_pnl=None,
            unrealized_pnl="0.25",
        )
    )

    _write_artifact(
        artifacts_root,
        run_id="run-stability",
        artifact_name="dc-stable.json",
        payload=_decision_card_payload(
            decision_card_id="dc-stable",
            generated_at_utc="2026-03-24T08:00:00Z",
            symbol="AAPL",
            strategy_id="RSI2",
            qualification_state="paper_approved",
            paper_trade_id="trade-stable",
        ),
    )
    _write_artifact(
        artifacts_root,
        run_id="run-stability",
        artifact_name="dc-failing.json",
        payload=_decision_card_payload(
            decision_card_id="dc-failing",
            generated_at_utc="2026-03-24T10:00:00Z",
            symbol="NVDA",
            strategy_id="TURTLE",
            qualification_state="paper_approved",
            paper_trade_id="trade-failing",
        ),
    )
    _write_artifact(
        artifacts_root,
        run_id="run-stability",
        artifact_name="dc-weak.json",
        payload=_decision_card_payload(
            decision_card_id="dc-weak",
            generated_at_utc="2026-03-24T09:00:00Z",
            symbol="MSFT",
            strategy_id="RSI2",
            qualification_state="paper_approved",
            paper_trade_id="trade-weak-open",
        ),
    )
    _write_artifact(
        artifacts_root,
        run_id="run-stability",
        artifact_name="dc-missing.json",
        payload=_decision_card_payload(
            decision_card_id="dc-missing",
            generated_at_utc="2026-03-24T11:00:00Z",
            symbol="GOOG",
            strategy_id="RSI2",
            qualification_state="paper_approved",
            paper_trade_id=None,
        ),
    )

    with _client(monkeypatch, artifacts_root, repo=repo) as client:
        first = client.get("/decision-cards", headers=READ_ONLY_HEADERS)
        second = client.get("/decision-cards", headers=READ_ONLY_HEADERS)

    assert first.status_code == 200
    assert first.json() == second.json()

    by_id = {item["decision_card_id"]: item for item in first.json()["items"]}

    stable = by_id["dc-stable"]["metadata"]["bounded_signal_quality_stability_audit"]
    assert stable["contract_id"] == "bounded_signal_quality_stability.paper_audit.v1"
    assert stable["contract_version"] == "1.0.0"
    assert stable["match_status"] == "matched"
    assert stable["stability_classification"] == "stable"
    assert stable["matched_outcome"]["outcome_direction"] == "favorable"
    assert stable["signal_quality_score"] == 88.0
    assert "non-live" in stable["interpretation_limit"]

    failing = by_id["dc-failing"]["metadata"]["bounded_signal_quality_stability_audit"]
    assert failing["match_status"] == "matched"
    assert failing["stability_classification"] == "failing"
    assert failing["matched_outcome"]["outcome_direction"] == "adverse"

    weak = by_id["dc-weak"]["metadata"]["bounded_signal_quality_stability_audit"]
    assert weak["match_status"] == "open"
    assert weak["stability_classification"] == "weak"
    assert weak["matched_outcome"]["outcome_direction"] == "open"

    missing = by_id["dc-missing"]["metadata"]["bounded_signal_quality_stability_audit"]
    assert missing["match_status"] == "missing"
    assert missing["stability_classification"] == "weak"
    assert missing["matched_outcome"] is None
    assert missing["match_reference"] is None


def test_decision_card_inspection_persists_bounded_confidence_calibration_audit(
    monkeypatch, tmp_path: Path
) -> None:
    artifacts_root = tmp_path / "runs" / "phase6"
    repo = _repo(tmp_path)
    repo.save_trade(
        _trade(
            "trade-cal-stable",
            strategy_id="RSI2",
            symbol="AAPL",
            status="closed",
            opened_at="2026-03-24T08:05:00Z",
            closed_at="2026-03-24T09:05:00Z",
            realized_pnl="2.50",
            unrealized_pnl=None,
        )
    )
    repo.save_trade(
        _trade(
            "trade-cal-failing",
            strategy_id="RSI2",
            symbol="MSFT",
            status="closed",
            opened_at="2026-03-24T10:05:00Z",
            closed_at="2026-03-24T11:05:00Z",
            realized_pnl="-2.50",
            unrealized_pnl=None,
        )
    )

    _write_artifact(
        artifacts_root,
        run_id="run-calibration-stable",
        artifact_name="backtest-result.json",
        payload=_backtest_artifact_payload(),
    )
    _write_artifact(
        artifacts_root,
        run_id="run-calibration-stable",
        artifact_name="decision-card.json",
        payload=_decision_card_payload(
            decision_card_id="dc-cal-stable",
            generated_at_utc="2026-03-24T08:00:00Z",
            symbol="AAPL",
            strategy_id="RSI2",
            qualification_state="paper_approved",
            paper_trade_id="trade-cal-stable",
        ),
    )

    _write_artifact(
        artifacts_root,
        run_id="run-calibration-failing",
        artifact_name="backtest-result.json",
        payload=_backtest_artifact_payload(unstable=True),
    )
    _write_artifact(
        artifacts_root,
        run_id="run-calibration-failing",
        artifact_name="decision-card.json",
        payload=_decision_card_payload(
            decision_card_id="dc-cal-failing",
            generated_at_utc="2026-03-24T10:00:00Z",
            symbol="MSFT",
            strategy_id="RSI2",
            qualification_state="paper_approved",
            paper_trade_id="trade-cal-failing",
        ),
    )

    _write_artifact(
        artifacts_root,
        run_id="run-calibration-missing",
        artifact_name="decision-card.json",
        payload=_decision_card_payload(
            decision_card_id="dc-cal-missing",
            generated_at_utc="2026-03-24T12:00:00Z",
            symbol="GOOG",
            strategy_id="RSI2",
            qualification_state="paper_candidate",
            paper_trade_id=None,
        ),
    )

    with _client(monkeypatch, artifacts_root, repo=repo) as client:
        first = client.get("/decision-cards", headers=READ_ONLY_HEADERS)
        second = client.get("/decision-cards", headers=READ_ONLY_HEADERS)

    assert first.status_code == 200
    assert first.json() == second.json()

    by_id = {item["decision_card_id"]: item for item in first.json()["items"]}

    stable = by_id["dc-cal-stable"]["metadata"]["bounded_confidence_calibration_audit"]
    assert stable["contract_id"] == "bounded_confidence_calibration.realism_to_paper.paper_audit.v1"
    assert stable["contract_version"] == "1.0.0"
    assert stable["backtest_realism_status"] == "stable"
    assert stable["match_status"] == "matched"
    assert stable["matched_outcome"]["outcome_direction"] == "favorable"
    assert stable["calibration_classification"] == "stable"

    failing = by_id["dc-cal-failing"]["metadata"]["bounded_confidence_calibration_audit"]
    assert failing["backtest_realism_status"] == "failing"
    assert failing["match_status"] == "matched"
    assert failing["matched_outcome"]["outcome_direction"] == "adverse"
    assert failing["calibration_classification"] == "failing"

    missing = by_id["dc-cal-missing"]["metadata"]["bounded_confidence_calibration_audit"]
    assert missing["backtest_realism_status"] == "missing"
    assert missing["match_status"] == "missing"
    assert missing["matched_outcome"] is None
    assert missing["calibration_classification"] == "weak"
    assert "non-live" in missing["interpretation_limit"]

```

### tests\test_sig_p47_score_semantics.py
```
"""Contract and semantic tests for SIG-P47 score semantics and cross-strategy comparability."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from cilly_trading.engine.decision_card_contract import (
    CONFIDENCE_CALIBRATION_INTERPRETATION_BOUNDARY,
    CONFIDENCE_TIER_PRECISION_DISCLAIMER,
    CROSS_STRATEGY_SCORE_COMPARABILITY_BOUNDARY,
    QUALIFICATION_PROFILE_ROBUSTNESS_INTERPRETATION_BOUNDARY,
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
    QUALIFICATION_THRESHOLD_PROFILES_BY_COMPARISON_GROUP,
    get_registered_strategy_metadata,
    resolve_qualification_profile_robustness_slices,
    resolve_qualification_threshold_profile,
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


def test_comparison_group_threshold_profiles_are_defined_and_deterministic() -> None:
    assert "mean-reversion" in QUALIFICATION_THRESHOLD_PROFILES_BY_COMPARISON_GROUP
    assert "trend-following" in QUALIFICATION_THRESHOLD_PROFILES_BY_COMPARISON_GROUP
    assert "reference-control" in QUALIFICATION_THRESHOLD_PROFILES_BY_COMPARISON_GROUP

    first = resolve_qualification_threshold_profile(comparison_group="mean-reversion")
    second = resolve_qualification_threshold_profile(comparison_group="mean-reversion")
    assert first == second
    assert first["profile_id"] == "qualification-threshold.mean-reversion.v1"
    assert first["high_aggregate"] >= first["medium_aggregate"]
    assert first["high_min_component"] >= first["medium_min_component"]


def test_comparison_group_robustness_slices_are_defined_and_deterministic() -> None:
    first = resolve_qualification_profile_robustness_slices(comparison_group="mean-reversion")
    second = resolve_qualification_profile_robustness_slices(comparison_group="mean-reversion")

    assert first == second
    assert [item["deterministic_rank"] for item in first] == [1, 2, 3, 4]
    assert [item["slice_id"] for item in first] == [
        "covered.current_evidence.v1",
        "failure_envelope.evidence_decay.v1",
        "failure_envelope.execution_stress.v1",
        "regime_slice.mean_reversion_headwind.v1",
    ]
    assert all(isinstance(item["component_score_adjustments"], dict) for item in first)
    assert (
        resolve_qualification_profile_robustness_slices(comparison_group="trend-following")[-1][
            "slice_id"
        ]
        == "regime_slice.trend_following_headwind.v1"
    )


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


def test_score_semantics_governance_doc_mentions_calibrated_threshold_profiles() -> None:
    content = GOVERNANCE_DOC.read_text(encoding="utf-8")

    assert "threshold profile" in content.casefold()
    assert "comparison_group" in content
    assert "not directly comparable" in content


def test_score_semantics_governance_doc_mentions_bounded_robustness_audit() -> None:
    content = GOVERNANCE_DOC.read_text(encoding="utf-8")

    assert "Qualification-Profile Robustness Audit Boundary" in content
    assert "stable" in content
    assert "weak" in content
    assert "failing" in content
    assert "covered conditions" in content
    assert "QUALIFICATION_PROFILE_ROBUSTNESS_INTERPRETATION_BOUNDARY" in content


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


def test_signal_quality_contract_doc_mentions_calibrated_threshold_profiles() -> None:
    content = (REPO_ROOT / "docs" / "governance" / "signal-quality-bounded-contract.md").read_text(
        encoding="utf-8"
    )
    assert "threshold profile" in content.casefold()
    assert "comparison_group" in content
    assert "non-comparability" in content.casefold()


def test_signal_quality_contract_doc_mentions_bounded_robustness_claim_limits() -> None:
    content = (REPO_ROOT / "docs" / "governance" / "signal-quality-bounded-contract.md").read_text(
        encoding="utf-8"
    )

    assert "Qualification-Profile Robustness Boundary" in content
    assert "covered.current_evidence.v1" in content
    assert "failure_envelope.execution_stress.v1" in content
    assert "stable" in content
    assert "weak" in content
    assert "failing" in content
    assert "covered conditions" in content
    assert "trader_validation" in content


def test_signal_quality_contract_doc_mentions_bounded_confidence_calibration() -> None:
    content = (REPO_ROOT / "docs" / "governance" / "signal-quality-bounded-contract.md").read_text(
        encoding="utf-8"
    )

    assert "Confidence Calibration Boundary" in content
    assert "backtest-realism" in content
    assert "matched paper-trade outcomes" in content
    assert "stable" in content
    assert "weak" in content
    assert "failing" in content
    assert "non-live" in content


def test_confidence_calibration_boundary_constant_is_defined() -> None:
    boundary = CONFIDENCE_CALIBRATION_INTERPRETATION_BOUNDARY.casefold()

    assert isinstance(CONFIDENCE_CALIBRATION_INTERPRETATION_BOUNDARY, str)
    assert "non-live" in boundary
    assert "trader validation" in boundary
    assert "profitability forecasting" in boundary
    assert "live-trading readiness" in boundary


def test_qualification_profile_robustness_boundary_constant_is_defined() -> None:
    boundary = QUALIFICATION_PROFILE_ROBUSTNESS_INTERPRETATION_BOUNDARY.casefold()

    assert isinstance(QUALIFICATION_PROFILE_ROBUSTNESS_INTERPRETATION_BOUNDARY, str)
    assert "covered conditions" in boundary
    assert "weak or failing slices" in boundary
    assert "paper profitability" in boundary

```

### docs\governance\signal-quality-bounded-contract.md
```
# P56 Signal Quality - Bounded Validation Contract

## Purpose

This contract defines signal-quality validation boundaries for current repository behavior.
It validates deterministic ranking and filtering behavior for decision-support inspection
without expanding strategy scope or changing runtime architecture.

## Scope

In scope:

- deterministic ranking behavior under fixed fixtures
- selectivity behavior via `min_score` filtering where score data is numeric
- bounded handling for weak or low-information cases where current implementation supports it
- wording discipline aligned to available repository evidence only

Out of scope:

- new strategies
- ML scoring
- external data expansion
- broad scoring redesign
- trader-readiness claims

## Bounded Signal-Quality Meaning

Within this repository, "signal quality" is bounded to three implementation-level properties:

1. Deterministic ranking behavior under defined fixtures.
2. Selectivity boundary for low-information candidates.
3. Stability boundary under equivalent fixture content.

This contract evaluates ordering and filtering consistency only. It does not evaluate
market edge, profitability, or production trading outcomes.

## Bounded Win-Rate and Expected-Value Evidence

For paper-evaluation qualification output, bounded signal-quality evidence also includes:

- bounded win-rate formula: `win_rate=((signal_quality*0.60)+(backtest_quality*0.40))/100`
- bounded expected-value formula:
  `expected_value=(win_rate*bounded_reward_multiplier)-(1-win_rate)`
  where `bounded_reward_multiplier=clamp((risk_alignment+execution_readiness)/100,0.50,1.50)`

Both values are deterministic, clamped (`win_rate` in `[0,1]`, `expected_value` in `[-1,1]`), and
derived only from existing bounded component evidence. They are technical evidence fields only.

## Deterministic Action Boundary

The qualification output includes one deterministic paper-evaluation action:

- `entry`
- `exit`
- `ignore`

Deterministic paper-evaluation action is resolved with hard gates plus bounded aggregate,
win-rate, and expected-value evidence:

1. blocking hard-gate failure -> `ignore`
2. negative expected value -> `exit` (never `entry`)
3. qualified (`paper_candidate`/`paper_approved`) with weak bounded win-rate (`<= 0.50`) -> `exit`
4. qualified with bounded win-rate (`>= 0.55`) and non-negative expected value -> `entry`
5. otherwise -> `ignore`

These action semantics are bounded to paper evaluation and must not be interpreted as
live-trading authorization.

## Comparison-Group Threshold Profile Boundary

Qualification calibration is deterministic and bounded by strategy `comparison_group`
threshold profiles.

- threshold profiles are resolved from governed strategy metadata comparison groups
- the applied profile identifier is emitted in qualification evidence output
- calibrated thresholds remain bounded implementation semantics, not probability claims

Cross-group non-comparability remains explicit: threshold profile calibration does not
make decision-card scores directly comparable across different comparison groups.

## Qualification-Profile Robustness Boundary

Qualification-profile robustness is evaluated through one fixed deterministic bounded
audit slice set:

- `covered.current_evidence.v1`
- `failure_envelope.evidence_decay.v1`
- `failure_envelope.execution_stress.v1`
- one comparison-group regime slice resolved deterministically from registry metadata

The audit uses only existing component-score evidence dimensions and governed threshold
profiles. It records explicit `stable`, `weak`, and `failing` slice behavior in bounded
audit output.

Weak or failing slices limit interpretation outside covered conditions and do not expand
live-trading approval, paper profitability, or trader_validation claims.

## Confidence Calibration Boundary

Score-confidence interpretation is additionally bounded by one deterministic calibration
contract that relates:

- the covered `confidence_tier`
- covered backtest-realism sensitivity evidence
- matched paper-trade outcomes when an explicit `paper_trade_id` link exists

This calibration contract does not rescore strategies and does not change execution
behavior. It classifies confidence behavior only:

- `stable`: the covered confidence tier stays aligned with stable/complete realism coverage
  and the matched paper outcome does not contradict the bounded interpretation
- `weak`: the covered confidence tier remains only partially supported, or covered realism /
  downstream paper evidence is missing or still open
- `failing`: the covered confidence tier overstates evidence relative to failing realism
  coverage or a contradictory matched paper outcome

The calibration remains non-live and bounded:

- it does not imply trader validation
- it does not imply paper profitability
- it does not imply live-trading readiness or operational readiness
- missing backtest-realism evidence or missing matched paper evidence limits calibration to
  weak bounded interpretation rather than inflating confidence claims

## Deterministic Ranking Boundary

For setup-stage candidates that meet the configured score floor, ranking is deterministic:

- primary key: `score` descending
- secondary key: `signal_strength` descending (when present)
- tiebreaker: `symbol` ascending

This boundary is implemented by the ranking key in
`src/api/services/analysis_service.py` (`build_ranked_symbol_results`).

## Selectivity Boundary

Selectivity is bounded to currently supported filtering behavior:

- only `stage == "setup"` is considered
- candidate score must meet `min_score` (inclusive)
- scores that cannot be coerced to numeric are treated as low-information and filtered
  out when `min_score > 0`

The filter is bounded to available signal fields and does not infer missing external context.

## Weak/Low-Information Handling Boundary

Current bounded behavior for weak or low-information signals:

- missing/empty `symbol` is excluded from ranked output
- non-setup stage is excluded from ranked output
- non-numeric or missing scores are not promoted above valid numeric setups

These are implementation boundaries, not trader-value guarantees.

## Professional Non-Live Qualification Criteria Boundary

The bounded signal decision surface applies explicit non-live professional qualification criteria to reviewed signals:

- stage criterion: `stage` must be `entry_confirmed`
- score criterion: score must satisfy bounded decision thresholds (blocking and candidate levels)
- confirmation criterion: `confirmation_rule` must be present as explicit signal evidence
- entry-zone criterion: `entry_zone.from_` and `entry_zone.to` must be present and ordered (`from_ < to`)

Qualification output remains technical-only and must expose:
- explicit qualification evidence fields
- explicit missing criteria fields
- explicit blocking-condition fields

## Stability Boundary

Given equivalent fixture content, ranked output remains stable independent of input list order.
Determinism is asserted through contract tests with permuted fixture ordering.

## Evidence and Claim Boundary

This contract supports only bounded implementation claims. It explicitly supports
"Classification: technically good, traderically weak" for current state.

It does not claim trader readiness, and it provides no live-trading readiness, execution approval, or profitability guarantee.

Robustness audit findings remain non-live interpretation only: stable slices stay bounded
to covered conditions, and weak/failing slices reduce interpretive confidence rather than
expanding claims.

## Validation Surfaces

- Tests: `tests/test_sig_p56_signal_quality_contract.py`
- Runtime ranking surface: `src/api/services/analysis_service.py`
- Read-model ranking surface: `src/cilly_trading/repositories/signals_sqlite.py`

```

## TEST EXECUTION EVIDENCE
Command used:
```powershell
python -m pytest -q
```
Full test output:
```text
........................................................................ [  5%]
........................................................................ [ 11%]
........................................................................ [ 17%]
........................................................................ [ 23%]
........................................................................ [ 29%]
........................................................................ [ 35%]
........................................................................ [ 40%]
........................................................................ [ 46%]
........................................................................ [ 52%]
........................................................................ [ 58%]
........................................................................ [ 64%]
........................................................................ [ 70%]
........................................................................ [ 75%]
........................................................................ [ 81%]
........................................................................ [ 87%]
........................................................................ [ 93%]
........................................................................ [ 99%]
.........                                                                [100%]
1233 passed in 112.44s (0:01:52)
```

## PULL REQUEST INSTRUCTIONS
- Branch name: `codex/issue-1040-confidence-calibration`
- Commit messages:
  - `Add bounded confidence calibration audit against realism and paper outcomes`
  - `Add regression tests and governance wording for confidence calibration`
- PR title: `[QUEUED][SIGNAL-CALIBRATION] Calibrate bounded score confidence against backtest realism and matched paper outcomes (#1040)`
- PR body:
```markdown
Closes #1040

## Summary
- add one deterministic bounded confidence-calibration audit that aligns `confidence_tier` with covered backtest-realism sensitivity evidence and matched paper outcomes
- surface the audit on decision-card inspection metadata without changing execution behavior
- add regression and docs tests for stable/weak/failing and missing-evidence paths

## Testing
- `python -m pytest -q`
```
