"""Deterministic qualification engine for decision-card evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from cilly_trading.engine.decision_card_contract import (
    ACTION_ENTRY_WIN_RATE_MIN,
    ACTION_EXIT_WIN_RATE_MAX,
    DECISION_CARD_CONTRACT_VERSION,
    BoundedTraderRelevanceValidation,
    CONFIDENCE_TIER_PRECISION_DISCLAIMER,
    QUALIFICATION_PROFILE_ROBUSTNESS_INTERPRETATION_BOUNDARY,
    UPSTREAM_EVIDENCE_QUALITY_CONFIDENCE_BOUND,
    REQUIRED_COMPONENT_CATEGORIES,
    ComponentScore,
    DecisionCard,
    DecisionAction,
    DecisionComponentCategory,
    DecisionConfidenceTier,
    HardGateEvaluation,
    HardGateResult,
    QualificationColor,
    QualificationProfileRobustnessAudit,
    QualificationProfileRobustnessSliceResult,
    QualificationState,
    evaluate_bounded_trader_relevance_cases,
    validate_decision_card,
)
from cilly_trading.strategies.registry import (
    get_registered_strategy_metadata,
    resolve_qualification_profile_robustness_slices,
    resolve_qualification_threshold_profile,
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
WIN_RATE_SIGNAL_QUALITY_WEIGHT = 0.60
WIN_RATE_BACKTEST_QUALITY_WEIGHT = 0.40
EXPECTED_VALUE_REWARD_MULTIPLIER_MIN = 0.50
EXPECTED_VALUE_REWARD_MULTIPLIER_MAX = 1.50
EXPECTED_VALUE_MIN = -1.0
EXPECTED_VALUE_MAX = 1.0
QUALIFICATION_STATE_RANKS: dict[QualificationState, int] = {
    "reject": 0,
    "watch": 1,
    "paper_candidate": 2,
    "paper_approved": 3,
}
CONFIDENCE_TIER_RANKS: dict[DecisionConfidenceTier, int] = {
    "low": 0,
    "medium": 1,
    "high": 2,
}


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
class QualificationProfileSnapshot:
    qualification_state: QualificationState
    action: DecisionAction
    confidence_tier: DecisionConfidenceTier
    aggregate_score: float
    base_aggregate_score: float
    win_rate: float
    expected_value: float
    has_blocking_failure: bool


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
    threshold_profile = _resolve_threshold_profile(strategy_id=input_data.strategy_id)
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
        confidence_thresholds=threshold_profile["thresholds"],
    )
    confidence_reason = _confidence_reason(confidence_tier=confidence_tier, aggregate_score=aggregate_score)
    win_rate = compute_bounded_win_rate(component_scores=integrated_component_scores)
    expected_value = compute_bounded_expected_value(
        component_scores=integrated_component_scores,
        win_rate=win_rate,
    )
    state, color, qualification_summary = resolve_qualification_state(
        hard_gate_evaluation=hard_gate_evaluation,
        aggregate_score=aggregate_score,
        confidence_tier=confidence_tier,
        confidence_thresholds=threshold_profile["thresholds"],
    )
    action = resolve_decision_action(
        hard_gate_evaluation=hard_gate_evaluation,
        aggregate_score=aggregate_score,
        confidence_tier=confidence_tier,
        qualification_state=state,
        win_rate=win_rate,
        expected_value=expected_value,
        confidence_thresholds=threshold_profile["thresholds"],
    )
    robustness_audit = _evaluate_qualification_profile_robustness_audit(
        generated_at_utc=input_data.generated_at_utc,
        hard_gates=hard_gate_evaluation.gates,
        hard_gate_policy_version=input_data.hard_gate_policy_version,
        component_scores=integrated_component_scores,
        sentiment_overlay=input_data.sentiment_overlay,
        threshold_profile=threshold_profile,
        baseline_snapshot=QualificationProfileSnapshot(
            qualification_state=state,
            action=action,
            confidence_tier=confidence_tier,
            aggregate_score=aggregate_score,
            base_aggregate_score=base_aggregate_score,
            win_rate=win_rate,
            expected_value=expected_value,
            has_blocking_failure=hard_gate_evaluation.has_blocking_failure,
        ),
    )
    gate_explanations = _gate_explanations(hard_gate_evaluation=hard_gate_evaluation)
    score_explanations = _score_explanations(
        component_scores=integrated_component_scores,
        base_aggregate_score=base_aggregate_score,
        aggregate_score=aggregate_score,
        confidence_tier=confidence_tier,
        threshold_profile=threshold_profile,
        win_rate=win_rate,
        expected_value=expected_value,
        action=action,
        sentiment_resolution=sentiment_resolution,
        backtest_input_applied=input_data.backtest_evidence is not None,
        portfolio_fit_input_applied=input_data.portfolio_fit_input is not None,
        robustness_audit=robustness_audit,
    )
    rationale_summary = (
        "Qualification is resolved from explicit hard gates, bounded scores, and confidence rules."
    )
    final_explanation = (
        "Decision action and qualification are deterministic technical implementation evidence "
        "and does not imply live-trading approval, paper profitability, or trader_validation gate completion. "
        "Validation gate status remains explicitly separate and defaults to trader_validation_not_started "
        "unless governed evidence is recorded. "
        f"{robustness_audit.interpretation_limit}"
    )
    trader_relevance_validation = evaluate_bounded_trader_relevance_cases(
        qualification_state=state,
        action=action,
        win_rate=win_rate,
        expected_value=expected_value,
        qualification_summary=qualification_summary,
        rationale_summary=rationale_summary,
        final_explanation=final_explanation,
        gate_explanations=gate_explanations,
        score_explanations=score_explanations,
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
            "win_rate": win_rate,
            "expected_value": expected_value,
        },
        "action": action,
        "qualification": {
            "state": state,
            "color": color,
            "summary": qualification_summary,
        },
        "rationale": {
            "summary": rationale_summary,
            "gate_explanations": gate_explanations,
            "score_explanations": score_explanations,
            "final_explanation": final_explanation,
        },
        "metadata": _build_metadata(
            input_data=input_data,
            base_aggregate_score=base_aggregate_score,
            sentiment_resolution=sentiment_resolution,
            threshold_profile=threshold_profile,
            win_rate=win_rate,
            expected_value=expected_value,
            action=action,
            trader_relevance_validation=trader_relevance_validation,
            robustness_audit=robustness_audit,
        ),
    }
    return validate_decision_card(payload)


def _resolve_threshold_profile(*, strategy_id: str) -> dict[str, object]:
    metadata_by_strategy = get_registered_strategy_metadata()
    strategy_metadata = metadata_by_strategy.get(strategy_id, {})
    comparison_group = strategy_metadata.get("comparison_group")
    profile = resolve_qualification_threshold_profile(comparison_group=comparison_group)
    return {
        "comparison_group": comparison_group if isinstance(comparison_group, str) else "default",
        "profile_id": str(profile["profile_id"]),
        "thresholds": {
            "high_aggregate": float(profile["high_aggregate"]),
            "high_min_component": float(profile["high_min_component"]),
            "medium_aggregate": float(profile["medium_aggregate"]),
            "medium_min_component": float(profile["medium_min_component"]),
        },
    }


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
    confidence_thresholds: dict[str, float] | None = None,
) -> DecisionConfidenceTier:
    """Assign deterministic confidence tier from bounded aggregate and minimum component score."""
    thresholds = confidence_thresholds or CONFIDENCE_THRESHOLDS
    min_component = min(float(component.score) for component in component_scores)
    if (
        aggregate_score >= thresholds["high_aggregate"]
        and min_component >= thresholds["high_min_component"]
    ):
        return "high"
    if (
        aggregate_score >= thresholds["medium_aggregate"]
        and min_component >= thresholds["medium_min_component"]
    ):
        return "medium"
    return "low"


def compute_bounded_win_rate(*, component_scores: list[ComponentScore]) -> float:
    """Compute bounded win-rate evidence in [0, 1] from deterministic component inputs."""
    score_by_category = {component.category: float(component.score) for component in component_scores}
    weighted_score = (
        (score_by_category["signal_quality"] * WIN_RATE_SIGNAL_QUALITY_WEIGHT)
        + (score_by_category["backtest_quality"] * WIN_RATE_BACKTEST_QUALITY_WEIGHT)
    )
    return max(0.0, min(1.0, round(weighted_score / 100.0, 4)))


def compute_bounded_expected_value(
    *,
    component_scores: list[ComponentScore],
    win_rate: float,
) -> float:
    """Compute bounded expected value in [-1, 1] from win-rate and reward multiplier evidence."""
    score_by_category = {component.category: float(component.score) for component in component_scores}
    reward_multiplier = (
        score_by_category["risk_alignment"] + score_by_category["execution_readiness"]
    ) / 100.0
    bounded_reward_multiplier = max(
        EXPECTED_VALUE_REWARD_MULTIPLIER_MIN,
        min(EXPECTED_VALUE_REWARD_MULTIPLIER_MAX, reward_multiplier),
    )
    expected_value = (win_rate * bounded_reward_multiplier) - (1.0 - win_rate)
    return max(EXPECTED_VALUE_MIN, min(EXPECTED_VALUE_MAX, round(expected_value, 4)))


def resolve_qualification_state(
    *,
    hard_gate_evaluation: HardGateEvaluation,
    aggregate_score: float,
    confidence_tier: DecisionConfidenceTier,
    confidence_thresholds: dict[str, float] | None = None,
) -> tuple[DecisionActionState, QualificationColor, str]:
    """Resolve action-state and traffic-light output deterministically."""
    thresholds = confidence_thresholds or CONFIDENCE_THRESHOLDS
    if hard_gate_evaluation.has_blocking_failure:
        return (
            "reject",
            "red",
            "Blocking hard gate failed; opportunity is rejected for paper-trading qualification.",
        )
    if confidence_tier == "low" or aggregate_score < thresholds["medium_aggregate"]:
        return (
            "watch",
            "yellow",
            "Opportunity remains on watch for paper-trading pending stronger confidence or score.",
        )
    if confidence_tier == "high" and aggregate_score >= thresholds["high_aggregate"]:
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


def resolve_decision_action(
    *,
    hard_gate_evaluation: HardGateEvaluation,
    aggregate_score: float,
    confidence_tier: DecisionConfidenceTier,
    qualification_state: DecisionActionState,
    win_rate: float,
    expected_value: float,
    confidence_thresholds: dict[str, float] | None = None,
) -> DecisionAction:
    """Resolve deterministic paper-evaluation action from bounded evidence fields."""
    thresholds = confidence_thresholds or CONFIDENCE_THRESHOLDS
    if hard_gate_evaluation.has_blocking_failure:
        return "ignore"
    if expected_value < 0.0:
        return "exit"
    if qualification_state in {"paper_candidate", "paper_approved"} and win_rate <= ACTION_EXIT_WIN_RATE_MAX:
        return "exit"
    if confidence_tier == "low" or aggregate_score < thresholds["medium_aggregate"]:
        return "ignore"
    if qualification_state in {"paper_candidate", "paper_approved"} and win_rate >= ACTION_ENTRY_WIN_RATE_MIN:
        return "entry"
    return "ignore"


def _confidence_reason(*, confidence_tier: DecisionConfidenceTier, aggregate_score: float) -> str:
    if confidence_tier == "high":
        return (
            f"Aggregate score {aggregate_score:.4f} and all components satisfy high-confidence thresholds "
            f"bounded by upstream evidence quality; "
            f"{CONFIDENCE_TIER_PRECISION_DISCLAIMER}"
        )
    if confidence_tier == "medium":
        return (
            f"Aggregate score {aggregate_score:.4f} satisfies medium-confidence thresholds with bounded component support "
            f"limited by upstream evidence quality; "
            f"{CONFIDENCE_TIER_PRECISION_DISCLAIMER}"
        )
    return (
        f"Aggregate score {aggregate_score:.4f} or component minimum is below medium-confidence thresholds; "
        f"confidence is limited by upstream evidence quality; "
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
    threshold_profile: dict[str, object],
    win_rate: float,
    expected_value: float,
    action: DecisionAction,
    sentiment_resolution: SentimentOverlayResolution,
    backtest_input_applied: bool,
    portfolio_fit_input_applied: bool,
    robustness_audit: QualificationProfileRobustnessAudit,
) -> list[str]:
    ordered = sorted(component_scores, key=lambda component: component.category)
    component_summary = ", ".join(
        f"{component.category}={component.score:.2f}" for component in ordered
    )
    return [
        f"Backtest input path is {'explicitly integrated' if backtest_input_applied else 'not provided; component value is used as-is'}.",
        f"Portfolio-fit input path is {'explicitly integrated' if portfolio_fit_input_applied else 'not provided; component value is used as-is'}.",
        (
            "Qualification threshold profile applied: "
            f"{threshold_profile['profile_id']} "
            f"(comparison_group={threshold_profile['comparison_group']}, "
            f"high_aggregate={threshold_profile['thresholds']['high_aggregate']:.4f}, "
            f"high_min_component={threshold_profile['thresholds']['high_min_component']:.4f}, "
            f"medium_aggregate={threshold_profile['thresholds']['medium_aggregate']:.4f}, "
            f"medium_min_component={threshold_profile['thresholds']['medium_min_component']:.4f})."
        ),
        f"Bounded weighted aggregate score={base_aggregate_score:.4f} using fixed category weights.",
        (
            "Bounded win-rate formula: "
            "win_rate=((signal_quality*0.60)+(backtest_quality*0.40))/100 -> "
            f"{win_rate:.4f}."
        ),
        (
            "Bounded expected-value formula: "
            "expected_value=(win_rate*bounded_reward_multiplier)-(1-win_rate), "
            "bounded_reward_multiplier=clamp((risk_alignment+execution_readiness)/100,0.50,1.50) -> "
            f"{expected_value:.4f}."
        ),
        (
            f"Sentiment overlay status={sentiment_resolution.status}, points={sentiment_resolution.points:.4f}, "
            f"cap={sentiment_resolution.cap_points:.4f}."
        ),
        f"Final aggregate score after sentiment overlay={aggregate_score:.4f}.",
        f"Component scores by category: {component_summary}.",
        f"Confidence tier resolved deterministically as {confidence_tier}.",
        (
            "Action rules: blocking hard-gate failure -> ignore; negative expected value -> exit; "
            f"qualified win_rate <= {ACTION_EXIT_WIN_RATE_MAX:.2f} -> exit; "
            f"qualified win_rate >= {ACTION_ENTRY_WIN_RATE_MIN:.2f} with non-negative expected value -> entry; "
            f"else ignore. Resolved action={action}."
        ),
        f"Qualification-profile robustness audit: {robustness_audit.audit_summary}",
        f"Robustness interpretation boundary: {robustness_audit.interpretation_limit}",
    ]


def _evaluate_qualification_profile_robustness_audit(
    *,
    generated_at_utc: str,
    hard_gates: list[HardGateResult],
    hard_gate_policy_version: str,
    component_scores: list[ComponentScore],
    sentiment_overlay: SentimentOverlayInput | None,
    threshold_profile: dict[str, object],
    baseline_snapshot: QualificationProfileSnapshot,
) -> QualificationProfileRobustnessAudit:
    comparison_group = str(threshold_profile["comparison_group"])
    slice_definitions = resolve_qualification_profile_robustness_slices(
        comparison_group=comparison_group
    )
    slice_results: list[QualificationProfileRobustnessSliceResult] = []
    for slice_definition in slice_definitions:
        adjusted_snapshot = _resolve_qualification_profile_snapshot(
            generated_at_utc=generated_at_utc,
            hard_gates=hard_gates,
            hard_gate_policy_version=hard_gate_policy_version,
            component_scores=component_scores,
            sentiment_overlay=sentiment_overlay,
            threshold_profile=threshold_profile,
            component_score_adjustments=dict(slice_definition["component_score_adjustments"]),
        )
        behavior_status = _classify_robustness_behavior(
            baseline_snapshot=baseline_snapshot,
            slice_snapshot=adjusted_snapshot,
            slice_type=str(slice_definition["slice_type"]),
        )
        slice_results.append(
            QualificationProfileRobustnessSliceResult(
                slice_id=str(slice_definition["slice_id"]),
                slice_type=str(slice_definition["slice_type"]),
                deterministic_rank=int(slice_definition["deterministic_rank"]),
                description=str(slice_definition["description"]),
                behavior_status=behavior_status,
                qualification_state=adjusted_snapshot.qualification_state,
                action=adjusted_snapshot.action,
                confidence_tier=adjusted_snapshot.confidence_tier,
                aggregate_score=adjusted_snapshot.aggregate_score,
                base_aggregate_score=adjusted_snapshot.base_aggregate_score,
                win_rate=adjusted_snapshot.win_rate,
                expected_value=adjusted_snapshot.expected_value,
                has_blocking_failure=adjusted_snapshot.has_blocking_failure,
                applied_adjustments=_robustness_adjustment_entries(
                    component_score_adjustments=dict(slice_definition["component_score_adjustments"])
                ),
                finding=_robustness_finding(
                    baseline_snapshot=baseline_snapshot,
                    slice_snapshot=adjusted_snapshot,
                    behavior_status=behavior_status,
                ),
            )
        )

    stable_slice_ids = sorted(
        item.slice_id for item in slice_results if item.behavior_status == "stable"
    )
    weak_slice_ids = sorted(item.slice_id for item in slice_results if item.behavior_status == "weak")
    failing_slice_ids = sorted(
        item.slice_id for item in slice_results if item.behavior_status == "failing"
    )
    audit_summary = (
        f"Deterministic qualification-profile robustness audit covered {len(slice_results)} slices "
        f"for comparison_group={comparison_group}: stable={_format_slice_ids(stable_slice_ids)}; "
        f"weak={_format_slice_ids(weak_slice_ids)}; failing={_format_slice_ids(failing_slice_ids)}."
    )
    return QualificationProfileRobustnessAudit(
        comparison_group=comparison_group,
        threshold_profile_id=str(threshold_profile["profile_id"]),
        stable_slice_ids=stable_slice_ids,
        weak_slice_ids=weak_slice_ids,
        failing_slice_ids=failing_slice_ids,
        slice_results=slice_results,
        audit_summary=audit_summary,
        interpretation_limit=QUALIFICATION_PROFILE_ROBUSTNESS_INTERPRETATION_BOUNDARY,
    )


def _resolve_qualification_profile_snapshot(
    *,
    generated_at_utc: str,
    hard_gates: list[HardGateResult],
    hard_gate_policy_version: str,
    component_scores: list[ComponentScore],
    sentiment_overlay: SentimentOverlayInput | None,
    threshold_profile: dict[str, object],
    component_score_adjustments: dict[str, float],
) -> QualificationProfileSnapshot:
    adjusted_components = _apply_robustness_component_adjustments(
        component_scores=component_scores,
        component_score_adjustments=component_score_adjustments,
    )
    hard_gate_evaluation = HardGateEvaluation(
        policy_version=hard_gate_policy_version,
        gates=list(hard_gates),
    )
    base_aggregate_score = compute_aggregate_score(component_scores=adjusted_components)
    sentiment_resolution = _resolve_sentiment_overlay(
        sentiment_overlay=sentiment_overlay,
        generated_at_utc=generated_at_utc,
        component_scores=adjusted_components,
    )
    aggregate_score = _apply_sentiment_overlay(
        base_aggregate_score=base_aggregate_score,
        sentiment_resolution=sentiment_resolution,
    )
    confidence_tier = assign_confidence_tier(
        aggregate_score=aggregate_score,
        component_scores=adjusted_components,
        confidence_thresholds=threshold_profile["thresholds"],
    )
    win_rate = compute_bounded_win_rate(component_scores=adjusted_components)
    expected_value = compute_bounded_expected_value(
        component_scores=adjusted_components,
        win_rate=win_rate,
    )
    qualification_state, _, _ = resolve_qualification_state(
        hard_gate_evaluation=hard_gate_evaluation,
        aggregate_score=aggregate_score,
        confidence_tier=confidence_tier,
        confidence_thresholds=threshold_profile["thresholds"],
    )
    action = resolve_decision_action(
        hard_gate_evaluation=hard_gate_evaluation,
        aggregate_score=aggregate_score,
        confidence_tier=confidence_tier,
        qualification_state=qualification_state,
        win_rate=win_rate,
        expected_value=expected_value,
        confidence_thresholds=threshold_profile["thresholds"],
    )
    return QualificationProfileSnapshot(
        qualification_state=qualification_state,
        action=action,
        confidence_tier=confidence_tier,
        aggregate_score=aggregate_score,
        base_aggregate_score=base_aggregate_score,
        win_rate=win_rate,
        expected_value=expected_value,
        has_blocking_failure=hard_gate_evaluation.has_blocking_failure,
    )


def _apply_robustness_component_adjustments(
    *,
    component_scores: list[ComponentScore],
    component_score_adjustments: dict[str, float],
) -> list[ComponentScore]:
    adjusted_components: list[ComponentScore] = []
    for component in component_scores:
        delta = float(component_score_adjustments.get(component.category, 0.0))
        adjusted_components.append(
            ComponentScore(
                category=component.category,
                score=_clamp_audit_component_score(float(component.score) + delta),
                rationale=component.rationale,
                evidence=list(component.evidence),
            )
        )
    return adjusted_components


def _clamp_audit_component_score(value: float) -> float:
    return max(0.0, min(100.0, round(float(value), 4)))


def _classify_robustness_behavior(
    *,
    baseline_snapshot: QualificationProfileSnapshot,
    slice_snapshot: QualificationProfileSnapshot,
    slice_type: str,
) -> str:
    if slice_type == "covered":
        return "stable"
    if slice_snapshot.has_blocking_failure or slice_snapshot.qualification_state == "reject":
        return "failing"
    baseline_state_rank = QUALIFICATION_STATE_RANKS[baseline_snapshot.qualification_state]
    slice_state_rank = QUALIFICATION_STATE_RANKS[slice_snapshot.qualification_state]
    baseline_confidence_rank = CONFIDENCE_TIER_RANKS[baseline_snapshot.confidence_tier]
    slice_confidence_rank = CONFIDENCE_TIER_RANKS[slice_snapshot.confidence_tier]
    if baseline_snapshot.action == "entry" and slice_snapshot.action in {"ignore", "exit"}:
        return "failing"
    if slice_state_rank < (baseline_state_rank - 1):
        return "failing"
    if (
        slice_state_rank >= baseline_state_rank
        and slice_snapshot.action == baseline_snapshot.action
        and slice_confidence_rank >= baseline_confidence_rank
    ):
        return "stable"
    return "weak"


def _robustness_adjustment_entries(*, component_score_adjustments: dict[str, float]) -> list[str]:
    if not component_score_adjustments:
        return ["component_score_adjustments=none"]
    return [
        f"{category} delta={float(delta):.4f}"
        for category, delta in sorted(component_score_adjustments.items())
    ]


def _robustness_finding(
    *,
    baseline_snapshot: QualificationProfileSnapshot,
    slice_snapshot: QualificationProfileSnapshot,
    behavior_status: str,
) -> str:
    baseline_label = (
        f"{baseline_snapshot.qualification_state}/{baseline_snapshot.action}/"
        f"{baseline_snapshot.confidence_tier}"
    )
    slice_label = (
        f"{slice_snapshot.qualification_state}/{slice_snapshot.action}/"
        f"{slice_snapshot.confidence_tier}"
    )
    if behavior_status == "stable":
        lead = "Slice remained stable relative to covered current evidence."
        boundary = "Interpretation remains bounded to covered conditions only."
    elif behavior_status == "weak":
        lead = "Slice degraded profile support relative to covered current evidence."
        boundary = "This instability limits interpretation outside covered conditions."
    else:
        lead = "Slice produced failing profile behavior relative to covered current evidence."
        boundary = "Do not generalize stability outside covered conditions from this slice."
    return (
        f"{lead} Baseline={baseline_label}; slice={slice_label}; "
        f"aggregate={slice_snapshot.aggregate_score:.4f}; {boundary}"
    )


def _format_slice_ids(slice_ids: list[str]) -> str:
    return ",".join(slice_ids) if slice_ids else "none"


def _build_metadata(
    *,
    input_data: QualificationEngineInput,
    base_aggregate_score: float,
    sentiment_resolution: SentimentOverlayResolution,
    threshold_profile: dict[str, object],
    win_rate: float,
    expected_value: float,
    action: DecisionAction,
    trader_relevance_validation: BoundedTraderRelevanceValidation,
    robustness_audit: QualificationProfileRobustnessAudit,
) -> dict[str, object]:
    metadata = dict(input_data.metadata or {})
    metadata["base_aggregate_score"] = base_aggregate_score
    metadata["backtest_input_applied"] = input_data.backtest_evidence is not None
    metadata["portfolio_fit_input_applied"] = input_data.portfolio_fit_input is not None
    metadata["comparison_group"] = threshold_profile["comparison_group"]
    metadata["qualification_threshold_profile_id"] = threshold_profile["profile_id"]
    metadata["qualification_thresholds"] = dict(threshold_profile["thresholds"])
    metadata["sentiment_overlay_status"] = sentiment_resolution.status
    metadata["sentiment_overlay_points"] = sentiment_resolution.points
    metadata["sentiment_overlay_cap_points"] = sentiment_resolution.cap_points
    metadata["sentiment_overlay_reason"] = sentiment_resolution.reason
    if sentiment_resolution.sentiment_score is not None:
        metadata["sentiment_overlay_score"] = sentiment_resolution.sentiment_score
    metadata["win_rate"] = win_rate
    metadata["expected_value"] = expected_value
    metadata["decision_action"] = action
    metadata["decision_action_policy_version"] = "paper-action.v1"
    metadata["bounded_trader_relevance_validation"] = trader_relevance_validation.model_dump(mode="python")
    metadata["qualification_profile_robustness_audit"] = robustness_audit.model_dump(mode="python")
    metadata["technical_implementation_status"] = metadata.get(
        "technical_implementation_status", "technical_in_progress"
    )
    metadata["trader_validation_status"] = metadata.get(
        "trader_validation_status", "trader_validation_not_started"
    )
    return dict(sorted(metadata.items()))


__all__ = [
    "COMPONENT_WEIGHTS",
    "CONFIDENCE_THRESHOLDS",
    "UPSTREAM_EVIDENCE_QUALITY_CONFIDENCE_BOUND",
    "BacktestEvidenceInput",
    "DecisionActionState",
    "PortfolioFitInput",
    "QualificationEngineInput",
    "SentimentOverlayInput",
    "SENTIMENT_DEFAULT_STALE_AFTER_HOURS",
    "SENTIMENT_OVERLAY_MAX_POINTS",
    "assign_confidence_tier",
    "compute_bounded_expected_value",
    "compute_bounded_win_rate",
    "compute_aggregate_score",
    "evaluate_qualification",
    "resolve_qualification_threshold_profile",
    "resolve_decision_action",
    "resolve_qualification_state",
]
