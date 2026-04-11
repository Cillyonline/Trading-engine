"""Canonical bounded paper execution risk profile contract (P57-RISK).

This contract is the single authoritative input surface for bounded paper
execution risk behavior. Every bounded paper execution path must source risk
parameters from this profile.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from math import isfinite
from typing import Any


PAPER_EXECUTION_RISK_PROFILE_CONTRACT_ID = "paper-execution-risk-profile-v1"


def _require_finite_pct(*, name: str, value: Decimal, allow_zero: bool = False) -> None:
    if not value.is_finite():
        raise ValueError(f"{name} must be finite")
    if allow_zero:
        if value < Decimal("0") or value > Decimal("1"):
            raise ValueError(f"{name} must be in range [0, 1]")
        return
    if value <= Decimal("0") or value > Decimal("1"):
        raise ValueError(f"{name} must be in range (0, 1]")


def _require_finite_positive_decimal(*, name: str, value: Decimal) -> None:
    if not value.is_finite():
        raise ValueError(f"{name} must be finite")
    if value <= Decimal("0"):
        raise ValueError(f"{name} must be > 0")


def _require_finite_score(*, name: str, value: float) -> None:
    if not isfinite(value):
        raise ValueError(f"{name} must be finite")
    if value < 0.0 or value > 100.0:
        raise ValueError(f"{name} must be in range [0.0, 100.0]")


@dataclass(frozen=True)
class PaperExecutionRiskProfile:
    """Validated bounded risk profile for paper execution."""

    contract_id: str = PAPER_EXECUTION_RISK_PROFILE_CONTRACT_ID
    min_score_threshold: float = 60.0
    max_position_pct: Decimal = Decimal("0.10")
    max_total_exposure_pct: Decimal = Decimal("0.80")
    max_strategy_exposure_pct: Decimal = Decimal("0.80")
    max_symbol_exposure_pct: Decimal = Decimal("0.80")
    max_concurrent_positions: int = 10
    cooldown_hours: int = 24
    account_equity: Decimal = Decimal("100000")
    default_paper_quantity: Decimal = Decimal("1")
    default_paper_entry_price: Decimal = Decimal("100")

    def __post_init__(self) -> None:
        if self.contract_id != PAPER_EXECUTION_RISK_PROFILE_CONTRACT_ID:
            raise ValueError(
                "unsupported paper execution risk profile contract_id: "
                f"{self.contract_id!r}"
            )
        _require_finite_score(
            name="min_score_threshold",
            value=self.min_score_threshold,
        )
        _require_finite_pct(name="max_position_pct", value=self.max_position_pct)
        _require_finite_pct(
            name="max_total_exposure_pct",
            value=self.max_total_exposure_pct,
        )
        _require_finite_pct(
            name="max_strategy_exposure_pct",
            value=self.max_strategy_exposure_pct,
        )
        _require_finite_pct(
            name="max_symbol_exposure_pct",
            value=self.max_symbol_exposure_pct,
        )
        if self.max_concurrent_positions <= 0:
            raise ValueError("max_concurrent_positions must be > 0")
        if self.cooldown_hours < 0:
            raise ValueError("cooldown_hours must be >= 0")
        _require_finite_positive_decimal(
            name="account_equity",
            value=self.account_equity,
        )
        _require_finite_positive_decimal(
            name="default_paper_quantity",
            value=self.default_paper_quantity,
        )
        _require_finite_positive_decimal(
            name="default_paper_entry_price",
            value=self.default_paper_entry_price,
        )

    def to_payload(self) -> dict[str, Any]:
        """Return a deterministic JSON-safe payload for evidence/logging."""
        return {
            "contract_id": self.contract_id,
            "min_score_threshold": self.min_score_threshold,
            "max_position_pct": str(self.max_position_pct),
            "max_total_exposure_pct": str(self.max_total_exposure_pct),
            "max_strategy_exposure_pct": str(self.max_strategy_exposure_pct),
            "max_symbol_exposure_pct": str(self.max_symbol_exposure_pct),
            "max_concurrent_positions": self.max_concurrent_positions,
            "cooldown_hours": self.cooldown_hours,
            "account_equity": str(self.account_equity),
            "default_paper_quantity": str(self.default_paper_quantity),
            "default_paper_entry_price": str(self.default_paper_entry_price),
        }


DEFAULT_PAPER_EXECUTION_RISK_PROFILE = PaperExecutionRiskProfile()


__all__ = [
    "DEFAULT_PAPER_EXECUTION_RISK_PROFILE",
    "PAPER_EXECUTION_RISK_PROFILE_CONTRACT_ID",
    "PaperExecutionRiskProfile",
]
