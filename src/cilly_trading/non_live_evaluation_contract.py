"""Canonical non-live evaluation evidence contract.

This contract is shared by deterministic risk and portfolio policy evaluators
to make reject/cap/boundary semantics explicit and reviewable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


NonLiveDecision = Literal["approve", "reject"]
NonLiveSemantic = Literal["cap", "boundary"]
NonLiveScope = Literal["trade", "symbol", "strategy", "portfolio", "runtime"]


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

