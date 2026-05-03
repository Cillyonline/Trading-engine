"""RSI2 mean-reversion strategy for the Cilly Trading Engine.

Core idea (MVP):
- Uses a very short RSI (default: 2 periods) as a rebound signal.
- Emits a SETUP signal when RSI2 is strongly oversold.
- Emits an EXIT signal when RSI2 is overbought, indicating the rebound has played out.
- Entry confirmation guidance is provided in the ``confirmation_rule`` field.

The strategy evaluates only the last available bar in the DataFrame.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Any

import pandas as pd

from cilly_trading.models import Signal
from cilly_trading.engine.core import BaseStrategy
from cilly_trading.indicators.rsi import rsi
from cilly_trading.strategies._constants import PRICE_SCALE


@dataclass
class Rsi2Config:
    """Configuration for the RSI2 strategy.

    rsi_period:
        RSI window length. Classic RSI2 uses 2.
    oversold_threshold:
        Threshold for "extremely oversold". Default: 10.
    overbought_threshold:
        Threshold for "overbought" — triggers an exit signal. Default: 70.
    min_score:
        Minimum score a signal must reach to be emitted.
        Filters out extremely weak signals.
    stop_loss_pct:
        Percentage stop-loss distance below the close at signal time.
        Default: 0.05 (5% below close).
    entry_zone_lower_factor:
        Lower bound of the entry zone relative to close. Default: 0.97.
    entry_zone_upper_factor:
        Upper bound of the entry zone relative to close. Default: 1.01.
    """
    rsi_period: int = 2
    oversold_threshold: float = 10.0
    overbought_threshold: float = 70.0
    min_score: float = 20.0
    stop_loss_pct: float = 0.05
    entry_zone_lower_factor: float = 0.97
    entry_zone_upper_factor: float = 1.01


class Rsi2Strategy(BaseStrategy):
    """RSI2 strategy per MVP definition.

    Note:
    - Evaluates only the last bar in the DataFrame.
    - This avoids flooding the system with historical signals and is
      sufficient for finding current setups and exit conditions.
    """

    name: str = "RSI2"

    def generate_signals(
        self,
        df: pd.DataFrame,
        config: Dict[str, Any],
    ) -> List[Signal]:
        if df.empty:
            return []

        cfg = Rsi2Config(
            rsi_period=int(config.get("rsi_period", 2)),
            oversold_threshold=float(config.get("oversold_threshold", 10.0)),
            overbought_threshold=float(config.get("overbought_threshold", 70.0)),
            min_score=float(config.get("min_score", 20.0)),
            stop_loss_pct=float(config.get("stop_loss_pct", 0.05)),
            entry_zone_lower_factor=float(config.get("entry_zone_lower_factor", 0.97)),
            entry_zone_upper_factor=float(config.get("entry_zone_upper_factor", 1.01)),
        )

        if "close" not in df.columns:
            raise ValueError("DataFrame must contain a 'close' column for RSI2Strategy")

        # Compute RSI series; only uses past data — no lookahead bias.
        rsi_series = rsi(df, period=cfg.rsi_period, price_column="close")

        last_idx = df.index[-1]
        last_close = float(df.loc[last_idx, "close"])
        last_rsi = float(rsi_series.loc[last_idx])

        # EXIT: RSI is overbought — the mean-reversion move has likely played out.
        if last_rsi > cfg.overbought_threshold:
            # Score: how far above the overbought threshold (0 = barely, 100 = RSI at 100).
            raw_score = (last_rsi - cfg.overbought_threshold) / (100.0 - cfg.overbought_threshold) * 100.0
            score = max(0.0, min(100.0, raw_score))

            exit_signal: Signal = {
                "strategy": self.name,
                "direction": "long",
                "score": score,
                "stage": "exit",
                "confirmation_rule": (
                    "Exit long position: RSI2 has crossed above the overbought threshold, "
                    "indicating the mean-reversion rebound has likely completed."
                ),
            }
            return [exit_signal]

        # SETUP: RSI is extremely oversold — potential mean-reversion entry.
        if last_rsi < cfg.oversold_threshold:
            # Score: deeper oversold → higher score.
            raw_score = (cfg.oversold_threshold - last_rsi) / cfg.oversold_threshold * 100.0
            score = max(0.0, min(100.0, raw_score))

            if score < cfg.min_score:
                return []

            confirmation_rule = (
                "Enter long when a subsequent bar closes above the high of the trigger bar "
                "AND RSI2 is no longer in the oversold zone."
            )

            setup_signal: Signal = {
                "strategy": self.name,
                "direction": "long",
                "score": score,
                "stage": "setup",
                "confirmation_rule": confirmation_rule,
                "entry_zone": {
                    "from_": float(
                        (
                            Decimal(str(last_close))
                            * Decimal(str(cfg.entry_zone_lower_factor))
                        ).quantize(PRICE_SCALE, ROUND_HALF_UP)
                    ),
                    "to": float(
                        (
                            Decimal(str(last_close))
                            * Decimal(str(cfg.entry_zone_upper_factor))
                        ).quantize(PRICE_SCALE, ROUND_HALF_UP)
                    ),
                },
                "stop_loss": float(
                    (
                        Decimal(str(last_close))
                        * (Decimal("1") - Decimal(str(cfg.stop_loss_pct)))
                    ).quantize(PRICE_SCALE, ROUND_HALF_UP)
                ),
            }
            return [setup_signal]

        return []
