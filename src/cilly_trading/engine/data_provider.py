"""DataProvider interface for decoupled market data loading.

Interface contract
──────────────────
``get_ohlcv`` returns a ``pd.DataFrame`` with these columns:

  ┌───────────┬─────────────────────────────────────────────────────┐
  │ Column    │ Type / constraint                                   │
  ├───────────┼─────────────────────────────────────────────────────┤
  │ timestamp │ pd.Timestamp (UTC, timezone-aware) or datetime-like │
  │ open      │ float64, finite, > 0                                │
  │ high      │ float64, finite, ≥ open and close                   │
  │ low       │ float64, finite, ≤ open and close                   │
  │ close     │ float64, finite, > 0                                │
  │ volume    │ float64 or int, finite, ≥ 0                        │
  └───────────┴─────────────────────────────────────────────────────┘

- All timestamps MUST be UTC. Timezone-naive timestamps are not permitted.
- An empty DataFrame (zero rows) with the correct columns is returned when
  no data is available for the requested parameters.
- No NaN or infinite values in OHLCV columns.
- Rows are sorted by timestamp ascending.

Implementations must not raise exceptions for missing or unavailable data
(return an empty DataFrame instead). They MAY raise for invalid arguments
(negative lookback, unsupported timeframe strings, etc.).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable

import pandas as pd


OHLCV_COLUMNS: tuple[str, ...] = ("timestamp", "open", "high", "low", "close", "volume")


def empty_ohlcv() -> pd.DataFrame:
    """Return an empty OHLCV DataFrame with the canonical column schema."""
    return pd.DataFrame(columns=list(OHLCV_COLUMNS))


@runtime_checkable
class DataProvider(Protocol):
    """Protocol for market data providers.

    All implementations must return a DataFrame conforming to the contract
    documented at the top of this module.
    """

    def get_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> pd.DataFrame:
        """Fetch OHLCV data for a symbol over a date range.

        Args:
            symbol: Ticker or trading pair (e.g. "AAPL", "BTC/USDT").
            timeframe: Candle interval string (e.g. "1d", "1h", "4h").
            start: Start of the date range (UTC).
            end: End of the date range (UTC, exclusive or inclusive per provider).

        Returns:
            DataFrame with columns [timestamp, open, high, low, close, volume],
            sorted by timestamp ascending. Empty DataFrame when no data is
            available.
        """
        ...


class YFinanceDataProvider:
    """DataProvider backed by yfinance (Yahoo Finance).

    Wraps the existing yfinance loading logic from engine/data.py without
    changing any behavior. Supports daily (``"1d"``) timeframe only.
    """

    def get_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> pd.DataFrame:
        try:
            import yfinance as yf
        except ImportError:
            return empty_ohlcv()

        try:
            df = yf.download(
                symbol,
                start=start.date(),
                end=end.date(),
                interval=timeframe if timeframe else "1d",
                progress=False,
            )
        except Exception:
            return empty_ohlcv()

        if df is None or df.empty:
            return empty_ohlcv()

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

        missing = [c for c in OHLCV_COLUMNS if c not in df.columns]
        if missing:
            return empty_ohlcv()

        df = df[list(OHLCV_COLUMNS)].copy()
        try:
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
        except Exception:
            return empty_ohlcv()

        return df.sort_values("timestamp").reset_index(drop=True)


class CcxtDataProvider:
    """DataProvider backed by ccxt (crypto exchanges via Binance).

    Wraps the existing ccxt loading logic from engine/data.py without
    changing any behavior.

    Args:
        exchange_id: ccxt exchange identifier (default: ``"binance"``).
    """

    def __init__(self, exchange_id: str = "binance") -> None:
        self._exchange_id = exchange_id

    def get_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> pd.DataFrame:
        try:
            import ccxt as _ccxt
        except ImportError:
            return empty_ohlcv()

        try:
            exchange = getattr(_ccxt, self._exchange_id)()
        except Exception:
            return empty_ohlcv()

        since_ms = int(start.timestamp() * 1000)
        try:
            raw = exchange.fetch_ohlcv(symbol, timeframe=timeframe or "1d", since=since_ms)
        except Exception:
            return empty_ohlcv()

        if not raw:
            return empty_ohlcv()

        df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)

        end_ts = pd.Timestamp(end).tz_localize("UTC") if end.tzinfo is None else pd.Timestamp(end).tz_convert("UTC")
        df = df[df["timestamp"] <= end_ts].copy()

        return df.sort_values("timestamp").reset_index(drop=True)


class LocalSnapshotDataProvider:
    """DataProvider backed by in-memory fixture data.

    Designed for deterministic test runs without any external dependencies.
    Accepts a mapping of ``symbol → list of bar dicts`` (or pd.DataFrame).

    Each bar dict must contain at least ``timestamp`` and ``close`` keys;
    ``open``, ``high``, ``low``, ``volume`` default to ``close`` / 0 if absent.

    Args:
        fixtures: Mapping from symbol string to bar data (list of dicts or DataFrame).
    """

    def __init__(self, fixtures: dict[str, Any]) -> None:
        self._fixtures: dict[str, pd.DataFrame] = {}
        for sym, data in fixtures.items():
            if isinstance(data, pd.DataFrame):
                df = data.copy()
            else:
                df = pd.DataFrame(data)
            self._fixtures[sym.upper()] = self._normalize(df)

    @staticmethod
    def _normalize(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return empty_ohlcv()

        if "timestamp" not in df.columns:
            return empty_ohlcv()

        df = df.copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")

        for col in ("open", "high", "low", "close", "volume"):
            if col not in df.columns:
                df[col] = df.get("close", 0.0)

        df = df[list(OHLCV_COLUMNS)].copy()
        return df.sort_values("timestamp").reset_index(drop=True)

    def get_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> pd.DataFrame:
        df = self._fixtures.get(symbol.upper())
        if df is None or df.empty:
            return empty_ohlcv()

        start_ts = pd.Timestamp(start).tz_localize("UTC") if start.tzinfo is None else pd.Timestamp(start).tz_convert("UTC")
        end_ts = pd.Timestamp(end).tz_localize("UTC") if end.tzinfo is None else pd.Timestamp(end).tz_convert("UTC")
        mask = (df["timestamp"] >= start_ts) & (df["timestamp"] <= end_ts)
        return df[mask].reset_index(drop=True)
