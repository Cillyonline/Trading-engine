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
        return dict(sorted(value.items()))

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
    "PAPER_REVIEW_CASE_DEFINITIONS",
    "CROSS_STRATEGY_SCORE_COMPARABILITY_BOUNDARY",
    "CONFIDENCE_TIER_PRECISION_DISCLAIMER",
    "UPSTREAM_EVIDENCE_QUALITY_CONFIDENCE_BOUND",
    "QUALIFICATION_HIGH_AGGREGATE_THRESHOLD",
    "QUALIFICATION_MEDIUM_AGGREGATE_THRESHOLD",
    "REQUIRED_COMPONENT_CATEGORIES",
    "ACTION_ENTRY_WIN_RATE_MIN",
    "ACTION_EXIT_WIN_RATE_MAX",
    "QUALIFICATION_COLOR_BY_STATE",
    "BoundedTraderRelevanceCaseEvaluation",
    "BoundedTraderRelevanceValidation",
    "ComponentScore",
    "DecisionAction",
    "DecisionCard",
    "DecisionRationale",
    "HardGateEvaluation",
    "HardGateResult",
    "Qualification",
    "ScoreEvaluation",
    "evaluate_bounded_trader_relevance_cases",
    "serialize_decision_card",
    "validate_decision_card",
]
