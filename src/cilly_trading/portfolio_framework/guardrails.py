"""Deterministic portfolio-level guardrails for exposure and concentration."""

from __future__ import annotations

from dataclasses import dataclass

from cilly_trading.non_live_evaluation_contract import (
    NonLiveEvaluationEvidence,
    NonLiveScope,
)
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
        policy_evidence: Structured non-live reject/cap/boundary evidence rows.
    """

    approved: bool
    reasons: tuple[str, ...]
    exposure_summary: PortfolioExposureSummary
    absolute_net_exposure_pct: float
    offset_exposure_pct: float
    max_strategy_concentration_pct_observed: float
    max_symbol_concentration_pct_observed: float
    max_position_concentration_pct_observed: float
    policy_evidence: tuple[NonLiveEvaluationEvidence, ...] = ()


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

    reasons, policy_evidence = _build_violation_assessment(
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
        policy_evidence=policy_evidence,
    )


def _build_violation_assessment(
    *,
    exposure_summary: PortfolioExposureSummary,
    absolute_net_exposure_pct: float,
    offset_exposure_pct: float,
    max_strategy_concentration_pct_observed: float,
    max_symbol_concentration_pct_observed: float,
    max_position_concentration_pct_observed: float,
    limits: PortfolioGuardrailLimits,
) -> tuple[tuple[str, ...], tuple[NonLiveEvaluationEvidence, ...]]:
    reasons: list[str] = []
    policy_evidence: list[NonLiveEvaluationEvidence] = []

    if exposure_summary.gross_exposure_pct > limits.max_gross_exposure_pct:
        reasons.append(_guardrail_reason(
            rule_code="gross_exposure_pct",
            observed_value=exposure_summary.gross_exposure_pct,
            limit_value=limits.max_gross_exposure_pct,
        ))
        policy_evidence.append(
            _guardrail_evidence(
                scope="portfolio",
                rule_code="gross_exposure_pct",
                reason_code=reasons[-1],
                observed_value=exposure_summary.gross_exposure_pct,
                limit_value=limits.max_gross_exposure_pct,
            )
        )

    if absolute_net_exposure_pct > limits.max_abs_net_exposure_pct:
        reasons.append(_guardrail_reason(
            rule_code="abs_net_exposure_pct",
            observed_value=absolute_net_exposure_pct,
            limit_value=limits.max_abs_net_exposure_pct,
        ))
        policy_evidence.append(
            _guardrail_evidence(
                scope="portfolio",
                rule_code="abs_net_exposure_pct",
                reason_code=reasons[-1],
                observed_value=absolute_net_exposure_pct,
                limit_value=limits.max_abs_net_exposure_pct,
            )
        )

    if offset_exposure_pct > limits.max_offset_exposure_pct:
        reasons.append(_guardrail_reason(
            rule_code="offset_exposure_pct",
            observed_value=offset_exposure_pct,
            limit_value=limits.max_offset_exposure_pct,
        ))
        policy_evidence.append(
            _guardrail_evidence(
                scope="portfolio",
                rule_code="offset_exposure_pct",
                reason_code=reasons[-1],
                observed_value=offset_exposure_pct,
                limit_value=limits.max_offset_exposure_pct,
            )
        )

    if max_strategy_concentration_pct_observed > limits.max_strategy_concentration_pct:
        reasons.append(_guardrail_reason(
            rule_code="strategy_concentration_pct",
            observed_value=max_strategy_concentration_pct_observed,
            limit_value=limits.max_strategy_concentration_pct,
        ))
        policy_evidence.append(
            _guardrail_evidence(
                scope="strategy",
                rule_code="strategy_concentration_pct",
                reason_code=reasons[-1],
                observed_value=max_strategy_concentration_pct_observed,
                limit_value=limits.max_strategy_concentration_pct,
            )
        )

    if max_symbol_concentration_pct_observed > limits.max_symbol_concentration_pct:
        reasons.append(_guardrail_reason(
            rule_code="symbol_concentration_pct",
            observed_value=max_symbol_concentration_pct_observed,
            limit_value=limits.max_symbol_concentration_pct,
        ))
        policy_evidence.append(
            _guardrail_evidence(
                scope="symbol",
                rule_code="symbol_concentration_pct",
                reason_code=reasons[-1],
                observed_value=max_symbol_concentration_pct_observed,
                limit_value=limits.max_symbol_concentration_pct,
            )
        )

    if max_position_concentration_pct_observed > limits.max_position_concentration_pct:
        reasons.append(_guardrail_reason(
            rule_code="position_concentration_pct",
            observed_value=max_position_concentration_pct_observed,
            limit_value=limits.max_position_concentration_pct,
        ))
        policy_evidence.append(
            _guardrail_evidence(
                scope="trade",
                rule_code="position_concentration_pct",
                reason_code=reasons[-1],
                observed_value=max_position_concentration_pct_observed,
                limit_value=limits.max_position_concentration_pct,
            )
        )

    return tuple(reasons), tuple(policy_evidence)


def _guardrail_reason(*, rule_code: str, observed_value: float, limit_value: float) -> str:
    return (
        "guardrail_exceeded: "
        f"type={rule_code} observed={observed_value} limit={limit_value}"
    )


def _guardrail_evidence(
    *,
    scope: NonLiveScope,
    rule_code: str,
    reason_code: str,
    observed_value: float,
    limit_value: float,
) -> NonLiveEvaluationEvidence:
    return NonLiveEvaluationEvidence(
        decision="reject",
        semantic="boundary",
        scope=scope,
        rule_code=rule_code,
        reason_code=reason_code,
        observed_value=observed_value,
        limit_value=limit_value,
    )


def _concentration_ratio(absolute_notional: float, total_absolute_notional: float) -> float:
    if total_absolute_notional == 0.0:
        return 0.0
    return absolute_notional / total_absolute_notional
