"""Deterministic capital allocation policy enforcement for portfolio state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

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
class PrioritizedAllocationSignal:
    """Candidate signal to prioritize for bounded notional allocation.

    Attributes:
        signal_id: Stable signal identifier.
        strategy_id: Strategy identifier that produced the signal.
        symbol: Instrument symbol for this opportunity.
        priority_score: Higher score means higher allocation priority.
        requested_notional: Requested notional amount for this signal.
        signal_timestamp: ISO-8601 timestamp used in deterministic ordering.
        max_position_notional: Optional per-signal cap used as a bounded sizing hook.
    """

    signal_id: str
    strategy_id: str
    symbol: str
    priority_score: float
    requested_notional: float
    signal_timestamp: str
    max_position_notional: float | None = None


@dataclass(frozen=True)
class PrioritizedAllocationConfig:
    """Configuration for deterministic constrained-capital signal allocation.

    Attributes:
        available_capital_notional: Total notional budget for this allocation run.
        max_positions: Maximum number of accepted signals.
        default_position_cap_notional: Default per-position notional cap.
        min_allocation_notional: Minimum notional required for an accepted allocation.
    """

    available_capital_notional: float
    max_positions: int
    default_position_cap_notional: float
    min_allocation_notional: float = 0.0


@dataclass(frozen=True)
class PrioritizedAllocationDecision:
    """Deterministic allocation decision row for one candidate signal."""

    signal_id: str
    strategy_id: str
    symbol: str
    priority_rank: int
    tie_break_key: tuple[float, str, str, str, str]
    requested_notional: float
    bounded_requested_notional: float
    allocated_notional: float
    accepted: bool
    rejection_reason: str | None


@dataclass(frozen=True)
class PrioritizedAllocationResult:
    """Deterministic bounded allocation result."""

    decisions: tuple[PrioritizedAllocationDecision, ...]
    accepted_signal_ids: tuple[str, ...]
    total_allocated_notional: float
    remaining_capital_notional: float


BoundedPositionSizingHook = Callable[[PrioritizedAllocationSignal, float], float]


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
    signals: tuple[PrioritizedAllocationSignal, ...],
    config: PrioritizedAllocationConfig,
    bounded_position_sizing_hook: BoundedPositionSizingHook | None = None,
) -> PrioritizedAllocationResult:
    """Allocate limited capital across competing signals deterministically.

    Prioritization and tie-breaking order:
    1) priority_score DESC
    2) signal_timestamp ASC
    3) strategy_id ASC
    4) symbol ASC
    5) signal_id ASC
    """

    ranked_signals = tuple(sorted(signals, key=_priority_sort_key))
    remaining_capital = max(config.available_capital_notional, 0.0)
    accepted_positions = 0

    decisions: list[PrioritizedAllocationDecision] = []

    for index, signal in enumerate(ranked_signals):
        priority_rank = index + 1
        tie_break_key = _priority_sort_key(signal)
        bounded_requested_notional = _bounded_requested_notional(signal=signal, config=config)

        allocation_budget_available = (
            remaining_capital > 0.0
            and accepted_positions < config.max_positions
            and bounded_requested_notional >= config.min_allocation_notional
        )

        if not allocation_budget_available:
            decisions.append(
                PrioritizedAllocationDecision(
                    signal_id=signal.signal_id,
                    strategy_id=signal.strategy_id,
                    symbol=signal.symbol,
                    priority_rank=priority_rank,
                    tie_break_key=tie_break_key,
                    requested_notional=signal.requested_notional,
                    bounded_requested_notional=bounded_requested_notional,
                    allocated_notional=0.0,
                    accepted=False,
                    rejection_reason=_allocation_rejection_reason(
                        remaining_capital=remaining_capital,
                        accepted_positions=accepted_positions,
                        config=config,
                        bounded_requested_notional=bounded_requested_notional,
                    ),
                )
            )
            continue

        proposed_notional = min(bounded_requested_notional, remaining_capital)
        allocated_notional = _apply_bounded_position_sizing_hook(
            signal=signal,
            proposed_notional=proposed_notional,
            bounded_position_sizing_hook=bounded_position_sizing_hook,
        )
        allocated_notional = min(max(allocated_notional, 0.0), proposed_notional)

        if allocated_notional >= config.min_allocation_notional:
            accepted = True
            rejection_reason = None
            accepted_positions += 1
            remaining_capital -= allocated_notional
        else:
            accepted = False
            rejection_reason = "below_min_allocation_after_bounded_sizing"
            allocated_notional = 0.0

        decisions.append(
            PrioritizedAllocationDecision(
                signal_id=signal.signal_id,
                strategy_id=signal.strategy_id,
                symbol=signal.symbol,
                priority_rank=priority_rank,
                tie_break_key=tie_break_key,
                requested_notional=signal.requested_notional,
                bounded_requested_notional=bounded_requested_notional,
                allocated_notional=allocated_notional,
                accepted=accepted,
                rejection_reason=rejection_reason,
            )
        )

    accepted_signal_ids = tuple(item.signal_id for item in decisions if item.accepted)
    total_allocated_notional = sum(item.allocated_notional for item in decisions)

    return PrioritizedAllocationResult(
        decisions=tuple(decisions),
        accepted_signal_ids=accepted_signal_ids,
        total_allocated_notional=total_allocated_notional,
        remaining_capital_notional=remaining_capital,
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


def _priority_sort_key(signal: PrioritizedAllocationSignal) -> tuple[float, str, str, str, str]:
    return (
        -signal.priority_score,
        signal.signal_timestamp,
        signal.strategy_id,
        signal.symbol,
        signal.signal_id,
    )


def _bounded_requested_notional(
    *,
    signal: PrioritizedAllocationSignal,
    config: PrioritizedAllocationConfig,
) -> float:
    configured_cap = max(config.default_position_cap_notional, 0.0)
    signal_cap = (
        configured_cap
        if signal.max_position_notional is None
        else max(signal.max_position_notional, 0.0)
    )
    return min(max(signal.requested_notional, 0.0), signal_cap)


def _apply_bounded_position_sizing_hook(
    *,
    signal: PrioritizedAllocationSignal,
    proposed_notional: float,
    bounded_position_sizing_hook: BoundedPositionSizingHook | None,
) -> float:
    if bounded_position_sizing_hook is None:
        return proposed_notional
    return bounded_position_sizing_hook(signal, proposed_notional)


def _allocation_rejection_reason(
    *,
    remaining_capital: float,
    accepted_positions: int,
    config: PrioritizedAllocationConfig,
    bounded_requested_notional: float,
) -> str:
    if accepted_positions >= config.max_positions:
        return "position_limit_reached"
    if remaining_capital <= 0.0:
        return "capital_exhausted"
    if bounded_requested_notional < config.min_allocation_notional:
        return "below_min_allocation"
    return "not_allocated"


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
