"""Deterministic allocation limits for risk evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class RiskLimits:
    """Immutable risk constraints for deterministic evaluation.

    Attributes:
        max_account_exposure_pct: Maximum account exposure percentage after a
            proposed position is applied.
        max_position_size: Maximum absolute position size allowed for one
            proposal.
        max_strategy_exposure_pct: Maximum strategy-level exposure percentage
            after applying the proposed position.
        max_symbol_exposure_pct: Maximum symbol-level exposure percentage after
            applying the proposed position.
        max_trade_risk_pct: Optional maximum stop-loss bounded loss percentage
            for one proposal.
        max_strategy_risk_pct: Optional maximum strategy-level stop-loss
            bounded loss percentage after applying the proposed position.
        max_symbol_risk_pct: Optional maximum symbol-level stop-loss bounded
            loss percentage after applying the proposed position.
        max_portfolio_risk_pct: Optional maximum portfolio-level stop-loss
            bounded loss percentage after applying the proposed position.
    """

    max_account_exposure_pct: float
    max_position_size: float
    max_strategy_exposure_pct: float
    max_symbol_exposure_pct: float
    max_trade_risk_pct: Optional[float] = None
    max_strategy_risk_pct: Optional[float] = None
    max_symbol_risk_pct: Optional[float] = None
    max_portfolio_risk_pct: Optional[float] = None
