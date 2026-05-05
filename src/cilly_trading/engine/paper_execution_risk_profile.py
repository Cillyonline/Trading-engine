"""Canonical bounded paper execution risk profile contract (P57-RISK).

This contract is the single authoritative input surface for bounded paper
execution risk behavior. Every bounded paper execution path must source risk
parameters from this profile.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from math import isfinite
from typing import Any, Literal


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


def _require_finite_non_negative_pct(*, name: str, value: Decimal) -> None:
    if not value.is_finite():
        raise ValueError(f"{name} must be finite")
    if value < Decimal("0") or value > Decimal("1"):
        raise ValueError(f"{name} must be in range [0, 1]")


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


SizingMethod = Literal["stop_distance", "atr", "fixed"]


@dataclass(frozen=True)
class PaperExecutionRiskProfile:
    """Validated bounded risk profile for paper execution."""

    contract_id: str = PAPER_EXECUTION_RISK_PROFILE_CONTRACT_ID
    min_score_threshold: float = 60.0
    max_position_pct: Decimal = Decimal("0.10")
    max_risk_per_trade_pct: Decimal = Decimal("0.01")
    min_trade_risk_pct: Decimal = Decimal("0.005")
    max_trade_risk_pct: Decimal = Decimal("0.20")
    notional_rounding_quantum: Decimal = Decimal("0.01")
    max_total_exposure_pct: Decimal = Decimal("0.80")
    max_strategy_exposure_pct: Decimal = Decimal("0.80")
    max_symbol_exposure_pct: Decimal = Decimal("0.80")
    max_concurrent_positions: int = 10
    cooldown_hours: int = 24
    account_equity: Decimal = Decimal("100000")
    default_paper_quantity: Decimal = Decimal("1")
    default_paper_entry_price: Decimal = Decimal("100")
    commission_rate: Decimal = Decimal("0.001")
    slippage_rate: Decimal = Decimal("0.0005")
    # #1147 — ATR-based position sizing
    sizing_method: SizingMethod = "stop_distance"
    atr_multiple: Decimal = Decimal("2.0")
    # #1145 — correlation risk gate (requires price_history passed to process_signal)
    correlation_check_enabled: bool = False
    correlation_threshold: float = 0.7
    max_correlated_pairs: int = 2
    correlation_window: int = 60
    # #1146 — drawdown guard (circuit-breaker for losing streaks)
    drawdown_guard_enabled: bool = False
    max_consecutive_losses: int = 3
    max_drawdown_pct: Decimal = Decimal("0.10")
    # #1151 — regime filter (empty frozenset = allow all regimes)
    allowed_regimes: frozenset[str] = field(default_factory=frozenset)

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
            name="max_risk_per_trade_pct",
            value=self.max_risk_per_trade_pct,
        )
        _require_finite_pct(
            name="min_trade_risk_pct",
            value=self.min_trade_risk_pct,
        )
        _require_finite_pct(
            name="max_trade_risk_pct",
            value=self.max_trade_risk_pct,
        )
        if self.min_trade_risk_pct > self.max_trade_risk_pct:
            raise ValueError("min_trade_risk_pct must be <= max_trade_risk_pct")
        _require_finite_positive_decimal(
            name="notional_rounding_quantum",
            value=self.notional_rounding_quantum,
        )
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
        _require_finite_non_negative_pct(
            name="commission_rate",
            value=self.commission_rate,
        )
        _require_finite_non_negative_pct(
            name="slippage_rate",
            value=self.slippage_rate,
        )
        if self.sizing_method not in ("stop_distance", "atr", "fixed"):
            raise ValueError(
                f"sizing_method must be 'stop_distance', 'atr', or 'fixed', got {self.sizing_method!r}"
            )
        _require_finite_positive_decimal(name="atr_multiple", value=self.atr_multiple)
        if not isfinite(self.correlation_threshold):
            raise ValueError("correlation_threshold must be finite")
        if not (0.0 <= self.correlation_threshold <= 1.0):
            raise ValueError("correlation_threshold must be in range [0.0, 1.0]")
        if self.max_correlated_pairs < 0:
            raise ValueError("max_correlated_pairs must be >= 0")
        if self.correlation_window <= 0:
            raise ValueError("correlation_window must be > 0")
        if self.max_consecutive_losses <= 0:
            raise ValueError("max_consecutive_losses must be > 0")
        _require_finite_pct(name="max_drawdown_pct", value=self.max_drawdown_pct)
        from cilly_trading.engine.regime_classifier import _ALL_REGIME_LABELS
        unknown = self.allowed_regimes - _ALL_REGIME_LABELS
        if unknown:
            raise ValueError(f"unknown regime labels in allowed_regimes: {sorted(unknown)}")

    def to_payload(self) -> dict[str, Any]:
        """Return a deterministic JSON-safe payload for evidence/logging."""
        return {
            "contract_id": self.contract_id,
            "min_score_threshold": self.min_score_threshold,
            "max_position_pct": str(self.max_position_pct),
            "max_risk_per_trade_pct": str(self.max_risk_per_trade_pct),
            "min_trade_risk_pct": str(self.min_trade_risk_pct),
            "max_trade_risk_pct": str(self.max_trade_risk_pct),
            "notional_rounding_quantum": str(self.notional_rounding_quantum),
            "max_total_exposure_pct": str(self.max_total_exposure_pct),
            "max_strategy_exposure_pct": str(self.max_strategy_exposure_pct),
            "max_symbol_exposure_pct": str(self.max_symbol_exposure_pct),
            "max_concurrent_positions": self.max_concurrent_positions,
            "cooldown_hours": self.cooldown_hours,
            "account_equity": str(self.account_equity),
            "default_paper_quantity": str(self.default_paper_quantity),
            "default_paper_entry_price": str(self.default_paper_entry_price),
            "commission_rate": str(self.commission_rate),
            "slippage_rate": str(self.slippage_rate),
            "sizing_method": self.sizing_method,
            "atr_multiple": str(self.atr_multiple),
            "correlation_check_enabled": self.correlation_check_enabled,
            "correlation_threshold": self.correlation_threshold,
            "max_correlated_pairs": self.max_correlated_pairs,
            "correlation_window": self.correlation_window,
            "drawdown_guard_enabled": self.drawdown_guard_enabled,
            "max_consecutive_losses": self.max_consecutive_losses,
            "max_drawdown_pct": str(self.max_drawdown_pct),
            "allowed_regimes": sorted(self.allowed_regimes),
        }


DEFAULT_PAPER_EXECUTION_RISK_PROFILE = PaperExecutionRiskProfile()


__all__ = [
    "DEFAULT_PAPER_EXECUTION_RISK_PROFILE",
    "PAPER_EXECUTION_RISK_PROFILE_CONTRACT_ID",
    "PaperExecutionRiskProfile",
    "SizingMethod",
    "RegimeLabel",
]
