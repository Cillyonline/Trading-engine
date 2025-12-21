"""
Daten-Layer für die Cilly Trading Engine.

Stellt die Funktion `load_ohlcv` bereit, die OHLCV-Daten für
Aktien (über Yahoo Finance) und Krypto (über Binance via CCXT) lädt.
"""

from __future__ import annotations

import logging
import warnings
from datetime import datetime, timedelta, timezone
from typing import Final, Literal

import ccxt
import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

# yfinance FutureWarning (auto_adjust default) gezielt ausblenden (Noise, kein MVP-Value)
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
    """
    MVP-konform: leeres DataFrame signalisiert "no data" oder Provider-Fehler.
    Die Engine darf dadurch niemals crashen.
    """
    return pd.DataFrame(columns=list(REQUIRED_COLS))


def _validate_and_normalize_ohlcv(
    df: pd.DataFrame,
    *,
    symbol: str,
    source: str,
) -> pd.DataFrame:
    """
    Validiert und normalisiert ein OHLCV-DataFrame auf das Canonical-Schema.

    Erwartet Spalten:
    ["timestamp", "open", "high", "low", "close", "volume"]

    Gibt bei Ungültigkeit immer ein leeres DataFrame zurück.
    """
    if df is None or df.empty:
        logger.warning("No data (empty df) from %s for symbol=%s", source, symbol)
        return _empty_ohlcv()

    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        logger.warning(
            "Invalid OHLCV schema from %s for symbol=%s (missing=%s, columns=%s)",
            source,
            symbol,
            missing,
            list(df.columns),
        )
        return _empty_ohlcv()

    out = df[list(REQUIRED_COLS)].copy()

    # timestamp -> datetime UTC
    try:
        out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True, errors="coerce")
    except Exception:
        logger.exception("Failed to parse timestamp from %s for symbol=%s", source, symbol)
        return _empty_ohlcv()

    out = out.dropna(subset=["timestamp"])
    if out.empty:
        logger.warning("All timestamps invalid from %s for symbol=%s", source, symbol)
        return _empty_ohlcv()

    # OHLCV numerisch machen
    for col in ("open", "high", "low", "close", "volume"):
        out[col] = pd.to_numeric(out[col], errors="coerce")

    # Zeilen verwerfen, bei denen OHLC komplett NaN sind
    mask_all_nan = out[["open", "high", "low", "close"]].isna().all(axis=1)
    out = out.loc[~mask_all_nan].copy()
    if out.empty:
        logger.warning("No valid OHLC rows from %s for symbol=%s", source, symbol)
        return _empty_ohlcv()

    out = out.sort_values("timestamp").reset_index(drop=True)
    return out


def load_ohlcv(
    symbol: str,
    timeframe: str,
    lookback_days: int,
    market_type: MarketType = "stock",
) -> pd.DataFrame:
    """
    Lädt OHLCV-Daten für ein Symbol.

    Bei Provider-Fehlern oder No-Data:
    - Fehler wird geloggt
    - leeres DataFrame wird zurückgegeben
    - Engine darf nicht crashen
    """
    if timeframe.upper() == "D1":
        yf_interval = "1d"
        ccxt_timeframe = "1d"
    else:
        # MVP: nur Tagesdaten offiziell unterstützt
        raise ValueError(f"Unsupported timeframe for MVP: {timeframe}")

    if lookback_days <= 0:
        raise ValueError(f"lookback_days must be > 0, got: {lookback_days}")

    end = _utc_now()
    start = end - timedelta(days=lookback_days * 2)

    try:
        if market_type == "stock":
            raw = _load_stock_yahoo(symbol, start, end, yf_interval)
            return _validate_and_normalize_ohlcv(raw, symbol=symbol, source="yfinance")

        if market_type == "crypto":
            raw = _load_crypto_binance(symbol, lookback_days, ccxt_timeframe)
            return _validate_and_normalize_ohlcv(raw, symbol=symbol, source="ccxt/binance")

        raise ValueError(f"Unsupported market_type: {market_type}")

    except Exception:
        logger.exception(
            "Failed to load OHLCV (symbol=%s, timeframe=%s, lookback_days=%s, market_type=%s)",
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
    interval: str,
) -> pd.DataFrame:
    """
    Lädt OHLCV-Daten für Aktien über Yahoo Finance.
    """
    try:
        df = yf.download(
            symbol,
            start=start.date(),
            end=end.date(),
            interval=interval,
            progress=False,
        )
    except Exception:
        logger.exception("yfinance download failed for symbol=%s", symbol)
        return _empty_ohlcv()

    if df is None or df.empty:
        logger.warning("No data returned from Yahoo Finance for symbol=%s", symbol)
        return _empty_ohlcv()

    # yfinance kann MultiIndex-Spalten liefern (Price, Ticker)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    rename_map = {
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume",
        "Adj Close": "adj_close",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    df = df.reset_index()

    if "Date" in df.columns:
        df = df.rename(columns={"Date": "timestamp"})
    elif "Datetime" in df.columns:
        df = df.rename(columns={"Datetime": "timestamp"})
    elif "index" in df.columns:
        df = df.rename(columns={"index": "timestamp"})

    cols = ["timestamp", "open", "high", "low", "close", "volume"]
    if not all(c in df.columns for c in cols):
        logger.warning(
            "Unexpected Yahoo Finance schema for symbol=%s (columns=%s)",
            symbol,
            list(df.columns),
        )
        return _empty_ohlcv()

    df = df[cols].copy()

    try:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    except Exception:
        logger.exception("Failed to convert Yahoo timestamp for symbol=%s", symbol)
        return _empty_ohlcv()

    return df


def _load_crypto_binance(
    symbol: str,
    lookback_days: int,
    timeframe: str,
) -> pd.DataFrame:
    """
    Lädt OHLCV-Daten für Krypto über Binance (CCXT).
    """
    try:
        exchange = ccxt.binance()
    except Exception:
        logger.exception("Failed to initialize ccxt binance exchange")
        return _empty_ohlcv()

    since = int((_utc_now() - timedelta(days=lookback_days * 2)).timestamp() * 1000)

    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since)
    except Exception:
        logger.exception("ccxt fetch_ohlcv failed for symbol=%s", symbol)
        return _empty_ohlcv()

    if not ohlcv:
        logger.warning("No data returned from Binance for symbol=%s", symbol)
        return _empty_ohlcv()

    df = pd.DataFrame(
        ohlcv,
        columns=["timestamp", "open", "high", "low", "close", "volume"],
    )

    try:
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True, errors="coerce")
    except Exception:
        logger.exception("Failed to convert Binance timestamps for symbol=%s", symbol)
        return _empty_ohlcv()

    return df
