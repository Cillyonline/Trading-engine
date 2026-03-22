"""Deterministic capital allocation policy and signal prioritization model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from cilly_trading.portfolio_framework.contract import PortfolioState
from cilly_trading.portfolio_framework.exposure_aggregator import aggregate_portfolio_exposure


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


@dataclass(frozen=True)
class SignalAllocationInput:
    """Immutable candidate signal used for deterministic prioritization.

    Attributes:
        signal_id: Stable signal identifier used in deterministic ordering.
        strategy_id: Strategy identifier that owns the signal.
        symbol: Instrument symbol.
        side: Signal direction.
        priority_score: Higher score means higher priority.
        requested_notional: Absolute notional requested by the signal.
        position_size_cap_notional: Optional bounded size hook for this signal.
        deterministic_tie_breaker: Optional explicit final tie-break key.
    """

    signal_id: str
    strategy_id: str
    symbol: str
    side: Literal["buy", "sell"]
    priority_score: float
    requested_notional: float
    position_size_cap_notional: float | None = None
    deterministic_tie_breaker: str = ""


@dataclass(frozen=True)
class SignalAllocationDecision:
    """Deterministic allocation output row for one signal candidate.

    Attributes:
        rank: Deterministic processing rank (1-based).
        signal_id: Stable signal identifier.
        strategy_id: Strategy identifier.
        symbol: Instrument symbol.
        side: Signal direction.
        priority_score: Signal priority score.
        requested_notional: Absolute notional requested by the signal.
        allocated_notional: Bounded notional granted by the allocator.
        allocation_status: Allocation outcome for this signal.
        rejection_reason: Deterministic reason when allocation is zero.
        position_size_cap_notional: Optional per-signal size cap applied.
        remaining_global_cap_notional: Remaining global notional after this row.
        remaining_strategy_cap_notional: Remaining strategy notional after this row.
    """

    rank: int
    signal_id: str
    strategy_id: str
    symbol: str
    side: Literal["buy", "sell"]
    priority_score: float
    requested_notional: float
    allocated_notional: float
    allocation_status: Literal["accepted", "partially_allocated", "rejected"]
    rejection_reason: str | None
    position_size_cap_notional: float | None
    remaining_global_cap_notional: float
    remaining_strategy_cap_notional: float


@dataclass(frozen=True)
class SignalAllocationPlan:
    """Deterministic portfolio signal allocation plan under bounded capital.

    Attributes:
        decisions: Deterministic per-signal allocation decisions.
        selected_signal_ids: Accepted or partially accepted signal ids in rank order.
        remaining_global_cap_notional: Remaining global capacity after allocation.
    """

    decisions: tuple[SignalAllocationDecision, ...]
    selected_signal_ids: tuple[str, ...]
    remaining_global_cap_notional: float


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


def allocate_prioritized_signals(
    *,
    state: PortfolioState,
    rules: CapitalAllocationRules,
    candidates: tuple[SignalAllocationInput, ...],
    max_selected_signals: int | None = None,
) -> SignalAllocationPlan:
    """Allocate bounded capital across competing signals deterministically.

    Prioritization order is:
    1) higher priority_score first
    2) strategy_id ascending
    3) symbol ascending
    4) signal_id ascending
    5) deterministic_tie_breaker ascending

    Args:
        state: Portfolio state used to compute current consumed capacity.
        rules: Global and per-strategy allocation caps.
        candidates: Competing signal candidates.
        max_selected_signals: Optional cap for accepted signal count.

    Returns:
        SignalAllocationPlan: Deterministic bounded allocation plan.
    """

    assessment = assess_capital_allocation(state, rules)
    strategy_remaining = {
        row.strategy_id: max(0.0, row.effective_allowed_notional - row.current_absolute_notional)
        for row in assessment.strategy_assessments
    }
    global_remaining = max(
        0.0,
        assessment.global_cap_notional - assessment.total_absolute_notional,
    )

    ordered_candidates = tuple(
        sorted(
            candidates,
            key=lambda row: (
                -row.priority_score,
                row.strategy_id,
                row.symbol,
                row.signal_id,
                row.deterministic_tie_breaker,
            ),
        )
    )

    selected_count = 0
    decisions: list[SignalAllocationDecision] = []
    selected_signal_ids: list[str] = []

    for rank, candidate in enumerate(ordered_candidates, start=1):
        strategy_cap_remaining = strategy_remaining.get(candidate.strategy_id, 0.0)
        requested_notional = abs(candidate.requested_notional)
        per_signal_cap = (
            None
            if candidate.position_size_cap_notional is None
            else max(0.0, candidate.position_size_cap_notional)
        )

        if requested_notional == 0.0:
            allocated_notional = 0.0
            status: Literal["accepted", "partially_allocated", "rejected"] = "rejected"
            reason = "invalid_requested_notional"
        elif max_selected_signals is not None and selected_count >= max_selected_signals:
            allocated_notional = 0.0
            status = "rejected"
            reason = "max_selected_signals_reached"
        else:
            bounded_notional = min(
                _bound_notional_inputs(
                    requested_notional=requested_notional,
                    global_remaining=global_remaining,
                    strategy_remaining=strategy_cap_remaining,
                    per_signal_cap=per_signal_cap,
                )
            )

            if bounded_notional <= 0.0:
                allocated_notional = 0.0
                status = "rejected"
                reason = "insufficient_capacity"
            elif bounded_notional == requested_notional:
                allocated_notional = bounded_notional
                status = "accepted"
                reason = None
            else:
                allocated_notional = bounded_notional
                status = "partially_allocated"
                reason = None

        if allocated_notional > 0.0:
            global_remaining = max(0.0, global_remaining - allocated_notional)
            strategy_cap_remaining = max(0.0, strategy_cap_remaining - allocated_notional)
            strategy_remaining[candidate.strategy_id] = strategy_cap_remaining
            selected_count += 1
            selected_signal_ids.append(candidate.signal_id)

        decisions.append(
            SignalAllocationDecision(
                rank=rank,
                signal_id=candidate.signal_id,
                strategy_id=candidate.strategy_id,
                symbol=candidate.symbol,
                side=candidate.side,
                priority_score=candidate.priority_score,
                requested_notional=requested_notional,
                allocated_notional=allocated_notional,
                allocation_status=status,
                rejection_reason=reason,
                position_size_cap_notional=per_signal_cap,
                remaining_global_cap_notional=global_remaining,
                remaining_strategy_cap_notional=strategy_cap_remaining,
            )
        )

    return SignalAllocationPlan(
        decisions=tuple(decisions),
        selected_signal_ids=tuple(selected_signal_ids),
        remaining_global_cap_notional=global_remaining,
    )


def _bound_notional_inputs(
    *,
    requested_notional: float,
    global_remaining: float,
    strategy_remaining: float,
    per_signal_cap: float | None,
) -> tuple[float, ...]:
    """Build deterministic bounded notional inputs for min-cap sizing."""

    bounds: list[float] = [requested_notional, global_remaining, strategy_remaining]
    if per_signal_cap is not None:
        bounds.append(per_signal_cap)
    return tuple(bounds)


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
