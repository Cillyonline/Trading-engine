"""Deterministic capital allocation policy enforcement for portfolio state."""

from __future__ import annotations

from dataclasses import dataclass

from engine.portfolio_framework.contract import PortfolioState
from engine.portfolio_framework.exposure_aggregator import aggregate_portfolio_exposure


@dataclass(frozen=True)
class StrategyAllocationRule:
    """Immutable strategy-level allocation rule.

    Attributes:
        strategy_id: Strategy identifier.
        capital_cap_pct: Maximum absolute notional as a fraction of account equity.
        allocation_score: Static deterministic score used for score-weighted allocation.
    """

    strategy_id: str
    capital_cap_pct: float
    allocation_score: float


@dataclass(frozen=True)
class CapitalAllocationRules:
    """Immutable global and strategy-level capital allocation rules.

    Attributes:
        global_capital_cap_pct: Maximum global absolute notional as fraction of equity.
        strategy_rules: Strategy rules evaluated in deterministic order.
    """

    global_capital_cap_pct: float
    strategy_rules: tuple[StrategyAllocationRule, ...]


@dataclass(frozen=True)
class StrategyAllocationAssessment:
    """Deterministic assessment for a strategy under allocation rules.

    Attributes:
        strategy_id: Strategy identifier.
        allocation_score: Configured deterministic score for this strategy.
        deterministic_score_weight: Normalized score weight from all strategy scores.
        current_absolute_notional: Current strategy gross notional exposure.
        capital_cap_notional: Strategy cap converted to notional limit.
        score_weighted_notional: Score-weighted share of global cap in notional terms.
        effective_allowed_notional: Effective strategy notional cap used for enforcement.
        within_cap: Whether current_absolute_notional is within effective cap.
    """

    strategy_id: str
    allocation_score: float
    deterministic_score_weight: float
    current_absolute_notional: float
    capital_cap_notional: float
    score_weighted_notional: float
    effective_allowed_notional: float
    within_cap: bool


@dataclass(frozen=True)
class CapitalAllocationAssessment:
    """Deterministic portfolio-wide allocation policy assessment.

    Attributes:
        approved: Overall approval status for allocation enforcement.
        reasons: Deterministically ordered violation reasons.
        total_absolute_notional: Current global gross notional exposure.
        global_cap_notional: Global cap converted to notional limit.
        global_within_cap: Whether global exposure is within global cap.
        strategy_assessments: Per-strategy deterministic assessments.
    """

    approved: bool
    reasons: tuple[str, ...]
    total_absolute_notional: float
    global_cap_notional: float
    global_within_cap: bool
    strategy_assessments: tuple[StrategyAllocationAssessment, ...]


def assess_capital_allocation(
    state: PortfolioState,
    rules: CapitalAllocationRules,
) -> CapitalAllocationAssessment:
    """Assess portfolio capital usage against immutable deterministic rules.

    Args:
        state: Immutable portfolio state.
        rules: Immutable global and strategy-level capital allocation rules.

    Returns:
        CapitalAllocationAssessment: Deterministic allocation policy assessment.
    """

    exposure_summary = aggregate_portfolio_exposure(state)
    absolute_equity = abs(state.account_equity)

    global_cap_notional = rules.global_capital_cap_pct * absolute_equity
    total_absolute_notional = exposure_summary.total_absolute_notional
    global_within_cap = total_absolute_notional <= global_cap_notional

    strategy_notional_by_id = {
        row.strategy_id: row.total_absolute_notional
        for row in exposure_summary.strategy_exposures
    }

    ordered_rules = tuple(sorted(rules.strategy_rules, key=lambda item: item.strategy_id))
    total_score = sum(rule.allocation_score for rule in ordered_rules)

    strategy_assessments = tuple(
        _assess_strategy(
            rule=rule,
            total_score=total_score,
            global_cap_notional=global_cap_notional,
            strategy_notional_by_id=strategy_notional_by_id,
            absolute_equity=absolute_equity,
        )
        for rule in ordered_rules
    )

    violated_strategy_ids = tuple(
        item.strategy_id for item in strategy_assessments if not item.within_cap
    )

    reasons = _build_reasons(
        global_within_cap=global_within_cap,
        total_absolute_notional=total_absolute_notional,
        global_cap_notional=global_cap_notional,
        violated_strategy_ids=violated_strategy_ids,
    )

    return CapitalAllocationAssessment(
        approved=global_within_cap and not violated_strategy_ids,
        reasons=reasons,
        total_absolute_notional=total_absolute_notional,
        global_cap_notional=global_cap_notional,
        global_within_cap=global_within_cap,
        strategy_assessments=strategy_assessments,
    )


def _assess_strategy(
    *,
    rule: StrategyAllocationRule,
    total_score: float,
    global_cap_notional: float,
    strategy_notional_by_id: dict[str, float],
    absolute_equity: float,
) -> StrategyAllocationAssessment:
    """Build deterministic strategy-level cap assessment.

    Args:
        rule: Strategy allocation rule.
        total_score: Sum of all strategy allocation scores.
        global_cap_notional: Global notional cap.
        strategy_notional_by_id: Strategy gross exposure lookup.
        absolute_equity: Absolute account equity.

    Returns:
        StrategyAllocationAssessment: Deterministic strategy cap assessment row.
    """

    deterministic_score_weight = _safe_ratio(rule.allocation_score, total_score)
    current_absolute_notional = strategy_notional_by_id.get(rule.strategy_id, 0.0)
    capital_cap_notional = rule.capital_cap_pct * absolute_equity
    score_weighted_notional = deterministic_score_weight * global_cap_notional
    effective_allowed_notional = min(capital_cap_notional, score_weighted_notional)

    return StrategyAllocationAssessment(
        strategy_id=rule.strategy_id,
        allocation_score=rule.allocation_score,
        deterministic_score_weight=deterministic_score_weight,
        current_absolute_notional=current_absolute_notional,
        capital_cap_notional=capital_cap_notional,
        score_weighted_notional=score_weighted_notional,
        effective_allowed_notional=effective_allowed_notional,
        within_cap=current_absolute_notional <= effective_allowed_notional,
    )


def _build_reasons(
    *,
    global_within_cap: bool,
    total_absolute_notional: float,
    global_cap_notional: float,
    violated_strategy_ids: tuple[str, ...],
) -> tuple[str, ...]:
    """Return deterministically ordered violation reasons.

    Args:
        global_within_cap: Whether global exposure is within cap.
        total_absolute_notional: Current total absolute notional.
        global_cap_notional: Allowed global cap notional.
        violated_strategy_ids: Strategy identifiers that violated strategy limits.

    Returns:
        tuple[str, ...]: Deterministically ordered violation reasons.
    """

    reasons: list[str] = []

    if not global_within_cap:
        reasons.append(
            "global_cap_exceeded: "
            f"total_absolute_notional={total_absolute_notional} "
            f"global_cap_notional={global_cap_notional}"
        )

    reasons.extend(
        f"strategy_cap_exceeded: strategy_id={strategy_id}"
        for strategy_id in sorted(violated_strategy_ids)
    )

    return tuple(reasons)


def _safe_ratio(numerator: float, denominator: float) -> float:
    """Return deterministic ratio and avoid division by zero.

    Args:
        numerator: Ratio numerator.
        denominator: Ratio denominator.

    Returns:
        float: Deterministic ratio; 0.0 when denominator is zero.
    """

    if denominator == 0.0:
        return 0.0
    return numerator / denominator
