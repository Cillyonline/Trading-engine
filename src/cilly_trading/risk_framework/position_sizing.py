"""ATR-based and percentage-based position sizing models.

The existing percentage-of-equity model remains the default.
AtrPositionSizer provides a volatility-adjusted alternative using the formula:

    position_size = (account_equity × risk_pct) / (atr_value × atr_multiplier)

This is the standard Turtle Trading position sizing approach.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AtrPositionSizer:
    """Volatility-adjusted position sizer using Average True Range.

    Attributes:
        atr_period: Lookback period for ATR calculation (default: 14).
        atr_multiplier: Multiplier applied to ATR as a risk unit (default: 2.0).
    """

    atr_period: int = 14
    atr_multiplier: float = 2.0

    def __post_init__(self) -> None:
        if self.atr_period < 1:
            raise ValueError(f"atr_period must be >= 1, got {self.atr_period}")
        if self.atr_multiplier <= 0.0:
            raise ValueError(f"atr_multiplier must be > 0, got {self.atr_multiplier}")

    def compute_position_size(
        self,
        *,
        account_equity: float,
        risk_pct: float,
        atr_value: float,
    ) -> float | None:
        """Compute position size given current account equity, risk fraction, and ATR.

        Returns None when the result is undefined (zero or negative denominator,
        non-positive equity, non-positive risk_pct, non-finite inputs).

        Args:
            account_equity: Current account equity in currency units.
            risk_pct: Fraction of equity to risk per trade (e.g. 0.01 = 1%).
            atr_value: Current ATR value in price units.

        Returns:
            Position size in units, or None if inputs are invalid.
        """
        import math

        if not math.isfinite(account_equity) or account_equity <= 0.0:
            return None
        if not math.isfinite(risk_pct) or risk_pct <= 0.0:
            return None
        if not math.isfinite(atr_value) or atr_value <= 0.0:
            return None

        denominator = atr_value * self.atr_multiplier
        if denominator <= 0.0:
            return None

        return (account_equity * risk_pct) / denominator
