"""Canonical non-live evaluation evidence contract.

This contract is shared by deterministic risk and portfolio policy evaluators
to make reject/cap/boundary semantics explicit and reviewable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence


NonLiveDecision = Literal["approve", "reject"]
NonLiveSemantic = Literal["cap", "boundary"]
NonLiveScope = Literal["trade", "symbol", "strategy", "portfolio", "runtime"]

CanonicalRiskRejectionReasonCode = Literal[
    "rejected:risk_framework_kill_switch_enabled",
    "rejected:risk_framework_max_position_size_exceeded",
    "rejected:risk_framework_max_account_exposure_pct_exceeded",
    "rejected:risk_framework_max_strategy_exposure_pct_exceeded",
    "rejected:risk_framework_max_symbol_exposure_pct_exceeded",
]

CANONICAL_RISK_REJECTION_REASON_CODES: tuple[CanonicalRiskRejectionReasonCode, ...] = (
    "rejected:risk_framework_kill_switch_enabled",
    "rejected:risk_framework_max_position_size_exceeded",
    "rejected:risk_framework_max_account_exposure_pct_exceeded",
    "rejected:risk_framework_max_strategy_exposure_pct_exceeded",
    "rejected:risk_framework_max_symbol_exposure_pct_exceeded",
)

RISK_REJECTION_REASON_PRECEDENCE: dict[CanonicalRiskRejectionReasonCode, int] = {
    reason_code: index
    for index, reason_code in enumerate(CANONICAL_RISK_REJECTION_REASON_CODES)
}

RISK_FRAMEWORK_REASON_TO_CANONICAL_REJECTION_REASON: dict[
    str, CanonicalRiskRejectionReasonCode
] = {
    "rejected: kill_switch_enabled": "rejected:risk_framework_kill_switch_enabled",
    "rejected: max_position_size_exceeded": "rejected:risk_framework_max_position_size_exceeded",
    "rejected: max_account_exposure_pct_exceeded": (
        "rejected:risk_framework_max_account_exposure_pct_exceeded"
    ),
    "rejected: max_strategy_exposure_pct_exceeded": (
        "rejected:risk_framework_max_strategy_exposure_pct_exceeded"
    ),
    "rejected: max_symbol_exposure_pct_exceeded": (
        "rejected:risk_framework_max_symbol_exposure_pct_exceeded"
    ),
}


@dataclass(frozen=True)
class NonLiveEvaluationEvidence:
    """Structured deterministic evidence for one policy decision edge."""

    decision: NonLiveDecision
    semantic: NonLiveSemantic
    scope: NonLiveScope
    rule_code: str
    reason_code: str
    observed_value: float
    limit_value: float


def normalize_risk_rejection_reason_code(reason_code: str) -> CanonicalRiskRejectionReasonCode:
    """Normalize risk rejection reason-code variants to canonical contract codes."""

    from_framework = RISK_FRAMEWORK_REASON_TO_CANONICAL_REJECTION_REASON.get(reason_code)
    if from_framework is not None:
        return from_framework
    if reason_code in RISK_REJECTION_REASON_PRECEDENCE:
        return reason_code  # type: ignore[return-value]
    raise ValueError(f"unsupported risk rejection reason code: {reason_code}")


def resolve_risk_rejection_reason_precedence(
    reason_codes: Sequence[str],
) -> CanonicalRiskRejectionReasonCode:
    """Resolve deterministic canonical rejection reason by contract precedence."""

    if not reason_codes:
        raise ValueError("at least one risk rejection reason code is required")
    normalized = {normalize_risk_rejection_reason_code(code) for code in reason_codes}
    ordered = sorted(
        normalized,
        key=lambda code: RISK_REJECTION_REASON_PRECEDENCE[code],
    )
    return ordered[0]


__all__ = [
    "CANONICAL_RISK_REJECTION_REASON_CODES",
    "CanonicalRiskRejectionReasonCode",
    "NonLiveDecision",
    "NonLiveEvaluationEvidence",
    "NonLiveScope",
    "NonLiveSemantic",
    "RISK_FRAMEWORK_REASON_TO_CANONICAL_REJECTION_REASON",
    "RISK_REJECTION_REASON_PRECEDENCE",
    "normalize_risk_rejection_reason_code",
    "resolve_risk_rejection_reason_precedence",
]
