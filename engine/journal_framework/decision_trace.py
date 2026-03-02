"""Deterministic decision trace primitives and generation logic."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from types import MappingProxyType
from typing import Any, Mapping

from engine.portfolio_framework.capital_allocation_policy import CapitalAllocationAssessment
from engine.portfolio_framework.exposure_aggregator import PortfolioExposureSummary



def _deep_freeze(value: Any) -> Any:
    """Create an immutable representation for nested containers.

    Args:
        value: Arbitrary JSON-compatible or container value.

    Returns:
        Immutable representation of input value.
    """

    if isinstance(value, Mapping):
        frozen = {key: _deep_freeze(value[key]) for key in sorted(value)}
        return MappingProxyType(frozen)
    if isinstance(value, list):
        return tuple(_deep_freeze(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_deep_freeze(item) for item in value)
    return value


@dataclass(frozen=True)
class DecisionTrace:
    """Immutable deterministic trace of a portfolio decision."""

    trace_id: str
    exposure: PortfolioExposureSummary
    allocation: CapitalAllocationAssessment
    decision_context: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "decision_context", _deep_freeze(self.decision_context))



def _canonicalize(value: Any) -> Any:
    """Convert nested structures into deterministically serializable values.

    Args:
        value: Arbitrary JSON-compatible or container value.

    Returns:
        Canonical representation with sorted mapping keys.
    """

    if isinstance(value, Mapping):
        return {key: _canonicalize(value[key]) for key in sorted(value)}
    if isinstance(value, tuple):
        return [_canonicalize(item) for item in value]
    if isinstance(value, list):
        return [_canonicalize(item) for item in value]
    return value



def _exposure_payload(exposure: PortfolioExposureSummary) -> dict[str, Any]:
    return {
        "total_absolute_notional": exposure.total_absolute_notional,
        "net_notional": exposure.net_notional,
        "gross_exposure_pct": exposure.gross_exposure_pct,
        "net_exposure_pct": exposure.net_exposure_pct,
        "strategy_exposures": [
            {
                "strategy_id": row.strategy_id,
                "total_absolute_notional": row.total_absolute_notional,
                "net_notional": row.net_notional,
                "gross_exposure_pct": row.gross_exposure_pct,
                "net_exposure_pct": row.net_exposure_pct,
            }
            for row in sorted(exposure.strategy_exposures, key=lambda item: item.strategy_id)
        ],
        "symbol_exposures": [
            {
                "symbol": row.symbol,
                "total_absolute_notional": row.total_absolute_notional,
                "net_notional": row.net_notional,
                "gross_exposure_pct": row.gross_exposure_pct,
                "net_exposure_pct": row.net_exposure_pct,
            }
            for row in sorted(exposure.symbol_exposures, key=lambda item: item.symbol)
        ],
    }



def _allocation_payload(allocation: CapitalAllocationAssessment) -> dict[str, Any]:
    return {
        "approved": allocation.approved,
        "reasons": list(allocation.reasons),
        "total_absolute_notional": allocation.total_absolute_notional,
        "global_cap_notional": allocation.global_cap_notional,
        "global_within_cap": allocation.global_within_cap,
        "strategy_assessments": [
            {
                "strategy_id": row.strategy_id,
                "allocation_score": row.allocation_score,
                "deterministic_score_weight": row.deterministic_score_weight,
                "current_absolute_notional": row.current_absolute_notional,
                "capital_cap_notional": row.capital_cap_notional,
                "score_weighted_notional": row.score_weighted_notional,
                "effective_allowed_notional": row.effective_allowed_notional,
                "within_cap": row.within_cap,
            }
            for row in sorted(allocation.strategy_assessments, key=lambda item: item.strategy_id)
        ],
    }



def generate_decision_trace(
    *,
    exposure: PortfolioExposureSummary,
    allocation: CapitalAllocationAssessment,
    decision_context: Mapping[str, Any] | None = None,
) -> DecisionTrace:
    """Create a deterministic, side-effect free decision trace."""

    context_payload: Mapping[str, Any] = _deep_freeze(decision_context or {})
    payload = {
        "exposure": _exposure_payload(exposure),
        "allocation": _allocation_payload(allocation),
        "decision_context": _canonicalize(context_payload),
    }
    serialized = json.dumps(payload, separators=(",", ":"), sort_keys=True, ensure_ascii=True)
    trace_id = sha256(serialized.encode("utf-8")).hexdigest()
    return DecisionTrace(
        trace_id=trace_id,
        exposure=exposure,
        allocation=allocation,
        decision_context=context_payload,
    )
