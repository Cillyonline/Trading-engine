from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional

from cilly_trading.db import init_db
from cilly_trading.engine.core import EngineConfig, add_signal_ids, compute_analysis_run_id, run_watchlist_analysis
from cilly_trading.repositories.signals_sqlite import SqliteSignalRepository
from cilly_trading.strategies.rsi2 import Rsi2Strategy

INGESTION_RUN_ID = "golden-master-ingestion-0001"


def stable_json_dumps(payload: Any) -> str:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _insert_ingestion_run(
    db_path: Path,
    ingestion_run_id: str,
    *,
    symbols: list[str],
    timeframe: str = "D1",
    source: str = "golden_master",
    created_at: str = "2025-01-01T00:00:00+00:00",
) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        INSERT INTO ingestion_runs (
            ingestion_run_id,
            created_at,
            source,
            symbols_json,
            timeframe,
            fingerprint_hash
        )
        VALUES (?, ?, ?, ?, ?, ?);
        """,
        (
            ingestion_run_id,
            created_at,
            source,
            json.dumps(symbols, separators=(",", ":"), ensure_ascii=False),
            timeframe,
            None,
        ),
    )
    conn.commit()
    conn.close()


def _insert_snapshot_rows(
    db_path: Path,
    ingestion_run_id: str,
    symbol: str,
    timeframe: str,
    rows: list[tuple[int, float, float, float, float, float]],
) -> None:
    conn = sqlite3.connect(db_path)
    conn.executemany(
        """
        INSERT INTO ohlcv_snapshots (
            ingestion_run_id,
            symbol,
            timeframe,
            ts,
            open,
            high,
            low,
            close,
            volume
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        [
            (
                ingestion_run_id,
                symbol,
                timeframe,
                ts,
                open_,
                high,
                low,
                close,
                volume,
            )
            for ts, open_, high, low, close, volume in rows
        ],
    )
    conn.commit()
    conn.close()


def prepare_snapshot_db(db_path: Path) -> None:
    init_db(db_path)
    _insert_ingestion_run(db_path, INGESTION_RUN_ID, symbols=["AAPL"], timeframe="D1")
    rows = [
        (1735689600000, 102.0, 103.0, 100.0, 100.0, 1000.0),
        (1735776000000, 100.0, 101.0, 90.0, 90.0, 1000.0),
        (1735862400000, 90.0, 91.0, 80.0, 80.0, 1000.0),
        (1735948800000, 80.0, 81.0, 70.0, 70.0, 1000.0),
    ]
    _insert_snapshot_rows(db_path, INGESTION_RUN_ID, "AAPL", "D1", rows)


def build_run_payload(ingestion_run_id: str) -> Dict[str, Any]:
    return {
        "ingestion_run_id": ingestion_run_id,
        "symbol": "AAPL",
        "strategy": "RSI2",
        "market_type": "stock",
        "lookback_days": 200,
    }


def _load_schema_version() -> str:
    schema_path = Path(__file__).resolve().parents[2] / "schemas" / "signal-output.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    version_enum = schema["properties"]["schema_version"]["enum"]
    if not isinstance(version_enum, list) or not version_enum:
        raise ValueError("schema_version enum must contain at least one version")
    return str(version_enum[0])


def run_fixed_analysis(db_path: Path, *, schema_version: Optional[str] = None) -> Dict[str, Any]:
    resolved_schema_version = schema_version or _load_schema_version()
    signal_repo = SqliteSignalRepository(db_path=db_path)
    engine_config = EngineConfig(
        timeframe="D1",
        lookback_days=200,
        market_type="stock",
        data_source="yahoo",
    )
    strategy = Rsi2Strategy()
    strategy_configs = {"RSI2": {}}

    signals = run_watchlist_analysis(
        symbols=["AAPL"],
        strategies=[strategy],
        engine_config=engine_config,
        strategy_configs=strategy_configs,
        signal_repo=signal_repo,
        ingestion_run_id=INGESTION_RUN_ID,
        db_path=db_path,
        snapshot_only=True,
    )

    filtered_signals = [
        signal
        for signal in signals
        if signal.get("symbol") == "AAPL" and signal.get("strategy") == "RSI2"
    ]
    enriched_signals = add_signal_ids(filtered_signals)
    run_request_payload = build_run_payload(INGESTION_RUN_ID)
    analysis_run_id = compute_analysis_run_id(run_request_payload)

    return {
        "schema_version": resolved_schema_version,
        "analysis_run_id": analysis_run_id,
        "ingestion_run_id": INGESTION_RUN_ID,
        "symbol": "AAPL",
        "strategy": "RSI2",
        "signals": enriched_signals,
    }


def build_canonical_output_bytes(db_path: Path, *, schema_version: Optional[str] = None) -> bytes:
    response_payload = run_fixed_analysis(db_path, schema_version=schema_version)
    output_json = stable_json_dumps(response_payload)
    return output_json.encode("utf-8")
