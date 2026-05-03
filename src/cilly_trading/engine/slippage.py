"""Stochastic slippage model for backtest execution."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Literal

import numpy as np

STOCHASTIC_SLIPPAGE_STRESS_MEAN_BPS: int = 50
STOCHASTIC_SLIPPAGE_STRESS_STD_BPS: int = 30
STOCHASTIC_SLIPPAGE_STRESS_MAX_BPS: int = 150


def build_stochastic_stress_preset(*, seed: int | None = None) -> "StochasticSlippageModel":
    """Return the canonical bounded stress-test slippage preset."""
    return StochasticSlippageModel(
        distribution="normal",
        mean_bps=float(STOCHASTIC_SLIPPAGE_STRESS_MEAN_BPS),
        std_bps=float(STOCHASTIC_SLIPPAGE_STRESS_STD_BPS),
        max_bps=float(STOCHASTIC_SLIPPAGE_STRESS_MAX_BPS),
        seed=seed,
    )


@dataclass
class StochasticSlippageModel:
    """Stochastic slippage model with configurable distribution.

    Samples basis-point slippage from the configured distribution.
    Output is floored at 0 and hard-capped at max_bps.
    When seed is set the draw sequence is fully reproducible.
    """

    distribution: Literal["normal", "uniform", "lognormal"] = "normal"
    mean_bps: float = 10.0
    std_bps: float = 5.0
    max_bps: float = 50.0
    seed: int | None = None

    def __post_init__(self) -> None:
        if self.distribution not in {"normal", "uniform", "lognormal"}:
            raise ValueError(
                f"StochasticSlippageModel distribution must be one of "
                f"'normal', 'uniform', 'lognormal'; got: {self.distribution!r}"
            )
        if not isinstance(self.mean_bps, (int, float)) or not math.isfinite(self.mean_bps) or self.mean_bps < 0:
            raise ValueError("StochasticSlippageModel mean_bps must be a finite non-negative number")
        if not isinstance(self.std_bps, (int, float)) or not math.isfinite(self.std_bps) or self.std_bps < 0:
            raise ValueError("StochasticSlippageModel std_bps must be a finite non-negative number")
        if not isinstance(self.max_bps, (int, float)) or not math.isfinite(self.max_bps) or self.max_bps < 0:
            raise ValueError("StochasticSlippageModel max_bps must be a finite non-negative number")
        if self.seed is not None and (not isinstance(self.seed, int) or self.seed < 0):
            raise ValueError("StochasticSlippageModel seed must be a non-negative integer or None")

        self._rng = np.random.default_rng(self.seed)

    def sample_slippage_bps(self) -> float:
        """Draw one slippage sample in basis points, floored at 0 and capped at max_bps."""
        if self.distribution == "normal":
            raw = self._sample_normal()
        elif self.distribution == "uniform":
            raw = self._sample_uniform()
        else:
            raw = self._sample_lognormal()

        return float(min(max(0.0, raw), self.max_bps))

    def _sample_normal(self) -> float:
        if self.std_bps == 0.0:
            return self.mean_bps
        return float(self._rng.normal(loc=self.mean_bps, scale=self.std_bps))

    def _sample_uniform(self) -> float:
        half_width = self.std_bps * math.sqrt(3)
        if half_width == 0.0:
            return self.mean_bps
        low = max(0.0, self.mean_bps - half_width)
        high = self.mean_bps + half_width
        return float(self._rng.uniform(low=low, high=high))

    def _sample_lognormal(self) -> float:
        mean = self.mean_bps
        std = self.std_bps
        if mean <= 0.0:
            return 0.0
        if std == 0.0:
            return mean
        cv_sq = (std / mean) ** 2
        log_sigma_sq = math.log1p(cv_sq)
        log_mu = math.log(mean) - log_sigma_sq / 2.0
        return float(self._rng.lognormal(mean=log_mu, sigma=math.sqrt(log_sigma_sq)))

    def to_payload(self) -> dict[str, Any]:
        return {
            "distribution": self.distribution,
            "mean_bps": self.mean_bps,
            "std_bps": self.std_bps,
            "max_bps": self.max_bps,
            "seed": self.seed,
        }


__all__ = [
    "STOCHASTIC_SLIPPAGE_STRESS_MEAN_BPS",
    "STOCHASTIC_SLIPPAGE_STRESS_STD_BPS",
    "STOCHASTIC_SLIPPAGE_STRESS_MAX_BPS",
    "StochasticSlippageModel",
    "build_stochastic_stress_preset",
]
