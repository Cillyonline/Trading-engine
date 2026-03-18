"""Portfolio framework package for deterministic portfolio-state aggregation."""

from cilly_trading.portfolio_framework.capital_allocation_policy import (
    CapitalAllocationAssessment,
    CapitalAllocationRules,
    StrategyAllocationAssessment,
    StrategyAllocationRule,
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
    "CapitalAllocationAssessment",
    "CapitalAllocationRules",
    "StrategyAllocationAssessment",
    "StrategyAllocationRule",
    "PortfolioExposureSummary",
    "PortfolioPosition",
    "PortfolioState",
    "PositionExposure",
    "StrategyExposure",
    "SymbolExposure",
    "aggregate_portfolio_exposure",
    "assess_capital_allocation",
]
