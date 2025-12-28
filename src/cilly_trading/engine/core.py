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
            "Invalid strategy config type: component=engine strategy=%s (expected mapping, got %s); using empty config",
            strat_name,
            type(raw_config).__name__,
        )
        normalized = {}

    allowed_keys = STRATEGY_CONFIG_KEYS.get(strat_name)
    if allowed_keys:
        unknown_keys = sorted(set(normalized.keys()) - allowed_keys)
        if unknown_keys:
            logger.warning(
                "Unknown config keys: component=engine strategy=%s keys=%s",
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
        "Engine run started: component=engine symbols=%d strategies=%d timeframe=%s lookback_days=%d market_type=%s",
        len(symbols),
        len(strategies),
        engine_config.timeframe,
        engine_config.lookback_days,
        engine_config.market_type,
    )

    if not isinstance(strategy_configs, Mapping):
        logger.warning(
            "Invalid strategy_configs type: component=engine (expected mapping, got %s); using empty configs",
            type(strategy_configs).__name__,
        )
        strategy_configs_map: Mapping[str, Any] = {}
    else:
        strategy_configs_map = strategy_configs

    all_signals: List[Signal] = []
    ordered_symbols = sorted(symbols)
    ordered_strategies = sorted(
        strategies,
        key=lambda s: getattr(s, "name", s.__class__.__name__),
    )

    for symbol in ordered_symbols:
        logger.info(
            "Symbol analysis start: component=engine symbol=%s timeframe=%s",
            symbol,
            engine_config.timeframe,
        )

        try:
            logger.debug(
                "Loading data: component=engine symbol=%s market_type=%s lookback_days=%d timeframe=%s",
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
                logger.error(
                    "Error loading data: component=engine symbol=%s timeframe=%s",
                    symbol,
                    engine_config.timeframe,
                    exc_info=True,
                )
                continue

            # Leere / fehlende Daten sauber skippen
            if df is None or getattr(df, "empty", False):
                logger.warning(
                    "Skipping symbol due to empty OHLCV data: component=engine symbol=%s timeframe=%s lookback_days=%d market_type=%s",
                    symbol,
                    engine_config.timeframe,
                    engine_config.lookback_days,
                    engine_config.market_type,
                )
                continue

            symbol_signals_count = 0

            for strategy in ordered_strategies:
                strat_name = getattr(strategy, "name", strategy.__class__.__name__)
                raw_config = strategy_configs_map.get(strat_name)
                strat_config = _normalize_strategy_config(strat_name, raw_config)

                logger.debug(
                    "Running strategy: component=engine strategy=%s symbol=%s timeframe=%s",
                    strat_name,
                    symbol,
                    engine_config.timeframe,
                )

                try:
                    signals = strategy.generate_signals(df, strat_config)
                except Exception:
                    # Fehler in einer Strategie dürfen die Engine nicht stoppen
                    logger.error(
                        "Error in strategy: component=engine strategy=%s symbol=%s timeframe=%s",
                        strat_name,
                        symbol,
                        engine_config.timeframe,
                        exc_info=True,
                    )
                    continue

                # Defensive: Strategie liefert None oder leere Liste
                if not signals:
                    logger.debug(
                        "Strategy finished: component=engine strategy=%s symbol=%s timeframe=%s signals=0",
                        strat_name,
                        symbol,
                        engine_config.timeframe,
                    )
                    continue

                logger.debug(
                    "Strategy finished: component=engine strategy=%s symbol=%s timeframe=%s signals=%d",
                    strat_name,
                    symbol,
                    engine_config.timeframe,
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
                            "Invalid signal object from strategy: component=engine strategy=%s symbol=%s timeframe=%s (skipping signal)",
                            strat_name,
                            symbol,
                            engine_config.timeframe,
                            exc_info=True,
                        )
                        continue

                all_signals.extend(signals)
                symbol_signals_count += len(signals)

            logger.info(
                "Symbol analysis done: component=engine symbol=%s timeframe=%s signals=%d",
                symbol,
                engine_config.timeframe,
                symbol_signals_count,
            )

        except Exception:
            # Letzter Schutzschirm: ein Symbol darf die Engine nie stoppen
            logger.error(
                "Unexpected error while processing symbol: component=engine symbol=%s timeframe=%s",
                symbol,
                engine_config.timeframe,
                exc_info=True,
            )
            continue

    if all_signals:
        logger.info(
            "Persisting signals: component=engine signals_total=%d",
            len(all_signals),
        )
        try:
            signal_repo.save_signals(all_signals)
        except Exception:
            # Persistenzfehler dürfen die Engine nicht abbrechen
            logger.error(
                "Error persisting signals: component=engine signals_total=%d",
                len(all_signals),
                exc_info=True,
            )
        logger.info(
            "Engine run completed: component=engine signals_total=%d",
            len(all_signals),
        )
    else:
        logger.info("Engine run completed: component=engine signals_total=0")

    return all_signals
