"""
Turtle-Breakout-Strategie für die Cilly Trading Engine.

MVP-Version:

- Betrachtet das höchste Hoch der letzten N Kerzen (klassisch z. B. 20).
- Wenn der Schlusskurs über dieses Breakout-Level steigt:
    -> ENTRY CONFIRMED (stage="entry_confirmed")
- Wenn der Schlusskurs knapp unterhalb des Breakout-Levels notiert:
    -> SETUP (stage="setup")

Score:
- Je näher bzw. je klarer über dem Breakout-Level, desto höher der Score.
- Wertebereich: 0–100 (im MVP vereinfacht heuristisch berechnet).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Any

import pandas as pd

from cilly_trading.models import Signal
from cilly_trading.engine.core import BaseStrategy


@dataclass
class TurtleConfig:
    """
    Konfiguration für die Turtle-Strategie.

    breakout_lookback:
        Anzahl der Kerzen für das Breakout-Hoch (klassisch z. B. 20).
    proximity_threshold_pct:
        Wie nah der Schlusskurs unterhalb des Breakout-Levels liegen darf,
        um als SETUP zu gelten (z. B. 0.03 = 3 %).
    min_score:
        Mindestscore, ab dem ein Signal überhaupt ausgegeben wird.
    stop_loss_buffer_pct:
        Puffer unterhalb des Breakout-Levels für den Stop-Loss.
        Standard: 0.01 (1 % unter dem Breakout-Level).
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
        )

        if df.empty:
            return []

        for col in ("high", "close"):
            if col not in df.columns:
                raise ValueError(f"DataFrame must contain '{col}' for TurtleStrategy")

        # Höchstes Hoch der letzten N Kerzen VOR der aktuellen Kerze
        # rolling(...).max() -> max pro Fenster
        # shift(1) -> Fenster endet mit der VORHERIGEN Kerze
        highs_rolling = df["high"].rolling(
            window=cfg.breakout_lookback,
            min_periods=cfg.breakout_lookback,
        ).max()
        prior_breakout_levels = highs_rolling.shift(1)

        last_idx = df.index[-1]
        prior_breakout_level = prior_breakout_levels.loc[last_idx]

        # Wenn wir nicht genug Historie haben, gibt es kein Setup
        if pd.isna(prior_breakout_level):
            return []

        last_high = float(df.loc[last_idx, "high"])
        last_close = float(df.loc[last_idx, "close"])

        signals: List[Signal] = []

        # Breakout-Level als float
        breakout_level = float(prior_breakout_level)

        # 1) Entry CONFIRMED: Schlusskurs über dem Breakout-Level
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
                "Position halten, solange der Schlusskurs nicht deutlich "
                "unter das Breakout-Level fällt (z. B. Tagesschluss unter dem "
                "Breakout-Hoch oder unter einem definierten Trailing-Stop)."
            )

            _scale = Decimal("0.0001")
            _stop = float(
                (
                    Decimal(str(breakout_level))
                    * (Decimal("1") - Decimal(str(cfg.stop_loss_buffer_pct)))
                ).quantize(_scale, ROUND_HALF_UP)
            )
            signal: Signal = {
                "strategy": self.name,
                "direction": "long",
                "score": score,
                "stage": "entry_confirmed",
                "confirmation_rule": confirmation_rule,
                "entry_zone": {
                    "from_": float(
                        Decimal(str(breakout_level)).quantize(_scale, ROUND_HALF_UP)
                    ),
                    "to": float(
                        (
                            Decimal(str(last_close))
                            * Decimal(str(cfg.confirmed_entry_zone_upper_factor))
                        ).quantize(_scale, ROUND_HALF_UP)
                    ),
                },
                "stop_loss": _stop,
            }
            signals.append(signal)

        else:
            # 2) SETUP: Schlusskurs knapp unterhalb des Breakout-Levels
            # z. B. innerhalb von proximity_threshold_pct unterhalb des Levels
            distance_to_level = (breakout_level - last_close) / breakout_level  # positiv, wenn darunter

            if 0.0 <= distance_to_level <= cfg.proximity_threshold_pct:
                score = cfg.setup_score_base - (
                    distance_to_level / cfg.proximity_threshold_pct
                ) * cfg.setup_score_range
                score = max(0.0, min(100.0, score))

                if score >= cfg.min_score:
                    confirmation_rule = (
                        "Long-Einstieg bei Tagesschluss oberhalb des Breakout-Levels "
                        f"(Breakout-Level ~ {breakout_level:.2f}). "
                        "Alternativ: Stop-Buy-Order knapp über dem Breakout-Hoch."
                    )

                    _scale = Decimal("0.0001")
                    _stop = float(
                        (
                            Decimal(str(breakout_level))
                            * (Decimal("1") - Decimal(str(cfg.stop_loss_buffer_pct)))
                        ).quantize(_scale, ROUND_HALF_UP)
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
                                ).quantize(_scale, ROUND_HALF_UP)
                            ),
                            "to": float(
                                (
                                    Decimal(str(breakout_level))
                                    * Decimal(str(cfg.setup_entry_zone_upper_factor))
                                ).quantize(_scale, ROUND_HALF_UP)
                            ),
                        },
                        "stop_loss": _stop,
                    }
                    signals.append(signal)

        return signals
