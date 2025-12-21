"""
Daten-Layer für die Cilly Trading Engine.

Stellt die Funktion `load_ohlcv` bereit, die OHLCV-Daten für
Aktien (über Yahoo Finance) und Krypto (über Binance via CCXT) lädt.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Final, Literal

import ccxt
import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

MarketType = Literal["stock", "crypto"]

REQUIRED_COLS: Final[tuple[str, ...]] = ("timestamp", "open", "high", "low", "close", "volume")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _empty_ohlcv() -> pd.DataFrame:
    # MVP-konform: leeres DF signalisiert "no data" / "error", ohne Engine zu crashen
    return pd.DataFrame(columns=list(REQUIRED_COLS))


def _validate_and_normalize_ohlcv(
    df: pd.DataFrame,
    *,
    symbol: str,
    source: str,
) -> pd.DataFrame:
    """
    Normalisiert und validiert das OHLCV-DataFrame.

    Erwartetes Schema: ["timestamp", "open", "high", "low", "close", "volume"]
    - timestamp: tz-aware UTC datetime
    - keine Exceptions nach außen (gibt leeres DF zurück bei Ungültigkeit)
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
        ts = pd.to_datetime(out["timestamp"], utc=True, errors="coerce")
    except Exception:
        logger.exception("Failed to parse timestamp from %s for symbol=%s", source, symbol)
        return _empty_ohlcv()

    out["timestamp"] = ts
    out = out.dropna(subset=["timestamp"])
    if out.empty:
        logger.warning("All timestamps invalid from %s for symbol=%s", source, symbol)
        return _empty_ohlcv()

    # OHLCV numerisch machen (robust)
    for col in ("open", "high", "low", "close", "volume"):
        out[col] = pd.to_numeric(out[col], errors="coerce")

    # Wenn OHLC komplett NaN sind -> ungültig
    ohlc_all_nan = out[["open", "high", "low", "close"]].isna().all(axis=1)
    out = out.loc[~ohlc_all_nan].copy()
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

    :param symbol: Ticker (z. B. "AAPL" oder "BTC/USDT")
    :param timeframe: Zeitrahmen, z. B. "D1"
    :param lookback_days: Anzahl Tage, die mindestens abgedeckt sein sollen
    :param market_type: "stock" oder "crypto"
    :return: DataFrame mit Spalten: ["timestamp", "open", "high", "low", "close", "volume"]
             Bei Provider-Fehler / No-Data: leeres DataFrame (Engine darf nicht crashen)
    """
    if timeframe.upper() == "D1":
        yf_interval = "1d"
        ccxt_timeframe = "1d"
    else:
        # MVP: nur Tagesdaten offiziell unterstützt (Programmierfehler => darf knallen)
        raise ValueError(f"Unsupported timeframe for MVP: {timeframe}")

    if lookback_days <= 0:
        # Ebenfalls eher Programmierfehler / Request-Fehler
        raise ValueError(f"lookback_days must be > 0, got: {lookback_days}")

    end = _utc_now()
    # etwas Puffer nach hinten, falls es Feiertage etc. gibt
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
        # Wichtigster MVP-Guardrail: ein Symbol darf die Engine nicht stoppen
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
    Gibt bei Provider-Fehlern ein leeres DF zurück (Logging erfolgt hier).
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

    # yfinance liefert typischerweise Spalten: Open, High, Low, Close, Adj Close, Volume
    # Robuste Umbenennung (case-sensitive Mapping auf bekannte Namen)
    rename_map = {
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume",
        "Adj Close": "adj_close",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    # Index -> timestamp
    df = df.reset_index()

    # Je nach yfinance kann die Index-Spalte unterschiedlich heißen
    if "Date" in df.columns:
        df = df.rename(columns={"Date": "timestamp"})
    elif "Datetime" in df.columns:
        df = df.rename(columns={"Datetime": "timestamp"})
    elif "index" in df.columns:
        df = df.rename(columns={"index": "timestamp"})

    # Pflichtspalten extrahieren (falls was fehlt -> leer)
    cols = ["timestamp", "open", "high", "low", "close", "volume"]
    if not all(c in df.columns for c in cols):
        logger.warning(
            "Unexpected Yahoo Finance schema for symbol=%s (columns=%s)",
            symbol,
            list(df.columns),
        )
        return _empty_ohlcv()

    df = df[cols].copy()

    # timestamp in UTC normieren (Yahoo liefert meist tz-naive)
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
    Gibt bei Provider-Fehlern ein leeres DF zurück (Logging erfolgt hier).
    """
    try:
        exchange = ccxt.binance()
    except Exception:
        logger.exception("Failed to initialize ccxt binance exchange")
        return _empty_ohlcv()

    # seit X Tagen zurück; CCXT arbeitet mit ms seit Epoch
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

    # Timestamp von ms in datetime umwandeln
    try:
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True, errors="coerce")
    except Exception:
        logger.exception("Failed to convert Binance timestamps for symbol=%s", symbol)
        return _empty_ohlcv()

    return df
