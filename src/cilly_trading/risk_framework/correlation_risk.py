"""Correlation-based portfolio risk aggregation checks."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, sqrt
from typing import Mapping, Sequence

from cilly_trading.non_live_evaluation_contract import NonLiveEvaluationEvidence
from cilly_trading.risk_framework.allocation_rules import RiskLimits


PriceHistory = Mapping[str, Sequence[float]] | Sequence[tuple[str, Sequence[float]]]


@dataclass(frozen=True)
class CorrelationRiskCheck:
    """Deterministic correlation result for proposed/open symbol pairs."""

    policy_evidence: tuple[NonLiveEvaluationEvidence, ...]
    correlated_pair_count: int
    rejection_reason: str | None


def _rolling_window(values: Sequence[float], window: int) -> tuple[float, ...]:
    if window <= 0:
        return ()
    finite_values = tuple(float(value) for value in values if isfinite(float(value)))
    return finite_values[-window:]


def _pearson_correlation(left: Sequence[float], right: Sequence[float]) -> float | None:
    if len(left) != len(right) or len(left) < 2:
        return None

    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    left_deltas = tuple(value - left_mean for value in left)
    right_deltas = tuple(value - right_mean for value in right)
    numerator = sum(
        left_delta * right_delta
        for left_delta, right_delta in zip(left_deltas, right_deltas, strict=True)
    )
    left_variance = sum(value * value for value in left_deltas)
    right_variance = sum(value * value for value in right_deltas)
    denominator = sqrt(left_variance * right_variance)
    if denominator == 0.0:
        return None
    return numerator / denominator


def _pair_rule_code(proposed_symbol: str, open_symbol: str) -> str:
    return f"correlation_pair:{proposed_symbol}:{open_symbol}"


def _history_values(price_history: PriceHistory, symbol: str) -> Sequence[float]:
    if isinstance(price_history, Mapping):
        return price_history.get(symbol, ())
    for history_symbol, values in price_history:
        if history_symbol == symbol:
            return values
    return ()


def evaluate_correlation_risk(
    *,
    proposed_symbol: str,
    open_position_symbols: Sequence[str],
    price_history: PriceHistory,
    limits: RiskLimits,
) -> CorrelationRiskCheck:
    """Evaluate pairwise proposed/open symbol correlations."""

    if not limits.correlation_check_enabled:
        return CorrelationRiskCheck((), 0, None)

    proposed_window = _rolling_window(
        _history_values(price_history, proposed_symbol),
        limits.correlation_window,
    )
    correlated_evidence: list[NonLiveEvaluationEvidence] = []
    seen_symbols: set[str] = set()

    for open_symbol in open_position_symbols:
        if open_symbol == proposed_symbol or open_symbol in seen_symbols:
            continue
        seen_symbols.add(open_symbol)

        open_window = _rolling_window(
            _history_values(price_history, open_symbol),
            limits.correlation_window,
        )
        pair_size = min(len(proposed_window), len(open_window))
        correlation = _pearson_correlation(
            proposed_window[-pair_size:],
            open_window[-pair_size:],
        )
        if correlation is None or correlation <= limits.correlation_threshold:
            continue

        correlated_pair_number = len(correlated_evidence) + 1
        rejected = correlated_pair_number > limits.max_correlated_pairs
        correlated_evidence.append(
            NonLiveEvaluationEvidence(
                decision="reject" if rejected else "approve",
                semantic="cap",
                scope="portfolio",
                rule_code=_pair_rule_code(proposed_symbol, open_symbol),
                reason_code=(
                    "rejected: correlated_pair_limit_exceeded"
                    if rejected
                    else "approved: within_risk_limits"
                ),
                observed_value=correlation,
                limit_value=limits.correlation_threshold,
            )
        )

    correlated_pair_count = len(correlated_evidence)
    rejection_reason = (
        "rejected: correlated_pair_limit_exceeded"
        if correlated_pair_count > limits.max_correlated_pairs
        else None
    )
    return CorrelationRiskCheck(
        policy_evidence=tuple(correlated_evidence),
        correlated_pair_count=correlated_pair_count,
        rejection_reason=rejection_reason,
    )
