"""
Daten-Layer für die Cilly Trading Engine.
"""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import uuid
import warnings
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, Literal, Optional

import ccxt
import pandas as pd
import yfinance as yf

from cilly_trading.db import DEFAULT_DB_PATH, init_db
from cilly_trading.db.init_db import get_connection

logger = logging.getLogger(__name__)

warnings.filterwarnings(
    "ignore",
    category=FutureWarning,
    message=r".*YF\.download\(\) has changed argument auto_adjust default to True.*",
)

MarketType = Literal["stock", "crypto"]

REQUIRED_COLS: Final[tuple[str, ...]] = (
    "timestamp",
    "open",
    "high",
    "low",
    "close",
    "volume",
)


class SnapshotDataError(RuntimeError):
    """Raised when snapshot data is missing or invalid for analysis."""


class SnapshotIngestionError(ValueError):
    """Raised when local snapshot ingestion fails."""


@dataclass(frozen=True)
class SnapshotIngestionResult:
    """Result of a local snapshot ingestion run."""

    ingestion_run_id: str
    snapshot_id: str
    inserted_rows: int


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _load_local_snapshot_file(input_path: Path) -> pd.DataFrame:
    if not input_path.exists():
        logger.error("Snapshot input file missing: component=data path=%s", input_path)
        raise SnapshotIngestionError("snapshot_input_missing")

    suffix = input_path.suffix.lower()
    try:
        if suffix == ".csv":
            return pd.read_csv(input_path)
        if suffix == ".json":
            payload = json.loads(input_path.read_text(encoding="utf-8"))
            if isinstance(payload, dict) and "data" in payload:
                payload = payload["data"]
            if not isinstance(payload, list):
                raise SnapshotIngestionError("snapshot_json_invalid")
            return pd.DataFrame(payload)
    except SnapshotIngestionError:
        raise
    except Exception:
        logger.exception("Failed to read snapshot input: component=data path=%s", input_path)
        raise SnapshotIngestionError("snapshot_input_unreadable")

    logger.error("Unsupported snapshot format: component=data path=%s", input_path)
    raise SnapshotIngestionError("snapshot_input_unsupported")


def _validate_required_columns(df: pd.DataFrame) -> None:
    missing = [col for col in REQUIRED_COLS if col not in df.columns]
    if missing:
        logger.error(
            "Snapshot missing required columns: component=data missing=%s columns=%s",
            missing,
            list(df.columns),
        )
        raise SnapshotIngestionError("snapshot_missing_columns")


def _normalize_local_ohlcv_rows(
    df: pd.DataFrame,
    *,
    symbol: str,
    timeframe: str,
) -> pd.DataFrame:
    if df is None or df.empty:
        logger.error("Snapshot input empty: component=data symbol=%s", symbol)
        raise SnapshotIngestionError("snapshot_empty")

    _validate_required_columns(df)
    out = df[list(REQUIRED_COLS)].copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True, errors="coerce")
    if out["timestamp"].isna().any():
        logger.error("Snapshot contains invalid timestamps: component=data symbol=%s", symbol)
        raise SnapshotIngestionError("snapshot_invalid_timestamp")

    for col in ("open", "high", "low", "close", "volume"):
        out[col] = pd.to_numeric(out[col], errors="coerce")
    if out[["open", "high", "low", "close", "volume"]].isna().any().any():
        logger.error("Snapshot contains invalid numeric values: component=data symbol=%s", symbol)
        raise SnapshotIngestionError("snapshot_invalid_numeric")

    out = out.sort_values("timestamp").reset_index(drop=True)
    out["symbol"] = symbol
    out["timeframe"] = timeframe
    return out


