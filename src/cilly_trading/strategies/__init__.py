"""
Strategie-Paket für die Cilly Trading Engine.

Im MVP enthalten:
- Rsi2Strategy (Rebound auf Basis RSI2)
- TurtleStrategy (Breakout über N-Tage-Hoch)
"""

from __future__ import annotations

from .experiment_search import (
    ParameterSearchExperimentConfig,
    ParameterSearchRunResult,
    StrategyLabConfigError,
    StrategyLabRunError,
    run_parameter_search_experiment,
)
from .registry import initialize_default_registry
from .rsi2 import Rsi2Strategy
from .turtle import TurtleStrategy

initialize_default_registry()

__all__ = [
    "ParameterSearchExperimentConfig",
    "ParameterSearchRunResult",
    "Rsi2Strategy",
    "StrategyLabConfigError",
    "StrategyLabRunError",
    "TurtleStrategy",
    "run_parameter_search_experiment",
]
