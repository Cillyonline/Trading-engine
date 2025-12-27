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
from collections.abc import Mapping

from cilly_trading.models import Signal
from cilly_trading.repositories import SignalRepository
from cilly_trading.engine.data import load_ohlcv


logger = logging.getLogger(__name__)


STRATEGY_CONFIG_KEYS: Dict[str, set[str]] = {
    "RSI2": {"rsi_period", "oversold_threshold", "min_score"},
    "TURTLE": {"breakout_lookback", "proximity_threshold_pct", "min_score"},
}


def _normalize_strategy_config(strat_name: str, raw_config: Any) -> Dict[str, Any]:
    if raw_config is None:
        normalized: Dict[str, Any] = {}
    elif isinstance(raw_config, Mapping):
        normalized = dict(raw_config)
    else:
        logger.warning(
            "Invalid strategy config type for strategy=%s (expected mapping, got %s); using empty config",
            strat_name,
            type(raw_config).__name__,
        )
        normalized = {}

    allowed_keys = STRATEGY_CONFIG_KEYS.get(strat_name)
    if allowed_keys:
        unknown_keys = sorted(set(normalized.keys()) - allowed_keys)
        if unknown_keys:
            logger.warning(
                "Unknown config keys for strategy=%s: %s",
                strat_name,
                ", ".join(unknown_keys),
            )

    return normalized


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

    Robustheitsziele (MVP):
    - Leere DataFrames skippen
    - Pro Symbol loggen (info/warning)
    - Engine darf niemals abbrechen
    """
    logger.info(
        "Engine run started: symbols=%d strategies=%d timeframe=%s lookback_days=%d market_type=%s",
        len(symbols),
        len(strategies),
        engine_config.timeframe,
        engine_config.lookback_days,
        engine_config.market_type,
    )

    if not isinstance(strategy_configs, Mapping):
        logger.warning(
            "Invalid strategy_configs type (expected mapping, got %s); using empty configs",
            type(strategy_configs).__name__,
        )
        strategy_configs_map: Mapping[str, Any] = {}
    else:
        strategy_configs_map = strategy_configs

    all_signals: List[Signal] = []

    for symbol in symbols:
        logger.info("Symbol analysis start: symbol=%s", symbol)

        try:
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
                    market_type=engine_config.market_type,
                )
            except Exception:
                logger.error("Error loading data for symbol=%s", symbol, exc_info=True)
                continue

            # Leere / fehlende Daten sauber skippen
            if df is None or getattr(df, "empty", False):
                logger.warning(
                    "Skipping symbol due to empty OHLCV data: symbol=%s timeframe=%s lookback_days=%d market_type=%s",
                    symbol,
                    engine_config.timeframe,
                    engine_config.lookback_days,
                    engine_config.market_type,
                )
                continue

            symbol_signals_count = 0

            for strategy in strategies:
                strat_name = getattr(strategy, "name", strategy.__class__.__name__)
                raw_config = strategy_configs_map.get(strat_name)
                strat_config = _normalize_strategy_config(strat_name, raw_config)

                logger.debug("Running strategy=%s for symbol=%s", strat_name, symbol)

                try:
                    signals = strategy.generate_signals(df, strat_config)
                except Exception:
                    # Fehler in einer Strategie dürfen die Engine nicht stoppen
                    logger.error(
                        "Error in strategy=%s for symbol=%s",
                        strat_name,
                        symbol,
                        exc_info=True,
                    )
                    continue

                # Defensive: Strategie liefert None oder leere Liste
                if not signals:
                    logger.info(
                        "Strategy finished: strategy=%s symbol=%s signals=0",
                        strat_name,
                        symbol,
                    )
                    continue

                logger.info(
                    "Strategy finished: strategy=%s symbol=%s signals=%d",
                    strat_name,
                    symbol,
                    len(signals),
                )

                for s in signals:
                    try:
                        s.setdefault("symbol", symbol)
                        s.setdefault("strategy", strat_name)
                        s.setdefault("timestamp", _now_iso())
                        s.setdefault("timeframe", engine_config.timeframe)
                        s.setdefault("market_type", engine_config.market_type)
                        s.setdefault("data_source", engine_config.data_source)
                        s.setdefault("direction", "long")
                    except Exception:
                        logger.error(
                            "Invalid signal object from strategy=%s for symbol=%s (skipping signal)",
                            strat_name,
                            symbol,
                            exc_info=True,
                        )
                        continue

                all_signals.extend(signals)
                symbol_signals_count += len(signals)

            logger.info(
                "Symbol analysis done: symbol=%s signals=%d",
                symbol,
                symbol_signals_count,
            )

        except Exception:
            # Letzter Schutzschirm: ein Symbol darf die Engine nie stoppen
            logger.error(
                "Unexpected error while processing symbol=%s",
                symbol,
                exc_info=True,
            )
            continue

    if all_signals:
        logger.info("Persisting %d signals", len(all_signals))
        try:
            signal_repo.save_signals(all_signals)
        except Exception:
            # Persistenzfehler dürfen die Engine nicht abbrechen
            logger.error(
                "Error persisting signals (signals_total=%d)",
                len(all_signals),
                exc_info=True,
            )
        logger.info("Engine run completed: signals_total=%d", len(all_signals))
    else:
        logger.info("Engine run completed: signals_total=0")

    return all_signals
