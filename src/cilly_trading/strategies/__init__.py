"""
Strategie-Paket für die Cilly Trading Engine.

Im MVP enthalten:
- Rsi2Strategy (Rebound auf Basis RSI2)
- TurtleStrategy (Breakout über N-Tage-Hoch)
"""

from __future__ import annotations

from .rsi2 import Rsi2Strategy
from .turtle import TurtleStrategy

__all__ = ["Rsi2Strategy", "TurtleStrategy"]
