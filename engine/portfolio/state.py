"""Portfolio state, drawdown and daily PnL calculation utilities."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PortfolioState:
    """Deterministic portfolio state for drawdown guards.

    Attributes:
        peak_equity: Highest observed portfolio equity in the active window.
        current_equity: Current portfolio equity.
        start_of_day_equity: Equity snapshot at start of trading day.
    """

    peak_equity: float
    current_equity: float
    start_of_day_equity: float | None = None

    def drawdown(self) -> float:
        """Return current drawdown as a ratio in [0.0, 1.0]."""
        return calculate_drawdown(
            peak_equity=self.peak_equity,
            current_equity=self.current_equity,
        )

    def daily_pnl(self) -> float:
        """Return daily PnL based on start-of-day and current equity."""
        if self.start_of_day_equity is None:
            return 0.0

        return calculate_daily_pnl(
            start_of_day_equity=self.start_of_day_equity,
            current_equity=self.current_equity,
        )

    def daily_loss(self) -> float:
        """Return non-negative realized daily loss amount."""
        pnl = self.daily_pnl()
        if pnl >= 0.0:
            return 0.0

        return -pnl


def calculate_drawdown(*, peak_equity: float, current_equity: float) -> float:
    """Calculate drawdown ratio from peak and current equity.

    Returns:
        float: Zero for non-positive peaks, otherwise
        ``max(0.0, (peak_equity - current_equity) / peak_equity)``.
    """

    if peak_equity <= 0.0:
        return 0.0

    raw_drawdown = (peak_equity - current_equity) / peak_equity
    if raw_drawdown <= 0.0:
        return 0.0

    return raw_drawdown


def calculate_daily_pnl(*, start_of_day_equity: float, current_equity: float) -> float:
    """Calculate daily PnL from start-of-day and current equity."""
    return current_equity - start_of_day_equity
