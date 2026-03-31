"""Canonical decision-card contract with hard gates and score semantics."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

DECISION_CARD_CONTRACT_VERSION = "2.0.0"
QUALIFICATION_MEDIUM_AGGREGATE_THRESHOLD = 60.0
QUALIFICATION_HIGH_AGGREGATE_THRESHOLD = 80.0

CROSS_STRATEGY_SCORE_COMPARABILITY_BOUNDARY = (
    "Decision-card scores are bounded to within-strategy evaluation for a single opportunity. "
    "Cross-strategy score comparison is not supported; aggregate scores and component scores "
    "from strategies in different comparison groups are not directly comparable."
)

CONFIDENCE_TIER_PRECISION_DISCLAIMER = (
    "Confidence tier is an ordinal classification (low/medium/high) derived from bounded thresholds. "
    "It does not imply precise probability, forecast accuracy, or score equality across strategies."
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
    "guaranteed",
    "guarantee",
    "certain outcome",
)


def _contains_forbidden_claim_phrase(value: str) -> str | None:
    normalized = value.casefold()
    for phrase in CLAIM_BOUNDARY_FORBIDDEN_PHRASES:
        if phrase in normalized:
            return phrase
    return None


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
    qualification: Qualification
    rationale: DecisionRationale
    metadata: dict[str, Any] = Field(default_factory=dict)

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
        return self

    def _expected_qualification_state(self) -> QualificationState:
        if self.hard_gates.has_blocking_failure:
            return "reject"
        if (
            self.score.confidence_tier == "low"
            or self.score.aggregate_score < QUALIFICATION_MEDIUM_AGGREGATE_THRESHOLD
        ):
            return "watch"
        if (
            self.score.confidence_tier == "high"
            and self.score.aggregate_score >= QUALIFICATION_HIGH_AGGREGATE_THRESHOLD
        ):
            return "paper_approved"
        return "paper_candidate"

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
    "CROSS_STRATEGY_SCORE_COMPARABILITY_BOUNDARY",
    "CONFIDENCE_TIER_PRECISION_DISCLAIMER",
    "QUALIFICATION_HIGH_AGGREGATE_THRESHOLD",
    "QUALIFICATION_MEDIUM_AGGREGATE_THRESHOLD",
    "REQUIRED_COMPONENT_CATEGORIES",
    "QUALIFICATION_COLOR_BY_STATE",
    "ComponentScore",
    "DecisionCard",
    "DecisionRationale",
    "HardGateEvaluation",
    "HardGateResult",
    "Qualification",
    "ScoreEvaluation",
    "serialize_decision_card",
    "validate_decision_card",
]
