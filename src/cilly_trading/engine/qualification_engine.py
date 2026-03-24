"""Deterministic qualification engine for decision-card evaluation."""

from __future__ import annotations

from dataclasses import dataclass

from cilly_trading.engine.decision_card_contract import (
    DECISION_CARD_CONTRACT_VERSION,
    REQUIRED_COMPONENT_CATEGORIES,
    ComponentScore,
    DecisionCard,
    DecisionComponentCategory,
    DecisionConfidenceTier,
    HardGateEvaluation,
    HardGateResult,
    QualificationColor,
    QualificationState,
    validate_decision_card,
)

DecisionActionState = QualificationState

COMPONENT_WEIGHTS: dict[DecisionComponentCategory, float] = {
    "signal_quality": 0.30,
    "backtest_quality": 0.25,
    "portfolio_fit": 0.15,
    "risk_alignment": 0.20,
    "execution_readiness": 0.10,
}

CONFIDENCE_THRESHOLDS: dict[str, float] = {
    "high_aggregate": 80.0,
    "high_min_component": 70.0,
    "medium_aggregate": 60.0,
    "medium_min_component": 50.0,
}


@dataclass(frozen=True)
class QualificationEngineInput:
    decision_card_id: str
    generated_at_utc: str
    symbol: str
    strategy_id: str
    hard_gates: list[HardGateResult]
    component_scores: list[ComponentScore]
    hard_gate_policy_version: str = "hard-gates.v1"
    metadata: dict[str, object] | None = None


def evaluate_qualification(input_data: QualificationEngineInput) -> DecisionCard:
    """Evaluate hard gates, component scores, and output a deterministic decision card."""
    hard_gate_evaluation = HardGateEvaluation(
        policy_version=input_data.hard_gate_policy_version,
        gates=list(input_data.hard_gates),
    )
    aggregate_score = compute_aggregate_score(component_scores=input_data.component_scores)
    confidence_tier = assign_confidence_tier(
        aggregate_score=aggregate_score,
        component_scores=input_data.component_scores,
    )
    confidence_reason = _confidence_reason(confidence_tier=confidence_tier, aggregate_score=aggregate_score)
    state, color, qualification_summary = resolve_qualification_state(
        hard_gate_evaluation=hard_gate_evaluation,
        aggregate_score=aggregate_score,
        confidence_tier=confidence_tier,
    )
    payload = {
        "contract_version": DECISION_CARD_CONTRACT_VERSION,
        "decision_card_id": input_data.decision_card_id,
        "generated_at_utc": input_data.generated_at_utc,
        "symbol": input_data.symbol,
        "strategy_id": input_data.strategy_id,
        "hard_gates": {
            "policy_version": input_data.hard_gate_policy_version,
            "gates": [gate.model_dump(mode="python") for gate in hard_gate_evaluation.gates],
        },
        "score": {
            "component_scores": [
                component.model_dump(mode="python")
                for component in sorted(
                    input_data.component_scores,
                    key=lambda item: item.category,
                )
            ],
            "confidence_tier": confidence_tier,
            "confidence_reason": confidence_reason,
            "aggregate_score": aggregate_score,
        },
        "qualification": {
            "state": state,
            "color": color,
            "summary": qualification_summary,
        },
        "rationale": {
            "summary": "Qualification is resolved from explicit hard gates, bounded scores, and confidence rules.",
            "gate_explanations": _gate_explanations(hard_gate_evaluation=hard_gate_evaluation),
            "score_explanations": _score_explanations(
                component_scores=input_data.component_scores,
                aggregate_score=aggregate_score,
                confidence_tier=confidence_tier,
            ),
            "final_explanation": (
                "Action state is deterministic and does not imply live-trading approval; "
                "it indicates reject, watch, paper candidate, or paper approved."
            ),
        },
        "metadata": dict(sorted((input_data.metadata or {}).items())),
    }
    return validate_decision_card(payload)


