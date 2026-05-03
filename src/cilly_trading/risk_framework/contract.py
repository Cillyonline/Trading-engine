"""Risk evaluation contract definitions for Issue #482.

This module contains immutable data contracts and an optional protocol surface
for risk evaluation. It contains no business logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional, Protocol, Sequence

from cilly_trading.non_live_evaluation_contract import NonLiveEvaluationEvidence


@dataclass(frozen=True)
class RiskEvaluationRequest:
    """Input contract for risk evaluation.

    Attributes:
        strategy_id: Identifier of the strategy under evaluation.
        symbol: Instrument symbol for the proposed position.
        proposed_position_size: Requested position size before risk adjustment.
        account_equity: Current account equity used by downstream evaluators.
        current_exposure: Current account exposure before this proposal.
        entry_price: Optional proposed entry price for bounded stop-loss risk.
        stop_loss_price: Optional proposed stop-loss price for bounded max-risk
            evidence.
        strategy_risk_used: Current strategy-level bounded risk before this
            proposal.
        symbol_risk_used: Current symbol-level bounded risk before this
            proposal.
        portfolio_risk_used: Current portfolio-level bounded risk before this
            proposal.
        require_bounded_risk_evidence: Require stop-loss and bounded risk-budget
            evidence to fail closed when missing or contradictory.
        open_position_symbols: Symbols with currently open positions available
            to this evaluation.
        price_history: In-scope price history keyed by symbol for deterministic
            correlation checks; normalized to immutable tuples.
    """

    strategy_id: str
    symbol: str
    proposed_position_size: float
    account_equity: float
    current_exposure: float
    entry_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    strategy_risk_used: float = 0.0
    symbol_risk_used: float = 0.0
    portfolio_risk_used: float = 0.0
    require_bounded_risk_evidence: bool = False
    open_position_symbols: Sequence[str] = ()
    price_history: (
        Mapping[str, Sequence[float]] | Sequence[tuple[str, Sequence[float]]]
    ) = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "open_position_symbols", tuple(self.open_position_symbols))
        price_history = self.price_history
        if isinstance(price_history, Mapping):
            normalized_price_history = tuple(
                (symbol, tuple(values))
                for symbol, values in sorted(price_history.items())
            )
        else:
            normalized_price_history = tuple(
                (symbol, tuple(values))
                for symbol, values in sorted(price_history)
            )
        object.__setattr__(self, "price_history", normalized_price_history)


@dataclass(frozen=True)
class RiskEvaluationResponse:
    """Output contract for risk evaluation.

    Attributes:
        approved: Whether the proposed risk request is approved.
        reason: Human-readable explanation of the evaluation outcome.
        adjusted_position_size: Optional adjusted position size.
        risk_score: Numeric risk score produced by an implementation.
        policy_evidence: Deterministic bounded non-live evidence rows.
    """

    approved: bool
    reason: str
    adjusted_position_size: Optional[float]
    risk_score: float
    policy_evidence: tuple[NonLiveEvaluationEvidence, ...] = ()


class RiskEvaluator(Protocol):
    """Protocol for deterministic risk evaluators."""

    def evaluate(self, request: RiskEvaluationRequest) -> RiskEvaluationResponse:
        """Evaluate a request and return an immutable response contract."""
        ...
