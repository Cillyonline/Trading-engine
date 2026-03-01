"""Risk gate implementations and execution guardrails."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from risk.contracts import RiskDecision, RiskEvaluationRequest, RiskGate


class RiskApprovalMissingError(ValueError):
    """Raised when execution is attempted without an explicit risk approval."""


class RiskRejectedError(ValueError):
    """Raised when execution is attempted with a non-approved risk decision."""


@dataclass(frozen=True)
class ThresholdRiskGate(RiskGate):
    """Trivial concrete risk gate using a fixed notional threshold policy."""

    max_notional_usd: float
    rule_version: str = "threshold-v1"

    def evaluate(self, request: RiskEvaluationRequest) -> RiskDecision:
        score = float(request.notional_usd)
        decision = "APPROVED" if score <= self.max_notional_usd else "REJECTED"
        reason = (
            "notional within threshold"
            if decision == "APPROVED"
            else "notional exceeds threshold"
        )
        return RiskDecision(
            decision=decision,
            score=score,
            max_allowed=float(self.max_notional_usd),
            reason=reason,
            timestamp=datetime.now(tz=timezone.utc),
            rule_version=self.rule_version,
        )


def enforce_approved_risk_decision(risk_decision: RiskDecision | None) -> RiskDecision:
    """Require an explicit APPROVED risk decision before execution continues."""

    if risk_decision is None:
        raise RiskApprovalMissingError(
            "Execution requires explicit risk approval: risk_decision is missing"
        )

    if risk_decision.decision == "APPROVED":
        return risk_decision

    if risk_decision.decision == "REJECTED":
        raise RiskRejectedError(
            "Execution blocked by risk gate: risk_decision.decision=REJECTED"
        )

    raise ValueError(
        "Execution blocked by risk gate: risk_decision.decision must be APPROVED or REJECTED"
    )


__all__ = [
    "RiskApprovalMissingError",
    "RiskRejectedError",
    "ThresholdRiskGate",
    "enforce_approved_risk_decision",
]
