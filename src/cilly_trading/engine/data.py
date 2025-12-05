"""
Daten-Layer für die Cilly Trading Engine.

Stellt die Funktion `load_ohlcv` bereit, die OHLCV-Daten für
Aktien (über Yahoo Finance) und Krypto (über Binance via CCXT) lädt.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal

import pandas as pd
import yfinance as yf
import ccxt

MarketType = Literal["stock", "crypto"]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


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
    """

    if timeframe.upper() == "D1":
        yf_interval = "1d"
        ccxt_timeframe = "1d"
    else:
        # MVP: nur Tagesdaten offiziell unterstützt
        raise ValueError(f"Unsupported timeframe for MVP: {timeframe}")

    end = _utc_now()
    # etwas Puffer nach hinten, falls es Feiertage etc. gibt
    start = end - timedelta(days=lookback_days * 2)

    if market_type == "stock":
        return _load_stock_yahoo(symbol, start, end, yf_interval)
    elif market_type == "crypto":
        return _load_crypto_binance(symbol, lookback_days, ccxt_timeframe)
    else:
        raise ValueError(f"Unsupported market_type: {market_type}")


def _load_stock_yahoo(
    symbol: str,
    start: datetime,
    end: datetime,
    interval: str,
) -> pd.DataFrame:
    """
    Lädt OHLCV-Daten für Aktien über Yahoo Finance.
    """
    df = yf.download(
        symbol,
        start=start.date(),
        end=end.date(),
        interval=interval,
        progress=False,
    )

    if df.empty:
        raise ValueError(f"No data returned from Yahoo Finance for symbol={symbol}")

    df = df.rename(
        columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Adj Close": "adj_close",
            "Volume": "volume",
        }
    )

    df = df.reset_index()
    df = df.rename(columns={"Date": "timestamp"})
    # nur relevante Spalten
    df = df[["timestamp", "open", "high", "low", "close", "volume"]]
    return df


def _load_crypto_binance(
    symbol: str,
    lookback_days: int,
    timeframe: str,
) -> pd.DataFrame:
    """
    Lädt OHLCV-Daten für Krypto über Binance (CCXT).
    """
    exchange = ccxt.binance()

    # seit X Tagen zurück; CCXT arbeitet mit ms seit Epoch
    since = int((_utc_now() - timedelta(days=lookback_days * 2)).timestamp() * 1000)

    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since)

    if not ohlcv:
        raise ValueError(f"No data returned from Binance for symbol={symbol}")

    df = pd.DataFrame(
        ohlcv,
        columns=["timestamp", "open", "high", "low", "close", "volume"],
    )
    # Timestamp von ms in datetime umwandeln
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    return df
