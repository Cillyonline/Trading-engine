"""
Core-Engine der Cilly Trading Engine.

- Definiert das Strategy-Interface (BaseStrategy)
- Definiert EngineConfig
- Implementiert `run_watchlist_analysis`
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol

import pandas as pd

from cilly_trading.engine.data import (
    SnapshotDataError,
    load_ohlcv,
    load_ohlcv_snapshot,
    load_snapshot_metadata,
)
from cilly_trading.engine.lineage import LineageContext, LineageMissingError
from cilly_trading.engine.logging import emit_structured_engine_log
from cilly_trading.engine.reasons import generate_reasons_for_signal
from cilly_trading.engine.strategy_params import normalize_and_validate_strategy_params
from cilly_trading.models import (
    Signal,
    canonical_json,
    compute_signal_id,
    sha256_hex,
    validate_signal_required_fields,
)
from cilly_trading.repositories import SignalRepository
from cilly_trading.repositories.lineage_repository import SqliteLineageRepository
from cilly_trading.config.external_data import EXTERNAL_DATA_ENABLED

logger = logging.getLogger(__name__)


class ReasonGenerationError(RuntimeError):
    """Raised when deterministic reason generation fails."""


class ExternalDataGateClosedError(RuntimeError):
    """Raised when external data usage is attempted while the gate is closed."""


def _require_external_data_enabled(engine_config: "EngineConfig") -> None:
    """Require external data usage to be explicitly enabled.

    Args:
        engine_config: Engine configuration containing the external data flag.

    Raises:
        ExternalDataGateClosedError: If external data usage is disabled.
    """
    if engine_config.external_data_enabled:
        return
    logger.error(
        "External data gate closed: external_data_enabled=%s; engine execution blocked.",
        engine_config.external_data_enabled,
    )
    raise ExternalDataGateClosedError(
        "external_data_enabled is False; external data usage is disabled"
    )


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
    external_data_enabled: bool = EXTERNAL_DATA_ENABLED


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
        df: "pd.DataFrame",
        config: Dict[str, Any],
    ) -> List[Signal]:
        ...


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_timestamp_to_utc(value: Any) -> Optional[str]:
    timestamp = pd.to_datetime(value, utc=True, errors="coerce")
    if pd.isna(timestamp):
        return None
    return timestamp.isoformat()


def _derive_timestamp_from_df(df: Any) -> Optional[str]:
    index = getattr(df, "index", None)
    if index is not None and len(index) > 0:
        if isinstance(index, pd.DatetimeIndex) or pd.api.types.is_datetime64_any_dtype(index):
            derived = _normalize_timestamp_to_utc(index[-1])
            if derived is not None:
                return derived

    if getattr(df, "columns", None) is not None and "timestamp" in df.columns:
        try:
            return _normalize_timestamp_to_utc(df["timestamp"].iloc[-1])
        except (IndexError, KeyError, AttributeError, TypeError, ValueError):
            logger.warning(
                "Failed to derive timestamp from OHLCV column: component=engine",
                exc_info=True,
            )
            return None

    return None


def compute_analysis_run_id(run_request_payload: Mapping[str, Any]) -> str:
    """Compute a deterministic analysis run ID.

    Args:
        run_request_payload: Request payload for the analysis run.

    Returns:
        Deterministic analysis run ID.
    """
    return sha256_hex(canonical_json(dict(run_request_payload)))



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
    snapshot_id: Optional[str] = None,
    db_path: Optional[Path] = None,
    run_id: Optional[str] = None,
    audit_dir: Optional[Path] = None,
    snapshot_only: bool = False,
    lineage_repo: Optional[SqliteLineageRepository] = None,
    symbol_failures: Optional[List[Dict[str, str]]] = None,
    isolate_symbol_failures: bool = False,
) -> List[Signal]:
    """
    Führt die Analyse über eine Symbol-Watchlist und eine Liste von Strategien aus.

    Semantik:
    - ingestion_run_id und snapshot_id sind Pflicht (Lineage-Kontext)
    - snapshot_only=True -> db_path muss gesetzt sein (Snapshot ist Pflicht)
    - db_path gesetzt -> Snapshot wird geladen, sonst externe Daten
    """
    if ingestion_run_id is None or not str(ingestion_run_id).strip():
        raise LineageMissingError("ingestion_run_id is required for analysis lineage")
    if snapshot_only and db_path is None:
        raise ValueError("db_path is required when snapshot_only is enabled")

    resolved_snapshot_id = snapshot_id
    if resolved_snapshot_id is None or not str(resolved_snapshot_id).strip():
        if db_path is None:
            raise LineageMissingError("snapshot_id is required for analysis lineage")
        try:
            metadata = load_snapshot_metadata(ingestion_run_id=ingestion_run_id, db_path=db_path)
        except Exception as exc:
            raise LineageMissingError("snapshot_id is required for analysis lineage") from exc
        resolved_snapshot_id = (
            metadata.get("deterministic_snapshot_id")
            or metadata.get("payload_checksum")
            or metadata.get("snapshot_id")
        )

    if resolved_snapshot_id is None or not str(resolved_snapshot_id).strip():
        raise LineageMissingError("snapshot_id is required for analysis lineage")

    ordered_symbols = sorted(symbols)
    ordered_strategy_names = sorted(
        getattr(strategy, "name", strategy.__class__.__name__) for strategy in strategies
    )
    analysis_run_payload = {
        "symbols": ordered_symbols,
        "strategies": ordered_strategy_names,
        "engine_config": {
            "timeframe": engine_config.timeframe,
            "lookback_days": engine_config.lookback_days,
            "market_type": engine_config.market_type,
            "data_source": engine_config.data_source,
        },
        "ingestion_run_id": str(ingestion_run_id),
        "snapshot_id": str(resolved_snapshot_id),
        "snapshot_only": snapshot_only,
    }
    analysis_run_id = compute_analysis_run_id(analysis_run_payload)
    lineage_ctx = LineageContext(
        snapshot_id=str(resolved_snapshot_id),
        ingestion_run_id=str(ingestion_run_id),
        analysis_run_id=analysis_run_id,
    )

    use_snapshot_data = snapshot_only or db_path is not None
    if not use_snapshot_data:
        _require_external_data_enabled(engine_config)

    if snapshot_only:
        _persist_phase6_audit(
            ingestion_run_id=ingestion_run_id,
            db_path=db_path,
            run_id=run_id,
            audit_dir=audit_dir,
        )

    logger.info(
        "Engine run started: component=engine symbols=%d strategies=%d timeframe=%s lookback_days=%d market_type=%s ingestion_run_id=%s snapshot_id=%s",
        len(symbols),
        len(strategies),
        engine_config.timeframe,
        engine_config.lookback_days,
        engine_config.market_type,
        ingestion_run_id or "n/a",
        resolved_snapshot_id or "n/a",
    )
    emit_structured_engine_log(
        "analysis_run.started",
        payload={
            "analysis_run_id": analysis_run_id,
            "ingestion_run_id": str(ingestion_run_id),
            "snapshot_id": str(resolved_snapshot_id),
            "snapshot_only": snapshot_only,
            "symbols": ordered_symbols,
            "strategies": ordered_strategy_names,
            "timeframe": engine_config.timeframe,
            "market_type": engine_config.market_type,
            "data_source": engine_config.data_source,
        },
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
                "Loading data: component=engine symbol=%s market_type=%s lookback_days=%d timeframe=%s ingestion_run_id=%s snapshot_only=%s",
                symbol,
                engine_config.market_type,
                engine_config.lookback_days,
                engine_config.timeframe,
                ingestion_run_id or "n/a",
                snapshot_only,
            )

            if use_snapshot_data:
                if db_path is None:
                    raise ValueError("db_path is required for snapshot-backed analysis")
                try:
                    df = load_ohlcv_snapshot(
                        ingestion_run_id=ingestion_run_id,
                        symbol=symbol,
                        timeframe=engine_config.timeframe,
                        db_path=db_path,
                    )
                except SnapshotDataError:
                    if snapshot_only and not isolate_symbol_failures:
                        raise
                    if symbol_failures is not None:
                        symbol_failures.append(
                            {
                                "symbol": symbol,
                                "code": "snapshot_data_invalid",
                                "detail": "snapshot data unavailable or invalid for symbol",
                            }
                        )
                    logger.warning(
                        "Skipping symbol due to snapshot data error: component=engine symbol=%s timeframe=%s ingestion_run_id=%s",
                        symbol,
                        engine_config.timeframe,
                        ingestion_run_id or "n/a",
                    )
                    continue
                if df is None or getattr(df, "empty", False):
                    raise SnapshotDataError(
                        f"snapshot_invalid ingestion_run_id={ingestion_run_id} symbol={symbol} timeframe={engine_config.timeframe}"
                    )
            else:
                try:
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

            derived_timestamp = _derive_timestamp_from_df(df)
            symbol_signals_count = 0

            for strategy in ordered_strategies:
                strat_name = getattr(strategy, "name", strategy.__class__.__name__)
                raw_config = strategy_configs_map.get(strat_name)
                try:
                    strat_config = _normalize_strategy_config(strat_name, raw_config)
                except (ValueError, KeyError, TypeError) as exc:
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

                processed_signals: List[Signal] = []
                for s in signals:
                    try:
                        s.setdefault("symbol", symbol)
                        s.setdefault("strategy", strat_name)
                        if not s.get("timestamp"):
                            if derived_timestamp is None:
                                logger.warning(
                                    "Skipping signal without deterministic timestamp: component=engine strategy=%s symbol=%s timeframe=%s",
                                    strat_name,
                                    symbol,
                                    engine_config.timeframe,
                                )
                                continue
                            s["timestamp"] = derived_timestamp
                        s.setdefault("timeframe", engine_config.timeframe)
                        s.setdefault("market_type", engine_config.market_type)
                        s.setdefault("data_source", engine_config.data_source)
                        s.setdefault("direction", "long")

                        existing_analysis_run_id = s.get("analysis_run_id")
                        if (
                            existing_analysis_run_id
                            and str(existing_analysis_run_id) != lineage_ctx.analysis_run_id
                        ):
                            raise LineageMissingError(
                                "analysis_run_id mismatch for lineage context"
                            )
                        existing_snapshot_id = s.get("snapshot_id")
                        if (
                            existing_snapshot_id
                            and str(existing_snapshot_id) != lineage_ctx.snapshot_id
                        ):
                            raise LineageMissingError(
                                "snapshot_id mismatch for lineage context"
                            )
                        existing_ingestion_run_id = s.get("ingestion_run_id")
                        if (
                            existing_ingestion_run_id
                            and str(existing_ingestion_run_id) != lineage_ctx.ingestion_run_id
                        ):
                            raise LineageMissingError(
                                "ingestion_run_id mismatch for lineage context"
                            )
                        s["analysis_run_id"] = lineage_ctx.analysis_run_id
                        s["snapshot_id"] = lineage_ctx.snapshot_id
                        s["ingestion_run_id"] = lineage_ctx.ingestion_run_id
                        validate_signal_required_fields(s)
                    except LineageMissingError:
                        raise
                    except ValueError as exc:
                        logger.warning(
                            "Dropping signal with missing required fields: component=engine strategy=%s symbol=%s reason=%s",
                            strat_name,
                            symbol,
                            exc,
                        )
                        continue
                    except (AttributeError, TypeError, KeyError, ValueError):
                        logger.error(
                            "Invalid signal object from strategy: component=engine strategy=%s symbol=%s timeframe=%s (skipping signal)",
                            strat_name,
                            symbol,
                            engine_config.timeframe,
                            exc_info=True,
                        )
                        continue

                    try:
                        s["signal_id"] = compute_signal_id(s)
                        reasons = generate_reasons_for_signal(
                            signal=s,
                            df=df,
                            strat_config=strat_config,
                        )
                        if not reasons:
                            raise ReasonGenerationError("Reason generation returned empty reasons list")
                        s["reasons"] = reasons
                    except (ValueError, KeyError, TypeError, AttributeError) as exc:
                        logger.error(
                            "Reason generation failed: component=engine strategy=%s symbol=%s timeframe=%s",
                            strat_name,
                            symbol,
                            engine_config.timeframe,
                            exc_info=True,
                        )
                        raise ReasonGenerationError("Reason generation failed for signal") from exc

                    emit_structured_engine_log(
                        "signal.generated",
                        payload={
                            "analysis_run_id": lineage_ctx.analysis_run_id,
                            "signal_id": s["signal_id"],
                            "symbol": str(s.get("symbol", "")),
                            "strategy": str(s.get("strategy", "")),
                            "timeframe": str(s.get("timeframe", "")),
                            "direction": str(s.get("direction", "")),
                        },
                    )
                    processed_signals.append(s)

                all_signals.extend(processed_signals)
                symbol_signals_count += len(processed_signals)

            logger.info(
                "Symbol analysis done: component=engine symbol=%s timeframe=%s signals=%d",
                symbol,
                engine_config.timeframe,
                symbol_signals_count,
            )

        except SnapshotDataError:
            if isolate_symbol_failures:
                if symbol_failures is not None:
                    symbol_failures.append(
                        {
                            "symbol": symbol,
                            "code": "snapshot_data_invalid",
                            "detail": "snapshot data unavailable or invalid for symbol",
                        }
                    )
                logger.warning(
                    "Snapshot data error isolated at symbol level: component=engine symbol=%s timeframe=%s",
                    symbol,
                    engine_config.timeframe,
                )
                continue
            logger.error(
                "Snapshot data error while processing symbol: component=engine symbol=%s timeframe=%s",
                symbol,
                engine_config.timeframe,
                exc_info=True,
            )
            raise
        except LineageMissingError:
            raise
        except ReasonGenerationError:
            if isolate_symbol_failures:
                if symbol_failures is not None:
                    symbol_failures.append(
                        {
                            "symbol": symbol,
                            "code": "reason_generation_failed",
                            "detail": "signal reason generation failed for symbol",
                        }
                    )
                logger.warning(
                    "Reason generation failure isolated at symbol level: component=engine symbol=%s timeframe=%s",
                    symbol,
                    engine_config.timeframe,
                )
                continue
            raise
        except Exception:
            if symbol_failures is not None:
                symbol_failures.append(
                    {
                        "symbol": symbol,
                        "code": "symbol_analysis_failed",
                        "detail": "unexpected symbol analysis failure",
                    }
                )
            logger.error(
                "Unexpected error while processing symbol: component=engine symbol=%s timeframe=%s",
                symbol,
                engine_config.timeframe,
                exc_info=True,
            )
            continue

    if lineage_repo is None:
        lineage_repo = SqliteLineageRepository(db_path=db_path)
    lineage_repo.save_lineage(lineage_ctx)

    if all_signals:
        logger.info(
            "Persisting signals: component=engine signals_total=%d",
            len(all_signals),
        )
        completion_status = "signals_persisted"
        try:
            signal_repo.save_signals(all_signals)
        except Exception:
            logger.error(
                "Error persisting signals: component=engine signals_total=%d",
                len(all_signals),
                exc_info=True,
            )
            completion_status = "signal_persistence_failed"
        logger.info(
            "Engine run completed: component=engine signals_total=%d",
            len(all_signals),
        )
        emit_structured_engine_log(
            "analysis_run.completed",
            payload={
                "analysis_run_id": analysis_run_id,
                "signals_total": len(all_signals),
                "status": completion_status,
            },
        )
    else:
        logger.info("Engine run completed: component=engine signals_total=0")
        emit_structured_engine_log(
            "analysis_run.completed",
            payload={
                "analysis_run_id": analysis_run_id,
                "signals_total": 0,
                "status": "no_signals",
            },
        )

    return all_signals


def _persist_phase6_audit(
    *,
    ingestion_run_id: str | None,
    db_path: Optional[Path],
    run_id: Optional[str],
    audit_dir: Optional[Path],
) -> None:
    if ingestion_run_id is None:
        raise ValueError("snapshot_only requires ingestion_run_id")

    if db_path is None:
        raise ValueError("db_path is required when ingestion_run_id is provided")

    snapshot_metadata = load_snapshot_metadata(
        ingestion_run_id=ingestion_run_id,
        db_path=db_path,
    )

    run_identifier = run_id or str(uuid.uuid4())
    base_dir = audit_dir or Path("runs/phase6")
    run_path = base_dir / run_identifier
    run_path.mkdir(parents=True, exist_ok=True)

    payload: Dict[str, Any] = {
        "run_id": run_identifier,
        "snapshot_id": ingestion_run_id,
        "snapshot_metadata": snapshot_metadata,
    }
    engine_version = os.getenv("CILLY_ENGINE_VERSION")
    if engine_version:
        payload["engine_version"] = engine_version

    audit_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    audit_path = run_path / "audit.json"
    audit_path.write_text(audit_json, encoding="utf-8")
