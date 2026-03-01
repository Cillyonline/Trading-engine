"""Risk evaluation contract definitions for Issue #482.

This module contains immutable data contracts and an optional protocol surface
for risk evaluation. It contains no business logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol


@dataclass(frozen=True)
class RiskEvaluationRequest:
    """Input contract for risk evaluation.

    Attributes:
        strategy_id: Identifier of the strategy under evaluation.
        symbol: Instrument symbol for the proposed position.
        proposed_position_size: Requested position size before risk adjustment.
        account_equity: Current account equity used by downstream evaluators.
        current_exposure: Current account exposure before this proposal.
    """

    strategy_id: str
    symbol: str
    proposed_position_size: float
    account_equity: float
    current_exposure: float


@dataclass(frozen=True)
class RiskEvaluationResponse:
    """Output contract for risk evaluation.

    Attributes:
        approved: Whether the proposed risk request is approved.
        reason: Human-readable explanation of the evaluation outcome.
        adjusted_position_size: Optional adjusted position size.
        risk_score: Numeric risk score produced by an implementation.
    """

    approved: bool
    reason: str
    adjusted_position_size: Optional[float]
    risk_score: float


class RiskEvaluator(Protocol):
    """Protocol for deterministic risk evaluators."""

    def evaluate(self, request: RiskEvaluationRequest) -> RiskEvaluationResponse:
        """Evaluate a request and return an immutable response contract."""
        ...