def _compute_snapshot_id(
    df: pd.DataFrame,
    *,
    symbol: str,
    timeframe: str,
    source: str,
) -> str:
    timestamps_ms = (df["timestamp"].astype("int64") // 1_000_000).astype(int)
    rows = []
    for idx, row in df.iterrows():
        rows.append(
            {
                "timestamp": int(timestamps_ms.iloc[idx]),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row["volume"]),
            }
        )
    payload = {
        "symbol": symbol,
        "timeframe": timeframe,
        "source": source,
        "rows": rows,
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _snapshot_exists(conn: sqlite3.Connection, snapshot_id: str) -> bool:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT 1
        FROM ingestion_runs
        WHERE fingerprint_hash = ?
        LIMIT 1;
        """,
        (snapshot_id,),
    )
    return cur.fetchone() is not None


def _insert_ingestion_run(
    conn: sqlite3.Connection,
    *,
    ingestion_run_id: str,
    source: str,
    symbol: str,
    timeframe: str,
    snapshot_id: str,
    created_at: Optional[str] = None,
) -> None:
    cur = conn.cursor()
    if created_at is None:
        created_at = _utc_now().isoformat()
    cur.execute(
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
            json.dumps([symbol]),
            timeframe,
            snapshot_id,
        ),
    )


def _insert_snapshot_rows(
    conn: sqlite3.Connection,
    df: pd.DataFrame,
    *,
    ingestion_run_id: str,
) -> int:
    timestamps_ms = (df["timestamp"].astype("int64") // 1_000_000).astype(int)
    rows = []
    for idx, row in df.iterrows():
        rows.append(
            (
                ingestion_run_id,
                row["symbol"],
                row["timeframe"],
                int(timestamps_ms.iloc[idx]),
                float(row["open"]),
                float(row["high"]),
                float(row["low"]),
                float(row["close"]),
                float(row["volume"]),
            )
        )
    cur = conn.cursor()
    cur.executemany(
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
        rows,
    )
    return len(rows)


def ingest_local_snapshot(
    *,
    input_path: Path | str,
    symbol: str,
    timeframe: str,
    source: str = "local",
    db_path: Optional[Path] = None,
) -> SnapshotIngestionResult:
    """Ingest a local CSV/JSON OHLCV snapshot into SQLite.

    Args:
        input_path: Path to the CSV or JSON file.
        symbol: Symbol identifier for the snapshot.
        timeframe: Explicit timeframe label (e.g., "D1").
        source: Stable source label for determinism.
        db_path: Optional SQLite database path.

    Returns:
        SnapshotIngestionResult containing ingestion_run_id and snapshot_id.
    """
    if not timeframe or not isinstance(timeframe, str):
        logger.error("Snapshot timeframe missing: component=data symbol=%s", symbol)
        raise SnapshotIngestionError("snapshot_timeframe_missing")
    if not symbol or not isinstance(symbol, str):
        logger.error("Snapshot symbol missing: component=data")
        raise SnapshotIngestionError("snapshot_symbol_missing")

    if db_path is None:
        db_path = DEFAULT_DB_PATH

    init_db(db_path)
    input_path = Path(input_path)
    df = _load_local_snapshot_file(input_path)
    normalized = _normalize_local_ohlcv_rows(df, symbol=symbol, timeframe=timeframe)
    snapshot_id = _compute_snapshot_id(
        normalized,
        symbol=symbol,
        timeframe=timeframe,
        source=source,
    )

    ingestion_run_id = str(uuid.uuid4())
    conn = get_connection(db_path)
    try:
        snapshot_exists = _snapshot_exists(conn, snapshot_id)
        _insert_ingestion_run(
            conn,
            ingestion_run_id=ingestion_run_id,
            source=source,
            symbol=symbol,
            timeframe=timeframe,
            snapshot_id=snapshot_id,
        )
        inserted_rows = 0
        if not snapshot_exists:
            inserted_rows = _insert_snapshot_rows(
                conn,
                normalized,
                ingestion_run_id=ingestion_run_id,
            )
        conn.commit()
    except SnapshotIngestionError:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        logger.exception("Snapshot ingestion failed: component=data symbol=%s", symbol)
        raise SnapshotIngestionError("snapshot_ingestion_failed")
    finally:
        conn.close()

    return SnapshotIngestionResult(
        ingestion_run_id=ingestion_run_id,
        snapshot_id=snapshot_id,
        inserted_rows=inserted_rows,
    )


def ingest_local_snapshot_deterministic(
    *,
    input_path: Path | str,
    symbol: str,
    timeframe: str,
    source: str = "local",
    ingestion_run_id: str,
    created_at: str,
    db_path: Optional[Path] = None,
) -> SnapshotIngestionResult:
    """Ingest a local snapshot with deterministic identifiers.

    Args:
        input_path: Path to the CSV or JSON file.
        symbol: Symbol identifier for the snapshot.
        timeframe: Explicit timeframe label (e.g., "D1").
        source: Stable source label for determinism.
        ingestion_run_id: Deterministic ingestion run identifier.
        created_at: Deterministic ISO-8601 timestamp for the ingestion run.
        db_path: Optional SQLite database path.

    Returns:
        SnapshotIngestionResult containing ingestion_run_id and snapshot_id.
    """
    if not ingestion_run_id or not isinstance(ingestion_run_id, str):
        logger.error("Snapshot ingestion_run_id missing: component=data symbol=%s", symbol)
        raise SnapshotIngestionError("snapshot_ingestion_run_id_missing")
    if not created_at or not isinstance(created_at, str):
        logger.error("Snapshot created_at missing: component=data symbol=%s", symbol)
        raise SnapshotIngestionError("snapshot_created_at_missing")
    if not timeframe or not isinstance(timeframe, str):
        logger.error("Snapshot timeframe missing: component=data symbol=%s", symbol)
        raise SnapshotIngestionError("snapshot_timeframe_missing")
    if not symbol or not isinstance(symbol, str):
        logger.error("Snapshot symbol missing: component=data")
        raise SnapshotIngestionError("snapshot_symbol_missing")

    if db_path is None:
        db_path = DEFAULT_DB_PATH

    init_db(db_path)
    input_path = Path(input_path)
    df = _load_local_snapshot_file(input_path)
    normalized = _normalize_local_ohlcv_rows(df, symbol=symbol, timeframe=timeframe)
    snapshot_id = _compute_snapshot_id(
        normalized,
        symbol=symbol,
        timeframe=timeframe,
        source=source,
    )

    conn = get_connection(db_path)
    try:
        snapshot_exists = _snapshot_exists(conn, snapshot_id)
        _insert_ingestion_run(
            conn,
            ingestion_run_id=ingestion_run_id,
            source=source,
            symbol=symbol,
            timeframe=timeframe,
            snapshot_id=snapshot_id,
            created_at=created_at,
        )
        inserted_rows = 0
        if not snapshot_exists:
            inserted_rows = _insert_snapshot_rows(
                conn,
                normalized,
                ingestion_run_id=ingestion_run_id,
            )
        conn.commit()
    except SnapshotIngestionError:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        logger.exception("Snapshot ingestion failed: component=data symbol=%s", symbol)
        raise SnapshotIngestionError("snapshot_ingestion_failed")
    finally:
        conn.close()

    return SnapshotIngestionResult(
        ingestion_run_id=ingestion_run_id,
        snapshot_id=snapshot_id,
        inserted_rows=inserted_rows,
    )


def _empty_ohlcv() -> pd.DataFrame:
    return pd.DataFrame(columns=list(REQUIRED_COLS))


def _validate_and_normalize_ohlcv(
    df: pd.DataFrame,
    *,
    symbol: str,
    source: str,
) -> pd.DataFrame:
    if df is None or df.empty:
        logger.warning(
            "No data (empty df): component=data source=%s symbol=%s",
            source,
            symbol,
        )
        return _empty_ohlcv()

    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        logger.warning(
            "Invalid OHLCV schema: component=data source=%s symbol=%s missing=%s columns=%s",
            source,
            symbol,
            missing,
            list(df.columns),
        )
        return _empty_ohlcv()

    out = df[list(REQUIRED_COLS)].copy()

    try:
        out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True, errors="coerce")
    except Exception:
        logger.exception(
            "Failed to parse timestamp: component=data source=%s symbol=%s",
            source,
            symbol,
        )
        return _empty_ohlcv()

    out = out.dropna(subset=["timestamp"])
    if out.empty:
        logger.warning(
            "All timestamps invalid: component=data source=%s symbol=%s",
            source,
            symbol,
        )
        return _empty_ohlcv()

    for col in ("open", "high", "low", "close", "volume"):
        out[col] = pd.to_numeric(out[col], errors="coerce")

    mask_all_nan = out[["open", "high", "low", "close"]].isna().all(axis=1)
    out = out.loc[~mask_all_nan].copy()
    if out.empty:
        logger.warning(
            "No valid OHLC rows: component=data source=%s symbol=%s",
            source,
            symbol,
        )
        return _empty_ohlcv()

    out = out.sort_values("timestamp").reset_index(drop=True)
    return out


def load_ohlcv_snapshot(
    *,
    ingestion_run_id: str,
    symbol: str,
    timeframe: str,
    db_path: Optional[Path] = None,
) -> pd.DataFrame:
    if timeframe.upper() != "D1":
        raise ValueError(f"Unsupported timeframe for MVP: {timeframe}")

    if db_path is None:
        db_path = DEFAULT_DB_PATH

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            ts,
            open,
            high,
            low,
            close,
            volume
        FROM ohlcv_snapshots
        WHERE ingestion_run_id = ?
          AND symbol = ?
          AND timeframe = ?
        ORDER BY ts ASC;
        """,
        (ingestion_run_id, symbol, timeframe),
    )
    rows = cur.fetchall()
    conn.close()

    if not rows:
        logger.warning(
            "No snapshot data: component=data ingestion_run_id=%s symbol=%s timeframe=%s",
            ingestion_run_id,
            symbol,
            timeframe,
        )
        raise SnapshotDataError(
            f"snapshot_missing ingestion_run_id={ingestion_run_id} symbol={symbol} timeframe={timeframe}"
        )

    df = pd.DataFrame(
        rows,
        columns=["ts", "open", "high", "low", "close", "volume"],
    )
    df = df.rename(columns={"ts": "timestamp"})
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True, errors="coerce")

    df = _validate_and_normalize_ohlcv(df, symbol=symbol, source="snapshot")
    if df.empty:
        raise SnapshotDataError(
            f"snapshot_invalid ingestion_run_id={ingestion_run_id} symbol={symbol} timeframe={timeframe}"
        )
    return df


