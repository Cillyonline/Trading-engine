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
STRATEGY_SCORE_CALIBRATION_CONTRACT_ID = (
    "bounded_strategy_score_calibration.backtest_to_paper.paper_audit.v1"
)
STRATEGY_SCORE_CALIBRATION_CONTRACT_VERSION = "1.0.0"
STRATEGY_SCORE_CALIBRATION_INTERPRETATION_BOUNDARY = (
    "Bounded strategy-score calibration is limited to per-strategy non-live interpretation of "
    "RSI2/Turtle MVP aggregate scores against covered backtest-realism evidence and matched "
    "paper-trade outcomes where available. Confidence tier remains ordinal, not probabilistic. "
    "Cross-strategy comparability remains explicitly unsupported unless governed evidence proves "
    "otherwise. It does not imply trader validation, profitability forecasting, live-trading "
    "readiness, or operational readiness."
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
StrategyScoreCalibrationClassification = Literal["stable", "weak", "failing", "limited"]
StrategyScoreEvidenceCoverage = Literal["covered", "partial", "missing", "invalid"]

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


class BoundedStrategyScoreCalibrationAudit(BaseModel):
    """Bounded per-strategy MVP score calibration against covered evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_id: str = STRATEGY_SCORE_CALIBRATION_CONTRACT_ID
    contract_version: str = STRATEGY_SCORE_CALIBRATION_CONTRACT_VERSION
    covered_case_id: str = Field(min_length=1)
    strategy_id: Literal["RSI2", "TURTLE"]
    score_scope: Literal["per_strategy"] = "per_strategy"
    score_interpretation: Literal["bounded_per_strategy_evidence"] = (
        "bounded_per_strategy_evidence"
    )
    aggregate_score: float = Field(ge=0.0, le=100.0)
    confidence_tier: DecisionConfidenceTier
    confidence_tier_semantics: Literal["ordinal_not_probabilistic"] = (
        "ordinal_not_probabilistic"
    )
    backtest_realism_status: BacktestRealismCalibrationStatus
    backtest_realism_reason: str = Field(min_length=24)
    match_reference: BoundedDecisionToPaperUsefulnessMatchReference | None = None
    match_status: DecisionToPaperUsefulnessMatchStatus
    matched_outcome: BoundedPaperTradeOutcome | None = None
    evidence_coverage: StrategyScoreEvidenceCoverage
    calibration_classification: StrategyScoreCalibrationClassification
    calibration_reason: str = Field(min_length=24)
    cross_strategy_comparison_supported: Literal[False] = False
    interpretation_limit: str = Field(min_length=24)

    @field_validator("contract_id")
    @classmethod
    def _validate_contract_id(cls, value: str) -> str:
        if value != STRATEGY_SCORE_CALIBRATION_CONTRACT_ID:
            raise ValueError(f"Unsupported strategy-score calibration contract_id: {value}")
        return value

    @field_validator("contract_version")
    @classmethod
    def _validate_contract_version(cls, value: str) -> str:
        if value != STRATEGY_SCORE_CALIBRATION_CONTRACT_VERSION:
            raise ValueError(
                f"Unsupported strategy-score calibration contract_version: {value}"
            )
        return value

    @model_validator(mode="after")
    def _validate_boundary_alignment(self) -> "BoundedStrategyScoreCalibrationAudit":
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
            "per-strategy",
            "confidence tier remains ordinal",
            "cross-strategy comparability remains explicitly unsupported",
            "non-live",
            "trader validation",
            "profitability forecasting",
            "live-trading readiness",
        )
        if not all(phrase in lowered_limit for phrase in required_phrases):
            raise ValueError(
                "interpretation_limit must preserve per-strategy, ordinal, non-live, "
                "non-comparability, trader-validation, profitability, and readiness boundaries"
            )
        return self


def _classify_strategy_score_evidence_coverage(
    *,
    backtest_realism_status: BacktestRealismCalibrationStatus,
    match_status: DecisionToPaperUsefulnessMatchStatus,
) -> StrategyScoreEvidenceCoverage:
    if backtest_realism_status == "missing" and match_status == "missing":
        return "missing"
    if backtest_realism_status == "failing" or match_status == "invalid":
        return "invalid"
    if backtest_realism_status == "missing" or match_status in {"missing", "open"}:
        return "partial"
    return "covered"


def _classify_strategy_score_calibration(
    *,
    aggregate_score: float,
    confidence_tier: DecisionConfidenceTier,
    backtest_realism_status: BacktestRealismCalibrationStatus,
    match_status: DecisionToPaperUsefulnessMatchStatus,
    matched_outcome: BoundedPaperTradeOutcome | None,
) -> tuple[
    StrategyScoreEvidenceCoverage,
    StrategyScoreCalibrationClassification,
    str,
]:
    evidence_coverage = _classify_strategy_score_evidence_coverage(
        backtest_realism_status=backtest_realism_status,
        match_status=match_status,
    )
    if evidence_coverage == "missing":
        return (
            evidence_coverage,
            "limited",
            "Strategy score has neither covered backtest-realism evidence nor matched paper "
            "outcome evidence, so per-strategy calibration is limited in non-live review.",
        )
    if evidence_coverage == "invalid":
        return (
            evidence_coverage,
            "failing",
            "Strategy score evidence includes failing backtest-realism coverage or invalid paper "
            "matching, so bounded per-strategy calibration is failing.",
        )
    if match_status == "open":
        return (
            evidence_coverage,
            "weak",
            "Strategy score has an open matched paper trade, so calibration remains weak until "
            "the downstream paper outcome is closed.",
        )
    if backtest_realism_status == "missing" or match_status == "missing":
        return (
            evidence_coverage,
            "limited",
            "Strategy score is supported by only partial calibration evidence, so interpretation "
            "is limited to bounded per-strategy evidence.",
        )
    if matched_outcome is None:
        return (
            evidence_coverage,
            "weak",
            "Matched paper outcome is unavailable, so bounded per-strategy score calibration "
            "remains weak.",
        )
    if matched_outcome.outcome_direction == "adverse":
        if confidence_tier == "low" or aggregate_score < QUALIFICATION_MEDIUM_AGGREGATE_THRESHOLD:
            return (
                evidence_coverage,
                "weak",
                "Adverse matched paper outcome aligns only with a cautious low-score posture, so "
                "per-strategy calibration remains weak rather than stable.",
            )
        return (
            evidence_coverage,
            "failing",
            "Strategy score remained medium/high while the matched paper outcome closed adverse, "
            "so bounded per-strategy calibration is failing.",
        )
    if matched_outcome.outcome_direction == "flat":
        return (
            evidence_coverage,
            "weak",
            "Matched paper outcome closed flat, so the strategy score has weak bounded "
            "per-strategy calibration evidence.",
        )
    if backtest_realism_status == "stable" and confidence_tier in {"medium", "high"}:
        return (
            evidence_coverage,
            "stable",
            "Strategy score is bounded per-strategy evidence with stable covered backtest-realism "
            "coverage and a favorable matched paper outcome.",
        )
    return (
        evidence_coverage,
        "weak",
        "Strategy score has favorable paper evidence but incomplete or cautious supporting "
        "evidence, so bounded per-strategy calibration remains weak.",
    )


def evaluate_bounded_strategy_score_calibration_audit(
    *,
    covered_case_id: str,
    strategy_id: Literal["RSI2", "TURTLE"],
    aggregate_score: float,
    confidence_tier: DecisionConfidenceTier,
    backtest_realism_status: BacktestRealismCalibrationStatus,
    backtest_realism_reason: str,
    match_status: DecisionToPaperUsefulnessMatchStatus,
    match_reference: dict[str, Any] | None = None,
    matched_outcome: dict[str, Any] | None = None,
) -> BoundedStrategyScoreCalibrationAudit:
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
    evidence_coverage, classification, reason = _classify_strategy_score_calibration(
        aggregate_score=aggregate_score,
        confidence_tier=confidence_tier,
        backtest_realism_status=backtest_realism_status,
        match_status=match_status,
        matched_outcome=normalized_matched_outcome,
    )
    return BoundedStrategyScoreCalibrationAudit(
        covered_case_id=covered_case_id,
        strategy_id=strategy_id,
        aggregate_score=aggregate_score,
        confidence_tier=confidence_tier,
        backtest_realism_status=backtest_realism_status,
        backtest_realism_reason=backtest_realism_reason,
        match_reference=normalized_match_reference,
        match_status=match_status,
        matched_outcome=normalized_matched_outcome,
        evidence_coverage=evidence_coverage,
        calibration_classification=classification,
        calibration_reason=reason,
        interpretation_limit=STRATEGY_SCORE_CALIBRATION_INTERPRETATION_BOUNDARY,
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
    "CONFIDENCE_CALIBRATION_CONTRACT_ID",
    "CONFIDENCE_CALIBRATION_CONTRACT_VERSION",
    "CONFIDENCE_CALIBRATION_INTERPRETATION_BOUNDARY",
    "STRATEGY_SCORE_CALIBRATION_CONTRACT_ID",
    "STRATEGY_SCORE_CALIBRATION_CONTRACT_VERSION",
    "STRATEGY_SCORE_CALIBRATION_INTERPRETATION_BOUNDARY",
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
    "BoundedStrategyScoreCalibrationAudit",
    "BoundedTraderRelevanceCaseEvaluation",
    "BoundedTraderRelevanceValidation",
    "ComponentScore",
    "DecisionAction",
    "DecisionCard",
    "DecisionRationale",
    "EndToEndTraceabilityLinkageStatus",
    "SignalQualityStabilityClassification",
    "StrategyScoreCalibrationClassification",
    "StrategyScoreEvidenceCoverage",
    "HardGateEvaluation",
    "HardGateResult",
    "QualificationProfileRobustnessAudit",
    "QualificationProfileRobustnessSliceResult",
    "Qualification",
    "ScoreEvaluation",
    "evaluate_bounded_decision_to_paper_usefulness_audit",
    "evaluate_bounded_end_to_end_traceability_chain",
    "evaluate_bounded_signal_quality_stability_audit",
    "evaluate_bounded_strategy_score_calibration_audit",
    "evaluate_bounded_trader_relevance_cases",
    "serialize_decision_card",
    "validate_decision_card",
]
