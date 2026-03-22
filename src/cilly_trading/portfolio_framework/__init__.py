"""Portfolio framework package for deterministic portfolio-state aggregation."""

from cilly_trading.portfolio_framework.capital_allocation_policy import (
    BoundedPositionSizingHook,
    CapitalAllocationAssessment,
    CapitalAllocationRules,
    PrioritizedAllocationConfig,
    PrioritizedAllocationDecision,
    PrioritizedAllocationResult,
    PrioritizedAllocationSignal,
    StrategyAllocationAssessment,
    StrategyAllocationRule,
    allocate_prioritized_signals,
    assess_capital_allocation,
)
from cilly_trading.portfolio_framework.contract import PortfolioPosition, PortfolioState
from cilly_trading.portfolio_framework.exposure_aggregator import (
    PortfolioExposureSummary,
    PositionExposure,
    StrategyExposure,
    SymbolExposure,
    aggregate_portfolio_exposure,
)
__all__ = [
    "BoundedPositionSizingHook",
    "CapitalAllocationAssessment",
    "CapitalAllocationRules",
    "PrioritizedAllocationConfig",
    "PrioritizedAllocationDecision",
    "PrioritizedAllocationResult",
    "PrioritizedAllocationSignal",
    "StrategyAllocationAssessment",
    "StrategyAllocationRule",
    "PortfolioExposureSummary",
    "PortfolioPosition",
    "PortfolioState",
    "PositionExposure",
    "StrategyExposure",
    "SymbolExposure",
    "aggregate_portfolio_exposure",
    "allocate_prioritized_signals",
    "assess_capital_allocation",
]
