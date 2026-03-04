"""Portfolio state and drawdown calculation utilities."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PortfolioState:
    """Deterministic portfolio state for drawdown guards.

    Attributes:
        peak_equity: Highest observed portfolio equity in the active window.
        current_equity: Current portfolio equity.
    """

    peak_equity: float
    current_equity: float

    def drawdown(self) -> float:
        """Return current drawdown as a ratio in [0.0, 1.0]."""
        return calculate_drawdown(
            peak_equity=self.peak_equity,
            current_equity=self.current_equity,
        )


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