def compute_aggregate_score(*, component_scores: list[ComponentScore]) -> float:
    """Compute bounded weighted aggregate score in [0, 100]."""
    score_by_category = {component.category: float(component.score) for component in component_scores}
    required_categories = set(REQUIRED_COMPONENT_CATEGORIES)
    if set(score_by_category) != required_categories:
        missing = sorted(required_categories - set(score_by_category))
        extra = sorted(set(score_by_category) - required_categories)
        details: list[str] = []
        if missing:
            details.append(f"missing={','.join(missing)}")
        if extra:
            details.append(f"extra={','.join(extra)}")
        raise ValueError(f"Component scores must cover required categories ({'; '.join(details)})")
    weighted = sum(score_by_category[category] * COMPONENT_WEIGHTS[category] for category in REQUIRED_COMPONENT_CATEGORIES)
    return max(0.0, min(100.0, round(weighted, 4)))


def assign_confidence_tier(
    *,
    aggregate_score: float,
    component_scores: list[ComponentScore],
) -> DecisionConfidenceTier:
    """Assign deterministic confidence tier from bounded aggregate and minimum component score."""
    min_component = min(float(component.score) for component in component_scores)
    if (
        aggregate_score >= CONFIDENCE_THRESHOLDS["high_aggregate"]
        and min_component >= CONFIDENCE_THRESHOLDS["high_min_component"]
    ):
        return "high"
    if (
        aggregate_score >= CONFIDENCE_THRESHOLDS["medium_aggregate"]
        and min_component >= CONFIDENCE_THRESHOLDS["medium_min_component"]
    ):
        return "medium"
    return "low"


def resolve_qualification_state(
    *,
    hard_gate_evaluation: HardGateEvaluation,
    aggregate_score: float,
    confidence_tier: DecisionConfidenceTier,
) -> tuple[DecisionActionState, QualificationColor, str]:
    """Resolve action-state and traffic-light output deterministically."""
    if hard_gate_evaluation.has_blocking_failure:
        return (
            "reject",
            "red",
            "Blocking hard gate failed; opportunity is rejected.",
        )
    if confidence_tier == "low" or aggregate_score < CONFIDENCE_THRESHOLDS["medium_aggregate"]:
        return (
            "watch",
            "yellow",
            "Opportunity remains on watch pending stronger confidence or score.",
        )
    if confidence_tier == "high" and aggregate_score >= CONFIDENCE_THRESHOLDS["high_aggregate"]:
        return (
            "paper_approved",
            "green",
            "Opportunity is approved for bounded paper-trading only.",
        )
    return (
        "paper_candidate",
        "yellow",
        "Opportunity is a paper-trading candidate but not yet approved.",
    )


def _confidence_reason(*, confidence_tier: DecisionConfidenceTier, aggregate_score: float) -> str:
    if confidence_tier == "high":
        return (
            f"Aggregate score {aggregate_score:.4f} and all components satisfy high-confidence thresholds."
        )
    if confidence_tier == "medium":
        return (
            f"Aggregate score {aggregate_score:.4f} satisfies medium-confidence thresholds with bounded component support."
        )
    return (
        f"Aggregate score {aggregate_score:.4f} or component minimum is below medium-confidence thresholds."
    )


def _gate_explanations(*, hard_gate_evaluation: HardGateEvaluation) -> list[str]:
    ordered = sorted(hard_gate_evaluation.gates, key=lambda gate: gate.gate_id)
    explanations: list[str] = []
    for gate in ordered:
        if gate.status == "pass":
            explanations.append(f"Gate {gate.gate_id} passed: {gate.reason}")
        else:
            suffix = "blocking" if gate.blocking else "non-blocking"
            explanations.append(
                f"Gate {gate.gate_id} failed ({suffix}): {gate.failure_reason}"
            )
    return explanations


def _score_explanations(
    *,
    component_scores: list[ComponentScore],
    aggregate_score: float,
    confidence_tier: DecisionConfidenceTier,
) -> list[str]:
    ordered = sorted(component_scores, key=lambda component: component.category)
    component_summary = ", ".join(
        f"{component.category}={component.score:.2f}" for component in ordered
    )
    return [
        f"Bounded weighted aggregate score={aggregate_score:.4f} using fixed category weights.",
        f"Component scores by category: {component_summary}.",
        f"Confidence tier resolved deterministically as {confidence_tier}.",
    ]


__all__ = [
    "COMPONENT_WEIGHTS",
    "CONFIDENCE_THRESHOLDS",
    "DecisionActionState",
    "QualificationEngineInput",
    "assign_confidence_tier",
    "compute_aggregate_score",
    "evaluate_qualification",
    "resolve_qualification_state",
]
