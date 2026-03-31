"""Deterministic qualification engine for decision-card evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from cilly_trading.engine.decision_card_contract import (
    DECISION_CARD_CONTRACT_VERSION,
    CONFIDENCE_TIER_PRECISION_DISCLAIMER,
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

SENTIMENT_OVERLAY_MAX_POINTS = 4.0
SENTIMENT_DEFAULT_STALE_AFTER_HOURS = 24


@dataclass(frozen=True)
class BacktestEvidenceInput:
    quality_score: float
    rationale: str
    evidence: list[str]


@dataclass(frozen=True)
class PortfolioFitInput:
    fit_score: float
    rationale: str
    evidence: list[str]


@dataclass(frozen=True)
class SentimentOverlayInput:
    sentiment_score: float
    as_of_utc: str
    rationale: str
    evidence: list[str]
    stale_after_hours: int = SENTIMENT_DEFAULT_STALE_AFTER_HOURS


@dataclass(frozen=True)
class SentimentOverlayResolution:
    status: str
    points: float
    cap_points: float
    reason: str
    sentiment_score: float | None = None


@dataclass(frozen=True)
class QualificationEngineInput:
    decision_card_id: str
    generated_at_utc: str
    symbol: str
    strategy_id: str
    hard_gates: list[HardGateResult]
    component_scores: list[ComponentScore]
    backtest_evidence: BacktestEvidenceInput | None = None
    portfolio_fit_input: PortfolioFitInput | None = None
    sentiment_overlay: SentimentOverlayInput | None = None
    hard_gate_policy_version: str = "hard-gates.v1"
    metadata: dict[str, object] | None = None


def evaluate_qualification(input_data: QualificationEngineInput) -> DecisionCard:
    """Evaluate hard gates, component scores, and output a deterministic decision card."""
    hard_gate_evaluation = HardGateEvaluation(
        policy_version=input_data.hard_gate_policy_version,
        gates=list(input_data.hard_gates),
    )
    integrated_component_scores = _integrate_component_inputs(input_data=input_data)
    base_aggregate_score = compute_aggregate_score(component_scores=integrated_component_scores)
    sentiment_resolution = _resolve_sentiment_overlay(
        sentiment_overlay=input_data.sentiment_overlay,
        generated_at_utc=input_data.generated_at_utc,
        component_scores=integrated_component_scores,
    )
    aggregate_score = _apply_sentiment_overlay(
        base_aggregate_score=base_aggregate_score,
        sentiment_resolution=sentiment_resolution,
    )
    confidence_tier = assign_confidence_tier(
        aggregate_score=aggregate_score,
        component_scores=integrated_component_scores,
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
                    integrated_component_scores,
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
                component_scores=integrated_component_scores,
                base_aggregate_score=base_aggregate_score,
                aggregate_score=aggregate_score,
                confidence_tier=confidence_tier,
                sentiment_resolution=sentiment_resolution,
                backtest_input_applied=input_data.backtest_evidence is not None,
                portfolio_fit_input_applied=input_data.portfolio_fit_input is not None,
            ),
            "final_explanation": (
                "Action state is deterministic and does not imply live-trading approval; "
                "it indicates reject, watch, paper candidate, or paper approved."
            ),
        },
        "metadata": _build_metadata(
            input_data=input_data,
            base_aggregate_score=base_aggregate_score,
            sentiment_resolution=sentiment_resolution,
        ),
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


def _integrate_component_inputs(*, input_data: QualificationEngineInput) -> list[ComponentScore]:
    score_by_category = {component.category: component for component in input_data.component_scores}
    if input_data.backtest_evidence is not None:
        backtest = input_data.backtest_evidence
        score_by_category["backtest_quality"] = ComponentScore(
            category="backtest_quality",
            score=_bounded_score(backtest.quality_score, field_name="backtest_evidence.quality_score"),
            rationale=backtest.rationale,
            evidence=list(backtest.evidence) + ["input_path=backtest_evidence"],
        )
    if input_data.portfolio_fit_input is not None:
        portfolio = input_data.portfolio_fit_input
        score_by_category["portfolio_fit"] = ComponentScore(
            category="portfolio_fit",
            score=_bounded_score(portfolio.fit_score, field_name="portfolio_fit_input.fit_score"),
            rationale=portfolio.rationale,
            evidence=list(portfolio.evidence) + ["input_path=portfolio_fit_input"],
        )
    return list(score_by_category.values())


def _bounded_score(value: float, *, field_name: str) -> float:
    if value < 0.0 or value > 100.0:
        raise ValueError(f"{field_name} must be within [0, 100]")
    return round(float(value), 4)


def _resolve_sentiment_overlay(
    *,
    sentiment_overlay: SentimentOverlayInput | None,
    generated_at_utc: str,
    component_scores: list[ComponentScore],
) -> SentimentOverlayResolution:
    if sentiment_overlay is None:
        return SentimentOverlayResolution(
            status="missing",
            points=0.0,
            cap_points=0.0,
            reason="Sentiment overlay missing; applying neutral 0.0000 points.",
        )
    if sentiment_overlay.sentiment_score < -1.0 or sentiment_overlay.sentiment_score > 1.0:
        raise ValueError("sentiment_overlay.sentiment_score must be within [-1, 1]")
    if sentiment_overlay.stale_after_hours < 1:
        raise ValueError("sentiment_overlay.stale_after_hours must be >= 1")

    generated_at = _parse_iso_timestamp(generated_at_utc)
    sentiment_as_of = _parse_iso_timestamp(sentiment_overlay.as_of_utc)
    stale_cutoff = generated_at - timedelta(hours=sentiment_overlay.stale_after_hours)
    if sentiment_as_of < stale_cutoff:
        return SentimentOverlayResolution(
            status="stale",
            points=0.0,
            cap_points=0.0,
            reason=(
                "Sentiment overlay stale relative to decision timestamp; applying neutral 0.0000 points."
            ),
            sentiment_score=round(sentiment_overlay.sentiment_score, 4),
        )

    score_by_category = {component.category: float(component.score) for component in component_scores}
    stronger_average = (
        score_by_category["backtest_quality"]
        + score_by_category["portfolio_fit"]
        + score_by_category["risk_alignment"]
    ) / 3.0
    cap_points = min(
        SENTIMENT_OVERLAY_MAX_POINTS,
        round((stronger_average / 100.0) * SENTIMENT_OVERLAY_MAX_POINTS, 4),
    )
    raw_points = round(sentiment_overlay.sentiment_score * SENTIMENT_OVERLAY_MAX_POINTS, 4)
    points = max(-cap_points, min(cap_points, raw_points))
    return SentimentOverlayResolution(
        status="applied",
        points=round(points, 4),
        cap_points=round(cap_points, 4),
        reason=(
            f"Sentiment overlay applied with bounded impact {points:.4f} "
            f"(raw={raw_points:.4f}, cap={cap_points:.4f})."
        ),
        sentiment_score=round(sentiment_overlay.sentiment_score, 4),
    )


def _apply_sentiment_overlay(
    *,
    base_aggregate_score: float,
    sentiment_resolution: SentimentOverlayResolution,
) -> float:
    return max(0.0, min(100.0, round(base_aggregate_score + sentiment_resolution.points, 4)))


def _parse_iso_timestamp(value: str) -> datetime:
    iso_value = value.replace("Z", "+00:00") if value.endswith("Z") else value
    timestamp = datetime.fromisoformat(iso_value)
    if timestamp.tzinfo is None:
        raise ValueError("Timestamp must include timezone information")
    return timestamp.astimezone(timezone.utc)


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
            "Blocking hard gate failed; opportunity is rejected for paper-trading qualification.",
        )
    if confidence_tier == "low" or aggregate_score < CONFIDENCE_THRESHOLDS["medium_aggregate"]:
        return (
            "watch",
            "yellow",
            "Opportunity remains on watch for paper-trading pending stronger confidence or score.",
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
            f"Aggregate score {aggregate_score:.4f} and all components satisfy high-confidence thresholds; "
            f"{CONFIDENCE_TIER_PRECISION_DISCLAIMER}"
        )
    if confidence_tier == "medium":
        return (
            f"Aggregate score {aggregate_score:.4f} satisfies medium-confidence thresholds with bounded component support; "
            f"{CONFIDENCE_TIER_PRECISION_DISCLAIMER}"
        )
    return (
        f"Aggregate score {aggregate_score:.4f} or component minimum is below medium-confidence thresholds; "
        f"{CONFIDENCE_TIER_PRECISION_DISCLAIMER}"
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
    base_aggregate_score: float,
    aggregate_score: float,
    confidence_tier: DecisionConfidenceTier,
    sentiment_resolution: SentimentOverlayResolution,
    backtest_input_applied: bool,
    portfolio_fit_input_applied: bool,
) -> list[str]:
    ordered = sorted(component_scores, key=lambda component: component.category)
    component_summary = ", ".join(
        f"{component.category}={component.score:.2f}" for component in ordered
    )
    return [
        f"Backtest input path is {'explicitly integrated' if backtest_input_applied else 'not provided; component value is used as-is'}.",
        f"Portfolio-fit input path is {'explicitly integrated' if portfolio_fit_input_applied else 'not provided; component value is used as-is'}.",
        f"Bounded weighted aggregate score={base_aggregate_score:.4f} using fixed category weights.",
        (
            f"Sentiment overlay status={sentiment_resolution.status}, points={sentiment_resolution.points:.4f}, "
            f"cap={sentiment_resolution.cap_points:.4f}."
        ),
        f"Final aggregate score after sentiment overlay={aggregate_score:.4f}.",
        f"Component scores by category: {component_summary}.",
        f"Confidence tier resolved deterministically as {confidence_tier}.",
    ]


def _build_metadata(
    *,
    input_data: QualificationEngineInput,
    base_aggregate_score: float,
    sentiment_resolution: SentimentOverlayResolution,
) -> dict[str, object]:
    metadata = dict(input_data.metadata or {})
    metadata["base_aggregate_score"] = base_aggregate_score
    metadata["backtest_input_applied"] = input_data.backtest_evidence is not None
    metadata["portfolio_fit_input_applied"] = input_data.portfolio_fit_input is not None
    metadata["sentiment_overlay_status"] = sentiment_resolution.status
    metadata["sentiment_overlay_points"] = sentiment_resolution.points
    metadata["sentiment_overlay_cap_points"] = sentiment_resolution.cap_points
    metadata["sentiment_overlay_reason"] = sentiment_resolution.reason
    if sentiment_resolution.sentiment_score is not None:
        metadata["sentiment_overlay_score"] = sentiment_resolution.sentiment_score
    return dict(sorted(metadata.items()))


__all__ = [
    "COMPONENT_WEIGHTS",
    "CONFIDENCE_THRESHOLDS",
    "BacktestEvidenceInput",
    "DecisionActionState",
    "PortfolioFitInput",
    "QualificationEngineInput",
    "SentimentOverlayInput",
    "SENTIMENT_DEFAULT_STALE_AFTER_HOURS",
    "SENTIMENT_OVERLAY_MAX_POINTS",
    "assign_confidence_tier",
    "compute_aggregate_score",
    "evaluate_qualification",
    "resolve_qualification_state",
]
