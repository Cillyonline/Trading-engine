"""
Core-Engine der Cilly Trading Engine.

- Definiert das Strategy-Interface (BaseStrategy)
- Definiert EngineConfig
- Implementiert `run_watchlist_analysis`
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol, List, Dict, Any, Optional
from collections.abc import Mapping
from pathlib import Path

from cilly_trading.models import Signal
from cilly_trading.repositories import SignalRepository
from cilly_trading.engine.data import load_ohlcv, load_ohlcv_snapshot
from cilly_trading.engine.strategy_params import normalize_and_validate_strategy_params


logger = logging.getLogger(__name__)


def _normalize_assets(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)):
        raise TypeError("assets must be a list or tuple")

    normalized = []
    for item in value:
        if not isinstance(item, str):
            raise TypeError("assets list items must be strings")
        normalized.append(item.strip().upper())

    return sorted(normalized)


def _normalize_canonical_value(value: Any, *, key: Optional[str] = None) -> Any:
    if isinstance(value, float):
        raise TypeError("floats are not supported in canonical_json")

    if value is None or isinstance(value, (bool, int, str)):
        return value

    if isinstance(value, dict):
        normalized_dict: Dict[str, Any] = {}
        for raw_key, raw_value in value.items():
            if not isinstance(raw_key, str):
                raise TypeError("dict keys must be strings")
            normalized_dict[raw_key] = _normalize_canonical_value(raw_value, key=raw_key)
        return normalized_dict

    if isinstance(value, (list, tuple)):
        if key == "assets":
            return _normalize_assets(value)
        return [_normalize_canonical_value(item) for item in value]

    raise TypeError(f"unsupported type for canonical_json: {type(value).__name__}")


def canonical_json(obj: Any) -> str:
    """
    Create a deterministic JSON representation of the provided object.
    """
    normalized = _normalize_canonical_value(obj)
    return json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def sha256_hex(text: str) -> str:
    """
    Return a SHA-256 hex digest for the provided text.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _normalize_strategy_config(strat_name: str, raw_config: Any) -> Dict[str, Any]:
    if raw_config is None:
        normalized: Dict[str, Any] = {}
    elif isinstance(raw_config, Mapping):
        normalized, unknown_keys = normalize_and_validate_strategy_params(strat_name, raw_config)

        if unknown_keys:
            logger.warning(
                "Unknown config keys: component=engine strategy=%s keys=%s",
                strat_name,
                ", ".join(unknown_keys),
            )
    else:
        logger.warning(
            "Invalid strategy config type: component=engine strategy=%s (expected mapping, got %s); using empty config",
            strat_name,
            type(raw_config).__name__,
        )
        normalized = {}

    return normalized


@dataclass
class EngineConfig:
    """
    Minimale Konfiguration für die Engine.
    """
    timeframe: str = "D1"
    lookback_days: int = 200
    market_type: str = "stock"
    data_source: str = "yahoo"


@dataclass(frozen=True)
class AnalysisRun:
    """Minimal analysis run representation.

    Args:
        analysis_run_id: Deterministic identifier for the analysis run.
        ingestion_run_id: Snapshot ingestion run reference.
        request_payload: Canonical request payload for the run.
        signals: Signals emitted during the run (with deterministic IDs).
    """

    analysis_run_id: str
    ingestion_run_id: str
    request_payload: Dict[str, Any]
    signals: List[Signal]


class BaseStrategy(Protocol):
    name: str

    def generate_signals(
        self,
        df,
        config: Dict[str, Any],
    ) -> List[Signal]:
        ...


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def compute_analysis_run_id(run_request_payload: Mapping[str, Any]) -> str:
    """Compute a deterministic analysis run ID.

    Args:
        run_request_payload: Request payload for the analysis run.

    Returns:
        Deterministic analysis run ID.
    """
    return sha256_hex(canonical_json(dict(run_request_payload)))


def _signal_identity_payload(signal: Mapping[str, Any]) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    for key in (
        "symbol",
        "strategy",
        "timestamp",
        "timeframe",
        "market_type",
        "data_source",
        "direction",
        "stage",
        "assets",
    ):
        if key in signal:
            payload[key] = signal[key]
    return payload


def compute_signal_id(signal: Mapping[str, Any]) -> str:
    """Compute a deterministic signal ID.

    Args:
        signal: Signal payload used to compute the ID.

    Returns:
        Deterministic signal ID.
    """
    return sha256_hex(canonical_json(_signal_identity_payload(signal)))


