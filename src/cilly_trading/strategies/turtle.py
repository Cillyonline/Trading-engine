"""Turtle breakout strategy for the Cilly Trading Engine.

MVP version:

- Tracks the highest high of the last N bars (classic: 20).
- When close breaks above that level:
    -> ENTRY CONFIRMED (stage="entry_confirmed")
- When close is just below the breakout level (within proximity threshold):
    -> SETUP (stage="setup")
- When close drops below the trailing stop (lowest low of last M bars):
    -> EXIT (stage="exit")

Score:
- Entry: higher score the more clearly close is above/near the breakout level.
- Exit: 100.0 (definitive — trailing stop has been breached).
- Range: 0–100.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Any

import pandas as pd

from cilly_trading.indicators.atr import atr as compute_atr
from cilly_trading.models import Signal
from cilly_trading.engine.core import BaseStrategy
from cilly_trading.risk_framework.position_sizing import AtrPositionSizer
from cilly_trading.strategies._constants import PRICE_SCALE


@dataclass
class TurtleConfig:
    """Configuration for the Turtle strategy.

    breakout_lookback:
        Number of bars for the breakout high window (classic: 20).
    proximity_threshold_pct:
        How close the close may be below the breakout level to qualify as
        a SETUP signal (e.g. 0.03 = within 3%).
    min_score:
        Minimum score required to emit any signal.
    stop_loss_buffer_pct:
        Buffer below the breakout level for the initial stop-loss.
        Default: 0.01 (1% below the breakout level).
    exit_lookback:
        Number of bars for the trailing stop (lowest low window). Classic
        Turtle exit uses 10. The window is shifted by 1 bar to avoid
        lookahead bias.
    use_atr_sizing:
        When True, include ATR-based position size suggestion in emitted signals.
        Requires account_equity and risk_pct to be supplied in config.
    atr_period:
        Lookback period for ATR calculation (default: 14).
    atr_multiplier:
        Multiplier applied to ATR as a risk unit (default: 2.0).
    account_equity:
        Account equity used for ATR position sizing. Required when use_atr_sizing=True.
    risk_pct:
        Fraction of equity to risk per trade (default: 0.01). Used with ATR sizing.
    """
    breakout_lookback: int = 20
    proximity_threshold_pct: float = 0.03
    min_score: float = 30.0
    stop_loss_buffer_pct: float = 0.01
    confirmed_score_min: float = 60.0
    confirmed_score_range: float = 40.0
    confirmed_max_breakout_strength_pct: float = 0.05
    confirmed_entry_zone_upper_factor: float = 1.02
    setup_score_base: float = 80.0
    setup_score_range: float = 40.0
    setup_entry_zone_upper_factor: float = 1.01
    exit_lookback: int = 10
    use_atr_sizing: bool = False
    atr_period: int = 14
    atr_multiplier: float = 2.0
    account_equity: float | None = None
    risk_pct: float = 0.01


class TurtleStrategy(BaseStrategy):
    """
    MVP-Implementierung einer Turtle-Breakout-Strategie.

    - Arbeitet nur auf der letzten Kerze.
    - Nutzt das höchste Hoch der letzten N Kerzen (exklusive der aktuellen Kerze)
      als Breakout-Level.
    """

    name: str = "TURTLE"

    def generate_signals(
        self,
        df: pd.DataFrame,
        config: Dict[str, Any],
    ) -> List[Signal]:
        _account_equity = config.get("account_equity")
        cfg = TurtleConfig(
            breakout_lookback=int(config.get("breakout_lookback", 20)),
            proximity_threshold_pct=float(config.get("proximity_threshold_pct", 0.03)),
            min_score=float(config.get("min_score", 30.0)),
            stop_loss_buffer_pct=float(config.get("stop_loss_buffer_pct", 0.01)),
            confirmed_score_min=float(config.get("confirmed_score_min", 60.0)),
            confirmed_score_range=float(config.get("confirmed_score_range", 40.0)),
            confirmed_max_breakout_strength_pct=float(config.get("confirmed_max_breakout_strength_pct", 0.05)),
            confirmed_entry_zone_upper_factor=float(config.get("confirmed_entry_zone_upper_factor", 1.02)),
            setup_score_base=float(config.get("setup_score_base", 80.0)),
            setup_score_range=float(config.get("setup_score_range", 40.0)),
            setup_entry_zone_upper_factor=float(config.get("setup_entry_zone_upper_factor", 1.01)),
            exit_lookback=int(config.get("exit_lookback", 10)),
            use_atr_sizing=bool(config.get("use_atr_sizing", False)),
            atr_period=int(config.get("atr_period", 14)),
            atr_multiplier=float(config.get("atr_multiplier", 2.0)),
            account_equity=float(_account_equity) if _account_equity is not None else None,
            risk_pct=float(config.get("risk_pct", 0.01)),
        )

        if df.empty:
            return []

        for col in ("high", "low", "close"):
            if col not in df.columns:
                raise ValueError(f"DataFrame must contain '{col}' for TurtleStrategy")

        # ATR-based position sizing (optional).
        atr_position_size: float | None = None
        if cfg.use_atr_sizing and cfg.account_equity is not None:
            atr_series = compute_atr(df, period=cfg.atr_period)
            last_atr = atr_series.iloc[-1] if not atr_series.empty else float("nan")
            if not pd.isna(last_atr):
                sizer = AtrPositionSizer(
                    atr_period=cfg.atr_period,
                    atr_multiplier=cfg.atr_multiplier,
                )
                atr_position_size = sizer.compute_position_size(
                    account_equity=cfg.account_equity,
                    risk_pct=cfg.risk_pct,
                    atr_value=float(last_atr),
                )

        # Trailing stop: lowest low over exit_lookback bars, shifted by 1 to avoid lookahead.
        trailing_stops = df["low"].rolling(
            window=cfg.exit_lookback,
            min_periods=cfg.exit_lookback,
        ).min().shift(1)

        last_idx = df.index[-1]
        last_close = float(df.loc[last_idx, "close"])
        trailing_stop = trailing_stops.loc[last_idx]

        # EXIT: close has fallen below the trailing stop level.
        if not pd.isna(trailing_stop) and last_close < float(trailing_stop):
            exit_signal: Signal = {
                "strategy": self.name,
                "direction": "long",
                "score": 100.0,
                "stage": "exit",
                "confirmation_rule": (
                    f"Exit long position: close ({last_close:.2f}) has broken below the "
                    f"{cfg.exit_lookback}-bar trailing stop ({float(trailing_stop):.2f})."
                ),
            }
            if atr_position_size is not None:
                exit_signal["atr_position_size"] = atr_position_size
            return [exit_signal]

        # Highest high of the last N bars BEFORE the current bar.
        # rolling().max() computes the window max, shift(1) moves it one bar back
        # so the window ends at the previous bar — no lookahead bias.
        highs_rolling = df["high"].rolling(
            window=cfg.breakout_lookback,
            min_periods=cfg.breakout_lookback,
        ).max()
        prior_breakout_levels = highs_rolling.shift(1)

        prior_breakout_level = prior_breakout_levels.loc[last_idx]

        # Not enough history for a breakout level — no signal possible.
        if pd.isna(prior_breakout_level):
            return []

        last_high = float(df.loc[last_idx, "high"])
        breakout_level = float(prior_breakout_level)

        signals: List[Signal] = []

        # 1) ENTRY CONFIRMED: close is above the breakout level.
        if last_close > breakout_level:
            breakout_strength = (last_close - breakout_level) / breakout_level  # in %
            breakout_strength_clamped = max(
                0.0,
                min(breakout_strength, cfg.confirmed_max_breakout_strength_pct),
            )

            score = cfg.confirmed_score_min + (
                breakout_strength_clamped / cfg.confirmed_max_breakout_strength_pct
            ) * cfg.confirmed_score_range

            if score < cfg.min_score:
                return []

            confirmation_rule = (
                "Hold position as long as close does not break significantly below the "
                "breakout level (e.g. daily close below breakout high or trailing stop)."
            )

            _stop = float(
                (
                    Decimal(str(breakout_level))
                    * (Decimal("1") - Decimal(str(cfg.stop_loss_buffer_pct)))
                ).quantize(PRICE_SCALE, ROUND_HALF_UP)
            )
            signal: Signal = {
                "strategy": self.name,
                "direction": "long",
                "score": score,
                "stage": "entry_confirmed",
                "confirmation_rule": confirmation_rule,
                "entry_zone": {
                    "from_": float(
                        Decimal(str(breakout_level)).quantize(PRICE_SCALE, ROUND_HALF_UP)
                    ),
                    "to": float(
                        (
                            Decimal(str(last_close))
                            * Decimal(str(cfg.confirmed_entry_zone_upper_factor))
                        ).quantize(PRICE_SCALE, ROUND_HALF_UP)
                    ),
                },
                "stop_loss": _stop,
            }
            if atr_position_size is not None:
                signal["atr_position_size"] = atr_position_size
            signals.append(signal)

        else:
            # 2) SETUP: close is just below the breakout level (within proximity threshold).
            distance_to_level = (breakout_level - last_close) / breakout_level

            if 0.0 <= distance_to_level <= cfg.proximity_threshold_pct:
                score = cfg.setup_score_base - (
                    distance_to_level / cfg.proximity_threshold_pct
                ) * cfg.setup_score_range
                score = max(0.0, min(100.0, score))

                if score >= cfg.min_score:
                    confirmation_rule = (
                        f"Enter long on a daily close above the breakout level "
                        f"(breakout level ~ {breakout_level:.2f}). "
                        "Alternative: stop-buy order just above the breakout high."
                    )

                    _stop = float(
                        (
                            Decimal(str(breakout_level))
                            * (Decimal("1") - Decimal(str(cfg.stop_loss_buffer_pct)))
                        ).quantize(PRICE_SCALE, ROUND_HALF_UP)
                    )
                    signal = {
                        "strategy": self.name,
                        "direction": "long",
                        "score": score,
                        "stage": "setup",
                        "confirmation_rule": confirmation_rule,
                        "entry_zone": {
                            "from_": float(
                                (
                                    Decimal(str(breakout_level))
                                    * (Decimal("1") - Decimal(str(cfg.proximity_threshold_pct)))
                                ).quantize(PRICE_SCALE, ROUND_HALF_UP)
                            ),
                            "to": float(
                                (
                                    Decimal(str(breakout_level))
                                    * Decimal(str(cfg.setup_entry_zone_upper_factor))
                                ).quantize(PRICE_SCALE, ROUND_HALF_UP)
                            ),
                        },
                        "stop_loss": _stop,
                    }
                    if atr_position_size is not None:
                        signal["atr_position_size"] = atr_position_size
                    signals.append(signal)

        return signals
