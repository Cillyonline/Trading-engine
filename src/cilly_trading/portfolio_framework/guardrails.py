"""Deterministic portfolio-level guardrails for exposure and concentration."""

from __future__ import annotations

from dataclasses import dataclass

from cilly_trading.portfolio_framework.contract import PortfolioState
from cilly_trading.portfolio_framework.exposure_aggregator import PortfolioExposureSummary, aggregate_portfolio_exposure


@dataclass(frozen=True)
class PortfolioGuardrailLimits:
    """Immutable portfolio guardrail limits.

    Attributes:
        max_gross_exposure_pct: Maximum portfolio gross exposure as fraction of equity.
        max_abs_net_exposure_pct: Maximum absolute portfolio net exposure as fraction of equity.
        max_offset_exposure_pct: Maximum offsetting exposure (gross-abs(net)) as fraction of equity.
        max_strategy_concentration_pct: Maximum per-strategy gross concentration share of total gross notional.
        max_symbol_concentration_pct: Maximum per-symbol gross concentration share of total gross notional.
        max_position_concentration_pct: Maximum per-position concentration share of total gross notional.
    """

    max_gross_exposure_pct: float
    max_abs_net_exposure_pct: float
    max_offset_exposure_pct: float
    max_strategy_concentration_pct: float
    max_symbol_concentration_pct: float
    max_position_concentration_pct: float


@dataclass(frozen=True)
class PortfolioGuardrailAssessment:
    """Deterministic result of portfolio guardrail enforcement.

    Attributes:
        approved: Whether all guardrails are satisfied.
        reasons: Deterministically ordered violation reasons.
        exposure_summary: Underlying deterministic portfolio exposure summary.
        absolute_net_exposure_pct: Absolute value of net exposure pct.
        offset_exposure_pct: Gross minus absolute net exposure pct.
        max_strategy_concentration_pct_observed: Largest observed strategy concentration.
        max_symbol_concentration_pct_observed: Largest observed symbol concentration.
        max_position_concentration_pct_observed: Largest observed position concentration.
    """

    approved: bool
    reasons: tuple[str, ...]
    exposure_summary: PortfolioExposureSummary
    absolute_net_exposure_pct: float
    offset_exposure_pct: float
    max_strategy_concentration_pct_observed: float
    max_symbol_concentration_pct_observed: float
    max_position_concentration_pct_observed: float


def assess_portfolio_guardrails(
    state: PortfolioState,
    limits: PortfolioGuardrailLimits,
) -> PortfolioGuardrailAssessment:
    """Assess portfolio-level exposure and concentration guardrails deterministically."""

    exposure_summary = aggregate_portfolio_exposure(state)
    gross_exposure_pct = exposure_summary.gross_exposure_pct
    absolute_net_exposure_pct = abs(exposure_summary.net_exposure_pct)
    offset_exposure_pct = gross_exposure_pct - absolute_net_exposure_pct

    max_strategy_concentration_pct_observed = max(
        (_concentration_ratio(row.total_absolute_notional, exposure_summary.total_absolute_notional)
         for row in exposure_summary.strategy_exposures),
        default=0.0,
    )
    max_symbol_concentration_pct_observed = max(
        (_concentration_ratio(row.total_absolute_notional, exposure_summary.total_absolute_notional)
         for row in exposure_summary.symbol_exposures),
        default=0.0,
    )
    max_position_concentration_pct_observed = max(
        (_concentration_ratio(row.absolute_notional, exposure_summary.total_absolute_notional)
         for row in exposure_summary.position_exposures),
        default=0.0,
    )

    reasons = _build_violation_reasons(
        exposure_summary=exposure_summary,
        absolute_net_exposure_pct=absolute_net_exposure_pct,
        offset_exposure_pct=offset_exposure_pct,
        max_strategy_concentration_pct_observed=max_strategy_concentration_pct_observed,
        max_symbol_concentration_pct_observed=max_symbol_concentration_pct_observed,
        max_position_concentration_pct_observed=max_position_concentration_pct_observed,
        limits=limits,
    )

    return PortfolioGuardrailAssessment(
        approved=not reasons,
        reasons=reasons,
        exposure_summary=exposure_summary,
        absolute_net_exposure_pct=absolute_net_exposure_pct,
        offset_exposure_pct=offset_exposure_pct,
        max_strategy_concentration_pct_observed=max_strategy_concentration_pct_observed,
        max_symbol_concentration_pct_observed=max_symbol_concentration_pct_observed,
        max_position_concentration_pct_observed=max_position_concentration_pct_observed,
    )


def _build_violation_reasons(
    *,
    exposure_summary: PortfolioExposureSummary,
    absolute_net_exposure_pct: float,
    offset_exposure_pct: float,
    max_strategy_concentration_pct_observed: float,
    max_symbol_concentration_pct_observed: float,
    max_position_concentration_pct_observed: float,
    limits: PortfolioGuardrailLimits,
) -> tuple[str, ...]:
    reasons: list[str] = []

    if exposure_summary.gross_exposure_pct > limits.max_gross_exposure_pct:
        reasons.append(
            "guardrail_exceeded: "
            f"type=gross_exposure_pct observed={exposure_summary.gross_exposure_pct} "
            f"limit={limits.max_gross_exposure_pct}"
        )

    if absolute_net_exposure_pct > limits.max_abs_net_exposure_pct:
        reasons.append(
            "guardrail_exceeded: "
            f"type=abs_net_exposure_pct observed={absolute_net_exposure_pct} "
            f"limit={limits.max_abs_net_exposure_pct}"
        )

    if offset_exposure_pct > limits.max_offset_exposure_pct:
        reasons.append(
            "guardrail_exceeded: "
            f"type=offset_exposure_pct observed={offset_exposure_pct} "
            f"limit={limits.max_offset_exposure_pct}"
        )

    if max_strategy_concentration_pct_observed > limits.max_strategy_concentration_pct:
        reasons.append(
            "guardrail_exceeded: "
            f"type=strategy_concentration_pct observed={max_strategy_concentration_pct_observed} "
            f"limit={limits.max_strategy_concentration_pct}"
        )

    if max_symbol_concentration_pct_observed > limits.max_symbol_concentration_pct:
        reasons.append(
            "guardrail_exceeded: "
            f"type=symbol_concentration_pct observed={max_symbol_concentration_pct_observed} "
            f"limit={limits.max_symbol_concentration_pct}"
        )

    if max_position_concentration_pct_observed > limits.max_position_concentration_pct:
        reasons.append(
            "guardrail_exceeded: "
            f"type=position_concentration_pct observed={max_position_concentration_pct_observed} "
            f"limit={limits.max_position_concentration_pct}"
        )

    return tuple(reasons)


def _concentration_ratio(absolute_notional: float, total_absolute_notional: float) -> float:
    if total_absolute_notional == 0.0:
        return 0.0
    return absolute_notional / total_absolute_notional
