"""Contracts for mandatory risk-gate evaluation.

This module defines only interfaces and data models. It must not contain runtime
wiring or side-effecting behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol


DecisionType = Literal["APPROVED", "REJECTED"]


@dataclass(frozen=True)
class RiskEvaluationRequest:
    """Input contract for risk evaluation.

    Attributes:
        request_id: Stable identifier for the candidate execution request.
        strategy_id: Strategy identifier associated with the request.
        symbol: Instrument identifier associated with the request.
        notional_usd: Requested notional exposure in USD.
        metadata: Opaque structured metadata for risk policies.
    """

    request_id: str
    strategy_id: str
    symbol: str
    notional_usd: float
    metadata: dict[str, str]


@dataclass(frozen=True)
class RiskDecision:
    """Explicit result contract returned by the mandatory risk gate.

    Attributes:
        decision: Mandatory explicit decision, either APPROVED or REJECTED.
        score: Computed exposure score for the request.
        max_allowed: Maximum score permitted by active policy.
        reason: Human-readable explanation for the decision.
        timestamp: timezone-aware UTC datetime of evaluation.
        rule_version: Version identifier of the risk policy/ruleset used.
    """

    decision: DecisionType
    score: float
    max_allowed: float
    reason: str
    timestamp: datetime
    rule_version: str


class RiskGate(Protocol):
    """Mandatory pre-execution risk gate contract.

    Implementations must be pure evaluators for the supplied request and return a
    `RiskDecision` without producing side effects.
    """

    def evaluate(self, request: RiskEvaluationRequest) -> RiskDecision:
        """Evaluate a request against risk policy and return an explicit decision.

        Args:
            request: Candidate request to be scored by risk rules.

        Returns:
            RiskDecision: Explicit APPROVED or REJECTED contract result.
        """
        ...
