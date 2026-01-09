"""
Daten-Layer für die Cilly Trading Engine.
"""

from __future__ import annotations

import logging
import sqlite3
import warnings
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Final, Literal, Optional

import ccxt
import pandas as pd
import yfinance as yf

from cilly_trading.db import DEFAULT_DB_PATH

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


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


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
        return _empty_ohlcv()

    df = pd.DataFrame(
        rows,
        columns=["ts", "open", "high", "low", "close", "volume"],
    )
    df = df.rename(columns={"ts": "timestamp"})
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True, errors="coerce")

    return _validate_and_normalize_ohlcv(df, symbol=symbol, source="snapshot")


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