def load_snapshot_metadata(
    *,
    ingestion_run_id: str,
    db_path: Optional[Path] = None,
) -> dict[str, Any]:
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            ingestion_run_id,
            created_at,
            source,
            fingerprint_hash
        FROM ingestion_runs
        WHERE ingestion_run_id = ?
        LIMIT 1;
        """,
        (ingestion_run_id,),
    )
    row = cur.fetchone()
    conn.close()

    if row is None:
        raise SnapshotDataError(f"snapshot_metadata_missing ingestion_run_id={ingestion_run_id}")

    metadata: dict[str, Any] = {
        "snapshot_id": row["ingestion_run_id"],
        "provider": "internal",
        "source": row["source"],
        "created_at_utc": row["created_at"],
        "schema_version": "1",
    }
    fingerprint_hash = row["fingerprint_hash"]
    if fingerprint_hash:
        metadata["payload_checksum"] = fingerprint_hash
        metadata["deterministic_snapshot_id"] = fingerprint_hash
    return metadata


def load_ohlcv(
    symbol: str,
    timeframe: str,
    lookback_days: int,
    market_type: MarketType = "stock",
) -> pd.DataFrame:
    if timeframe.upper() != "D1":
        raise ValueError(f"Unsupported timeframe for MVP: {timeframe}")

    if lookback_days <= 0:
        raise ValueError(f"lookback_days must be > 0, got: {lookback_days}")

    end = _utc_now()
    start = end - timedelta(days=lookback_days * 2)

    try:
        if market_type == "stock":
            raw = _load_stock_yahoo(symbol, start, end)
            return _validate_and_normalize_ohlcv(raw, symbol=symbol, source="yfinance")

        if market_type == "crypto":
            raw = _load_crypto_binance(symbol, lookback_days)
            return _validate_and_normalize_ohlcv(raw, symbol=symbol, source="ccxt/binance")

        raise ValueError(f"Unsupported market_type: {market_type}")

    except Exception:
        logger.exception(
            "Failed to load OHLCV: component=data symbol=%s timeframe=%s lookback_days=%s market_type=%s",
            symbol,
            timeframe,
            lookback_days,
            market_type,
        )
        return _empty_ohlcv()


def _load_stock_yahoo(
    symbol: str,
    start: datetime,
    end: datetime,
) -> pd.DataFrame:
    try:
        df = yf.download(
            symbol,
            start=start.date(),
            end=end.date(),
            interval="1d",
            progress=False,
        )
    except Exception:
        logger.exception(
            "yfinance download failed: component=data symbol=%s",
            symbol,
        )
        return _empty_ohlcv()

    if df is None or df.empty:
        logger.warning(
            "No data returned from Yahoo Finance: component=data symbol=%s",
            symbol,
        )
        return _empty_ohlcv()

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.reset_index().rename(
        columns={
            "Date": "timestamp",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        }
    )

    if not all(c in df.columns for c in REQUIRED_COLS):
        logger.warning(
            "Unexpected Yahoo Finance schema: component=data symbol=%s columns=%s",
            symbol,
            list(df.columns),
        )
        return _empty_ohlcv()

    df = df[list(REQUIRED_COLS)].copy()

    try:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    except Exception:
        logger.exception(
            "Failed to convert Yahoo timestamp: component=data symbol=%s",
            symbol,
        )
        return _empty_ohlcv()

    return df


def _load_crypto_binance(
    symbol: str,
    lookback_days: int,
) -> pd.DataFrame:
    try:
        exchange = ccxt.binance()
    except Exception:
        logger.exception(
            "Failed to initialize ccxt binance exchange: component=data symbol=%s",
            symbol,
        )
        return _empty_ohlcv()

    since = int((_utc_now() - timedelta(days=lookback_days * 2)).timestamp() * 1000)

    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe="1d", since=since)
    except Exception:
        logger.exception(
            "ccxt fetch_ohlcv failed: component=data symbol=%s",
            symbol,
        )
        return _empty_ohlcv()

    if not ohlcv:
        logger.warning(
            "No data returned from Binance: component=data symbol=%s",
            symbol,
        )
        return _empty_ohlcv()

    df = pd.DataFrame(
        ohlcv,
        columns=["timestamp", "open", "high", "low", "close", "volume"],
    )

    try:
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True, errors="coerce")
    except Exception:
        logger.exception(
            "Failed to convert Binance timestamps: component=data symbol=%s",
            symbol,
        )
        return _empty_ohlcv()

    return df
