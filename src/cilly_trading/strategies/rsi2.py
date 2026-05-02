"""
RSI2-Strategie (Rebound) für die Cilly Trading Engine.

Grundidee (MVP-Version):
- Nutzt einen sehr kurzen RSI (Standard: 2 Perioden) als Rebound-Signal.
- Erzeugt ein SETUP-Signal, wenn der RSI2 stark überverkauft ist.
- Die eigentliche Entry-Bestätigung erfolgt später durch eine klare Regel
  (z. B. Close über dem Hoch der Vorkerze), die im Feld `confirmation_rule`
  als Text mitgegeben wird.

Die Strategie arbeitet nur auf der letzten verfügbaren Kerze.
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
    """
    Konfiguration für die RSI2-Strategie.

    rsi_period:
        Länge des RSI-Fensters. Klassisch für RSI2: 2.
    oversold_threshold:
        Schwelle für "extrem überverkauft". Standard: 10.
    min_score:
        Mindestscore, den ein Signal erreichen muss, um ausgegeben zu werden.
        (Sicherheit, um extrem schwache Signale zu filtern.)
    stop_loss_pct:
        Prozentuale Stop-Loss-Distanz unter dem Close zum Zeitpunkt des Signals.
        Standard: 0.05 (5 % unter dem Close).
    """
    rsi_period: int = 2
    oversold_threshold: float = 10.0
    min_score: float = 20.0
    stop_loss_pct: float = 0.05
    entry_zone_lower_factor: float = 0.97
    entry_zone_upper_factor: float = 1.01


class Rsi2Strategy(BaseStrategy):
    """
    RSI2-Strategie gemäß MVP-Definition.

    Hinweis:
    - Diese Implementierung betrachtet nur die letzte Kerze im DataFrame.
    - Das vermeidet eine Flut an historischen Signalen und ist für
      den MVP (aktuelle Setups finden) absolut ausreichend.
    """

    name: str = "RSI2"

    def generate_signals(
        self,
        df: pd.DataFrame,
        config: Dict[str, Any],
    ) -> List[Signal]:
        if df.empty:
            return []

        # Konfiguration aus Dict in Rsi2Config überführen (mit Defaults)
        cfg = Rsi2Config(
            rsi_period=int(config.get("rsi_period", 2)),
            oversold_threshold=float(config.get("oversold_threshold", 10.0)),
            min_score=float(config.get("min_score", 20.0)),
            stop_loss_pct=float(config.get("stop_loss_pct", 0.05)),
            entry_zone_lower_factor=float(config.get("entry_zone_lower_factor", 0.97)),
            entry_zone_upper_factor=float(config.get("entry_zone_upper_factor", 1.01)),
        )

        # Sicherstellen, dass die notwendigen Spalten existieren
        if "close" not in df.columns:
            raise ValueError("DataFrame must contain a 'close' column for RSI2Strategy")

        # RSI2 berechnen
        rsi_series = rsi(df, period=cfg.rsi_period, price_column="close")

        # Letzte Zeile betrachten
        last_idx = df.index[-1]
        last_close = float(df.loc[last_idx, "close"])
        last_rsi = float(rsi_series.loc[last_idx])

        signals: List[Signal] = []

        # Check: ist RSI extrem überverkauft?
        if last_rsi < cfg.oversold_threshold:
            # Score ableiten:
            # Je tiefer der RSI, desto höher der Score.
            # Beispiel: RSI=0 → Score=100, RSI=oversold_threshold → Score ~ 0
            raw_score = (cfg.oversold_threshold - last_rsi) / cfg.oversold_threshold * 100.0
            score = max(0.0, min(100.0, raw_score))

            if score < cfg.min_score:
                # Signal zu schwach, nicht ausgeben
                return []

            # Textliche Bestätigungsregel (Entry-Logik) als Guidance
            confirmation_rule = (
                "Long-Einstieg, wenn der Schlusskurs einer der folgenden Kerzen "
                "über dem Hoch der Auslösekerze schließt UND der RSI2 wieder "
                "über dem Oversold-Bereich liegt."
            )

            signal: Signal = {
                # symbol, timeframe, market_type, data_source, timestamp
                # werden im Engine-Layer gesetzt (run_watchlist_analysis)
                "strategy": self.name,
                "direction": "long",
                "score": score,
                "stage": "setup",
                "confirmation_rule": confirmation_rule,
                "entry_zone": {
                    "from_": float(
                        (Decimal(str(last_close)) * Decimal(str(cfg.entry_zone_lower_factor))).quantize(PRICE_SCALE, ROUND_HALF_UP)
                    ),
                    "to": float(
                        (Decimal(str(last_close)) * Decimal(str(cfg.entry_zone_upper_factor))).quantize(PRICE_SCALE, ROUND_HALF_UP)
                    ),
                },
                "stop_loss": float(
                    (
                        Decimal(str(last_close))
                        * (Decimal("1") - Decimal(str(cfg.stop_loss_pct)))
                    ).quantize(PRICE_SCALE, ROUND_HALF_UP)
                ),
            }

            signals.append(signal)

        return signals
