"""
Core-Engine der Cilly Trading Engine.

- Definiert das Strategy-Interface (BaseStrategy)
- Definiert EngineConfig
- Implementiert `run_watchlist_analysis`
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol, List, Dict, Any

from cilly_trading.models import Signal
from cilly_trading.repositories import SignalRepository
from cilly_trading.engine.data import load_ohlcv


logger = logging.getLogger(__name__)


@dataclass
class EngineConfig:
    """
    Minimale Konfiguration für die Engine.

    MVP-Fokus:
    - Tagesdaten (D1)
    - Lookback in Tagen
    - Markt-Typ (Aktie/Krypto)
    """
    timeframe: str = "D1"
    lookback_days: int = 200
    market_type: str = "stock"   # "stock" oder "crypto"
    data_source: str = "yahoo"   # informativ; wird aktuell im Daten-Layer abgeleitet


class BaseStrategy(Protocol):
    """
    Interface, das jede Strategie im MVP implementieren muss.
    """

    name: str  # z. B. "RSI2" oder "TURTLE"

    def generate_signals(
        self,
        df,
        config: Dict[str, Any],
    ) -> List[Signal]:
        """
        Erzeugt eine Liste von Signals auf Basis der übergebenen Kursdaten.

        df: DataFrame mit Spalten ["timestamp", "open", "high", "low", "close", "volume"]
        config: Strategiekonfiguration (MVP: einfacher Dict)
        """
        ...


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_watchlist_analysis(
    symbols: List[str],
    strategies: List[BaseStrategy],
    engine_config: EngineConfig,
    strategy_configs: Dict[str, Dict[str, Any]],
    signal_repo: SignalRepository,
) -> List[Signal]:
    """
    Führt die Analyse über eine Symbol-Watchlist und eine Liste von Strategien aus.

    - lädt Kursdaten pro Symbol
    - lässt alle Strategien laufen
    - schreibt alle resultierenden Signals in das SignalRepository
    - gibt die Signals zurück
    """
    logger.info(
        "Engine run started: symbols=%d strategies=%d timeframe=%s lookback_days=%d market_type=%s",
        len(symbols),
        len(strategies),
        engine_config.timeframe,
        engine_config.lookback_days,
        engine_config.market_type,
    )

    all_signals: List[Signal] = []

    for symbol in symbols:
        logger.debug(
            "Loading data for symbol=%s market_type=%s lookback_days=%d timeframe=%s",
            symbol,
            engine_config.market_type,
            engine_config.lookback_days,
            engine_config.timeframe,
        )

        try:
            df = load_ohlcv(
                symbol=symbol,
                timeframe=engine_config.timeframe,
                lookback_days=engine_config.lookback_days,
                market_type=engine_config.market_type,  # "stock" | "crypto"
            )
        except Exception:
            logger.error("Error loading data for symbol=%s", symbol, exc_info=True)
            continue

        for strategy in strategies:
            strat_name = getattr(strategy, "name", strategy.__class__.__name__)
            strat_config = strategy_configs.get(strat_name, {})

            logger.debug("Running strategy=%s for symbol=%s", strat_name, symbol)

            try:
                signals = strategy.generate_signals(df, strat_config)
            except Exception:
                # MVP: Fehler in einer Strategie sollen nicht die gesamte Engine stoppen
                logger.error(
                    "Error in strategy=%s for symbol=%s",
                    strat_name,
                    symbol,
                    exc_info=True,
                )
                continue

            logger.info(
                "Strategy finished: strategy=%s symbol=%s signals=%d",
                strat_name,
                symbol,
                len(signals),
            )

            # Basisfelder sicherstellen
            for s in signals:
                s.setdefault("symbol", symbol)
                s.setdefault("strategy", strat_name)
                s.setdefault("timestamp", _now_iso())
                s.setdefault("timeframe", engine_config.timeframe)
                s.setdefault("market_type", engine_config.market_type)
                # Informativ, passt zu deinem Datenmodell
                s.setdefault("data_source", engine_config.data_source)
                s.setdefault("direction", "long")

            all_signals.extend(signals)

    if all_signals:
        logger.info("Persisting %d signals", len(all_signals))
        signal_repo.save_signals(all_signals)
        logger.info("Engine run completed: signals_total=%d", len(all_signals))
    else:
        logger.info("Engine run completed: signals_total=0")

    return all_signals
