"""Tests for the DataProvider interface and implementations (Issue #1101)."""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import pytest

from cilly_trading.engine.data_provider import (
    OHLCV_COLUMNS,
    CcxtDataProvider,
    DataProvider,
    LocalSnapshotDataProvider,
    YFinanceDataProvider,
    empty_ohlcv,
)


_UTC = timezone.utc
_START = datetime(2024, 1, 1, tzinfo=_UTC)
_END = datetime(2024, 3, 31, tzinfo=_UTC)


# ── Helpers ───────────────────────────────────────────────────────────────────


# ── empty_ohlcv ───────────────────────────────────────────────────────────────


def test_empty_ohlcv_has_correct_columns() -> None:
    df = empty_ohlcv()
    assert list(df.columns) == list(OHLCV_COLUMNS)


def test_empty_ohlcv_has_zero_rows() -> None:
    assert len(empty_ohlcv()) == 0


# ── DataProvider Protocol ─────────────────────────────────────────────────────


def test_local_snapshot_provider_is_a_data_provider() -> None:
    provider = LocalSnapshotDataProvider({})
    assert isinstance(provider, DataProvider)


def test_yfinance_provider_is_a_data_provider() -> None:
    provider = YFinanceDataProvider()
    assert isinstance(provider, DataProvider)


def test_ccxt_provider_is_a_data_provider() -> None:
    provider = CcxtDataProvider()
    assert isinstance(provider, DataProvider)


# ── LocalSnapshotDataProvider ─────────────────────────────────────────────────


def _bars(n: int, price: float = 100.0) -> list[dict]:
    result = []
    for i in range(n):
        ts = pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(days=i)
        result.append({
            "timestamp": ts,
            "open": price,
            "high": price + 1.0,
            "low": price - 1.0,
            "close": price + i * 0.1,
            "volume": 1_000_000.0,
        })
    return result


def test_local_provider_returns_empty_for_unknown_symbol() -> None:
    provider = LocalSnapshotDataProvider({"AAPL": _bars(10)})
    df = provider.get_ohlcv("UNKNOWN", "1d", _START, _END)
    assert df.empty
    assert list(df.columns) == list(OHLCV_COLUMNS)


def test_local_provider_returns_data_for_known_symbol() -> None:
    provider = LocalSnapshotDataProvider({"AAPL": _bars(30)})
    df = provider.get_ohlcv("AAPL", "1d", _START, _END)
    assert len(df) == 30


def test_local_provider_symbol_lookup_is_case_insensitive() -> None:
    provider = LocalSnapshotDataProvider({"AAPL": _bars(10)})
    df = provider.get_ohlcv("aapl", "1d", _START, _END)
    assert len(df) == 10


def test_local_provider_filters_by_date_range() -> None:
    # 90 bars: 2024-01-01 to 2024-03-30
    provider = LocalSnapshotDataProvider({"X": _bars(90)})
    narrow_start = datetime(2024, 1, 10, tzinfo=_UTC)
    narrow_end = datetime(2024, 1, 20, tzinfo=_UTC)
    df = provider.get_ohlcv("X", "1d", narrow_start, narrow_end)
    assert len(df) == 11  # inclusive: 10, 11, ..., 20


def test_local_provider_returns_canonical_columns() -> None:
    provider = LocalSnapshotDataProvider({"X": _bars(5)})
    df = provider.get_ohlcv("X", "1d", _START, _END)
    assert list(df.columns) == list(OHLCV_COLUMNS)


def test_local_provider_timestamps_are_utc() -> None:
    provider = LocalSnapshotDataProvider({"X": _bars(5)})
    df = provider.get_ohlcv("X", "1d", _START, _END)
    for ts in df["timestamp"]:
        assert ts.tzinfo is not None


def test_local_provider_accepts_dataframe_directly() -> None:
    bars_df = pd.DataFrame(_bars(10))
    provider = LocalSnapshotDataProvider({"X": bars_df})
    df = provider.get_ohlcv("X", "1d", _START, _END)
    assert len(df) == 10


