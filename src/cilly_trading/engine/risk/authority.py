"""Canonical bounded risk-framework authority surface.

This module is the single canonical authority handle for the currently
implemented bounded risk-framework primitives. It is bounded non-live
technical evidence only and is not live-trading, broker, trader-validation,
or operational-readiness evidence.

The canonical bounded risk-framework authority contract is documented at:

- ``docs/architecture/risk/bounded_risk_framework_authority_contract.md``

This module re-exports the existing canonical bounded surfaces so consumers
reference one canonical handle. It does not redefine bounded risk semantics
and adds no new risk model, threshold, or execution-policy behavior.
"""

from __future__ import annotations

from typing import Final

from cilly_trading.non_live_evaluation_contract import (
    CANONICAL_RISK_REJECTION_REASON_CODES,
    RISK_REJECTION_REASON_PRECEDENCE,
)

from .gate import (
    GUARD_TRIGGER_TYPES,
    RISK_FRAMEWORK_REASON_CODES,
)

#: Canonical bounded risk-framework authority identifier.
#:
#: Stable string handle for the bounded non-live risk-framework authority
#: contract. It is used as a deterministic identifier only and does not
#: imply live-trading, broker, trader-validation, or operational-readiness
#: status.
BOUNDED_RISK_FRAMEWORK_AUTHORITY_ID: Final[str] = "risk_framework_bounded_non_live_v1"

#: Canonical reason code for approved bounded risk-framework outcomes.
APPROVED_RISK_FRAMEWORK_REASON_CODE: Final[str] = "approved:risk_framework_within_limits"

#: Path (relative to repo root) of the canonical bounded authority contract
#: documentation. Exposed as a constant so runtime/test surfaces can
#: deterministically reference the canonical doc location.
BOUNDED_RISK_FRAMEWORK_AUTHORITY_CONTRACT_DOC: Final[str] = (
    "docs/architecture/risk/bounded_risk_framework_authority_contract.md"
)


__all__ = [
    "APPROVED_RISK_FRAMEWORK_REASON_CODE",
    "BOUNDED_RISK_FRAMEWORK_AUTHORITY_CONTRACT_DOC",
    "BOUNDED_RISK_FRAMEWORK_AUTHORITY_ID",
    "CANONICAL_RISK_REJECTION_REASON_CODES",
    "GUARD_TRIGGER_TYPES",
    "RISK_FRAMEWORK_REASON_CODES",
    "RISK_REJECTION_REASON_PRECEDENCE",
]