def add_signal_ids(signals: List[Signal]) -> List[Signal]:
    """Attach deterministic IDs to signals.

    Signals missing a timestamp are skipped with a warning.

    Args:
        signals: Signals to process.

    Returns:
        Signals with signal_id attached.
    """
    enriched_signals: List[Signal] = []
    for signal in signals:
        if not signal.get("timestamp"):
            logger.warning(
                "Skipping signal without timestamp for deterministic ID: component=engine symbol=%s strategy=%s",
                signal.get("symbol", "n/a"),
                signal.get("strategy", "n/a"),
            )
            continue
        signal_with_id = dict(signal)
        signal_with_id["signal_id"] = compute_signal_id(signal_with_id)
        enriched_signals.append(signal_with_id)
    return enriched_signals


def build_analysis_run(
    *,
    ingestion_run_id: str,
    run_request_payload: Mapping[str, Any],
    signals: List[Signal],
) -> AnalysisRun:
    """Build a minimal analysis run with deterministic IDs.

    Args:
        ingestion_run_id: Snapshot ingestion run reference.
        run_request_payload: Request payload for the analysis run.
        signals: Signals emitted during the run.

    Returns:
        AnalysisRun with deterministic IDs applied.
    """
    analysis_run_id = compute_analysis_run_id(run_request_payload)
    return AnalysisRun(
        analysis_run_id=analysis_run_id,
        ingestion_run_id=ingestion_run_id,
        request_payload=dict(run_request_payload),
        signals=add_signal_ids(signals),
    )


def run_watchlist_analysis(
    symbols: List[str],
    strategies: List[BaseStrategy],
    engine_config: EngineConfig,
    strategy_configs: Dict[str, Dict[str, Any]],
    signal_repo: SignalRepository,
    *,
    ingestion_run_id: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> List[Signal]:
    """
    Führt die Analyse über eine Symbol-Watchlist und eine Liste von Strategien aus.
    """
    if ingestion_run_id and db_path is None:
        raise ValueError("db_path is required when ingestion_run_id is provided")
    logger.info(
        "Engine run started: component=engine symbols=%d strategies=%d timeframe=%s lookback_days=%d market_type=%s ingestion_run_id=%s",
        len(symbols),
        len(strategies),
        engine_config.timeframe,
        engine_config.lookback_days,
        engine_config.market_type,
        ingestion_run_id or "n/a",
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
                "Loading data: component=engine symbol=%s market_type=%s lookback_days=%d timeframe=%s ingestion_run_id=%s",
                symbol,
                engine_config.market_type,
                engine_config.lookback_days,
                engine_config.timeframe,
                ingestion_run_id,
            )

            try:
                if ingestion_run_id:
                    df = load_ohlcv_snapshot(
                        ingestion_run_id=ingestion_run_id,
                        symbol=symbol,
                        timeframe=engine_config.timeframe,
                        db_path=db_path,
                    )
                else:
                    df = load_ohlcv(
                        symbol=symbol,
                        timeframe=engine_config.timeframe,
                        lookback_days=engine_config.lookback_days,
                        market_type=engine_config.market_type,
                    )
            except Exception:
                logger.error(
                    "Error loading data: component=engine symbol=%s timeframe=%s ingestion_run_id=%s",
                    symbol,
                    engine_config.timeframe,
                    ingestion_run_id or "n/a",
                    exc_info=True,
                )
                continue

            if df is None or getattr(df, "empty", False):
                logger.warning(
                    "Skipping symbol due to empty OHLCV data: component=engine symbol=%s timeframe=%s ingestion_run_id=%s",
                    symbol,
                    engine_config.timeframe,
                    ingestion_run_id or "n/a",
                )
                continue

            symbol_signals_count = 0

            for strategy in ordered_strategies:
                strat_name = getattr(strategy, "name", strategy.__class__.__name__)
                raw_config = strategy_configs_map.get(strat_name)
                try:
                    strat_config = _normalize_strategy_config(strat_name, raw_config)
                except Exception as exc:
                    logger.error(
                        "Invalid strategy config: component=engine strategy=%s error=%s",
                        strat_name,
                        exc,
                    )
                    continue

                logger.debug(
                    "Running strategy: component=engine strategy=%s symbol=%s timeframe=%s",
                    strat_name,
                    symbol,
                    engine_config.timeframe,
                )

                try:
                    signals = strategy.generate_signals(df, strat_config)
                except Exception:
                    logger.error(
                        "Error in strategy: component=engine strategy=%s symbol=%s timeframe=%s",
                        strat_name,
                        symbol,
                        engine_config.timeframe,
                        exc_info=True,
                    )
                    continue

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
