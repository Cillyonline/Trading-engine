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
from typing import List, Dict, Any

import pandas as pd

from cilly_trading.models import Signal
from cilly_trading.engine.core import BaseStrategy
from cilly_trading.strategies.config_schema import normalize_turtle_config


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
    """
    breakout_lookback: int = 20
    proximity_threshold_pct: float = 0.03
    min_score: float = 30.0


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
        config = normalize_turtle_config(config)
        cfg = TurtleConfig(
            breakout_lookback=int(config.get("breakout_lookback", 20)),
            proximity_threshold_pct=float(config.get("proximity_threshold_pct", 0.03)),
            min_score=float(config.get("min_score", 30.0)),
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
            # Wir gehen von 0–5 % "vernünftiger" Breakout-Stärke aus
            breakout_strength_clamped = max(0.0, min(breakout_strength, 0.05))

            # Score zwischen 60 und 100
            score = 60.0 + (breakout_strength_clamped / 0.05) * 40.0

            if score < cfg.min_score:
                return []

            confirmation_rule = (
                "Position halten, solange der Schlusskurs nicht deutlich "
                "unter das Breakout-Level fällt (z. B. Tagesschluss unter dem "
                "Breakout-Hoch oder unter einem definierten Trailing-Stop)."
            )

            signal: Signal = {
                "strategy": self.name,
                "direction": "long",
                "score": score,
                "stage": "entry_confirmed",
                "confirmation_rule": confirmation_rule,
                "entry_zone": {
                    # Entry in der Zone rund um das Breakout-Level bis leicht über dem Close
                    "from_": breakout_level,
                    "to": last_close * 1.02,
                },
            }
            signals.append(signal)

        else:
            # 2) SETUP: Schlusskurs knapp unterhalb des Breakout-Levels
            # z. B. innerhalb von proximity_threshold_pct unterhalb des Levels
            distance_to_level = (breakout_level - last_close) / breakout_level  # positiv, wenn darunter

            if 0.0 <= distance_to_level <= cfg.proximity_threshold_pct:
                # Je näher am Level, desto höher der Score.
                # distance = 0 -> Score ~ 80, distance = threshold -> Score ~ 40
                score = 80.0 - (distance_to_level / cfg.proximity_threshold_pct) * 40.0
                score = max(0.0, min(100.0, score))

                if score >= cfg.min_score:
                    confirmation_rule = (
                        "Long-Einstieg bei Tagesschluss oberhalb des Breakout-Levels "
                        f"(Breakout-Level ~ {breakout_level:.2f}). "
                        "Alternativ: Stop-Buy-Order knapp über dem Breakout-Hoch."
                    )

                    signal = {
                        "strategy": self.name,
                        "direction": "long",
                        "score": score,
                        "stage": "setup",
                        "confirmation_rule": confirmation_rule,
                        "entry_zone": {
                            # Einstiegszone knapp um das Breakout-Level
                            "from_": breakout_level * (1.0 - cfg.proximity_threshold_pct),
                            "to": breakout_level * 1.01,
                        },
                    }
                    signals.append(signal)

        return signals
