"""
Strategie-Paket für die Cilly Trading Engine.

Im MVP enthalten:
- Rsi2Strategy (Rebound auf Basis RSI2)
- (später) TurtleStrategy
"""

from __future__ import annotations

from .rsi2 import Rsi2Strategy

__all__ = ["Rsi2Strategy"]
