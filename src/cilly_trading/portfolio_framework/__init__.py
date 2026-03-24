"""Portfolio framework package for deterministic portfolio-state aggregation."""

from cilly_trading.portfolio_framework.capital_allocation_policy import (
    BoundedPositionSizingHook,
    CapitalAllocationAssessment,
    CapitalAllocationRules,
    PortfolioDecisionIntent,
    PortfolioDecisionRecord,
    PortfolioDecisionResult,
    PrioritizedAllocationConfig,
    PrioritizedAllocationDecision,
    PrioritizedAllocationResult,
    PrioritizedAllocationSignal,
    StrategyAllocationAssessment,
    StrategyAllocationRule,
    allocate_prioritized_signals,
    assess_capital_allocation,
    run_portfolio_decision_pipeline,
)
from cilly_trading.portfolio_framework.contract import PortfolioPosition, PortfolioState
from cilly_trading.portfolio_framework.exposure_aggregator import (
    PortfolioExposureSummary,
    PositionExposure,
    StrategyExposure,
    SymbolExposure,
    aggregate_portfolio_exposure,
)
from cilly_trading.portfolio_framework.guardrails import (
    PortfolioGuardrailAssessment,
    PortfolioGuardrailLimits,
    assess_portfolio_guardrails,
)
__all__ = [
    "BoundedPositionSizingHook",
    "CapitalAllocationAssessment",
    "CapitalAllocationRules",
    "PortfolioDecisionIntent",
    "PortfolioDecisionRecord",
    "PortfolioDecisionResult",
    "PortfolioGuardrailAssessment",
    "PortfolioGuardrailLimits",
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
    "assess_portfolio_guardrails",
    "aggregate_portfolio_exposure",
    "allocate_prioritized_signals",
    "assess_capital_allocation",
    "run_portfolio_decision_pipeline",
]