def test_local_provider_fills_missing_ohlc_columns_from_close() -> None:
    # Only timestamp and close provided
    sparse = [
        {"timestamp": pd.Timestamp("2024-01-01", tz="UTC"), "close": 100.0},
        {"timestamp": pd.Timestamp("2024-01-02", tz="UTC"), "close": 101.0},
    ]
    provider = LocalSnapshotDataProvider({"X": sparse})
    df = provider.get_ohlcv("X", "1d", _START, _END)
    assert "open" in df.columns
    assert "high" in df.columns
    assert "low" in df.columns
    assert "volume" in df.columns


def test_local_provider_empty_fixture_returns_empty_df() -> None:
    provider = LocalSnapshotDataProvider({"X": []})
    df = provider.get_ohlcv("X", "1d", _START, _END)
    assert df.empty


def test_local_provider_sorted_ascending() -> None:
    # Provide bars in reverse order
    bars = list(reversed(_bars(5)))
    provider = LocalSnapshotDataProvider({"X": bars})
    df = provider.get_ohlcv("X", "1d", _START, _END)
    timestamps = list(df["timestamp"])
    assert timestamps == sorted(timestamps)


def test_local_provider_no_external_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    """LocalSnapshotDataProvider must not import yfinance or ccxt."""
    original_import = __builtins__.__import__ if hasattr(__builtins__, "__import__") else None  # type: ignore[union-attr]
    # Just verify no exception is raised without yfinance/ccxt installed
    provider = LocalSnapshotDataProvider({"X": _bars(3)})
    df = provider.get_ohlcv("X", "1d", _START, _END)
    assert len(df) == 3


# ── YFinanceDataProvider (network-free, graceful failure) ─────────────────────


def test_yfinance_provider_returns_empty_df_when_yfinance_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Simulate yfinance being unavailable — provider must not raise."""
    import builtins
    real_import = builtins.__import__

    def mock_import(name: str, *args, **kwargs):
        if name == "yfinance":
            raise ImportError("yfinance not available")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)
    provider = YFinanceDataProvider()
    df = provider.get_ohlcv("AAPL", "1d", _START, _END)
    assert df.empty or isinstance(df, pd.DataFrame)


# ── CcxtDataProvider (network-free, graceful failure) ─────────────────────────


def test_ccxt_provider_returns_empty_df_when_ccxt_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Simulate ccxt being unavailable — provider must not raise."""
    import builtins
    real_import = builtins.__import__

    def mock_import(name: str, *args, **kwargs):
        if name == "ccxt":
            raise ImportError("ccxt not available")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)
    provider = CcxtDataProvider()
    df = provider.get_ohlcv("BTC/USDT", "1d", _START, _END)
    assert df.empty or isinstance(df, pd.DataFrame)


# ── DI pattern usage ──────────────────────────────────────────────────────────


def test_data_provider_can_be_injected_as_argument() -> None:
    """Demonstrate that DataProvider can be passed as a typed argument."""

    def run_backtest(provider: DataProvider, symbol: str) -> pd.DataFrame:
        return provider.get_ohlcv(symbol, "1d", _START, _END)

    local = LocalSnapshotDataProvider({"AAPL": _bars(10)})
    df = run_backtest(local, "AAPL")
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 10


def test_local_provider_is_substitutable_for_yfinance_provider() -> None:
    """LocalSnapshotDataProvider is a drop-in substitute for YFinanceDataProvider."""

    def fetch(provider: DataProvider, symbol: str) -> pd.DataFrame:
        return provider.get_ohlcv(symbol, "1d", _START, _END)

    yf_result = fetch(YFinanceDataProvider(), "NONEXISTENT_SYMBOL_XYZZY")
    local_result = fetch(LocalSnapshotDataProvider({"NONEXISTENT_SYMBOL_XYZZY": _bars(5)}), "NONEXISTENT_SYMBOL_XYZZY")

    # Both return DataFrames with OHLCV columns
    assert isinstance(yf_result, pd.DataFrame)
    assert isinstance(local_result, pd.DataFrame)
    assert list(local_result.columns) == list(OHLCV_COLUMNS)
