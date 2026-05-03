"""Lookahead-bias regression tests for RSI, MACD, and the data pipeline.

Issue #1090: guards against the most damaging source of inflated backtest
performance — using future-bar data when computing indicator or pipeline
output at bar t.

Strategy: build a controlled fixture of N bars, record the indicator value
at bar N-1, then append a 3× price spike at bar N and confirm that
indicator[N-1] is unchanged.  If the value changes, future data leaked
into the past-bar calculation.
"""
from __future__ import annotations

import pandas as pd
import pytest

from cilly_trading.indicators.macd import macd
from cilly_trading.indicators.rsi import rsi


# ── Fixture helpers ───────────────────────────────────────────────────────────


def _mixed_df(n: int) -> pd.DataFrame:
    """Alternating up/down price series — produces non-trivial RSI/MACD values."""
    closes = []
    price = 100.0
    for i in range(n):
        price += 1.0 if i % 3 != 0 else -2.0
        closes.append(max(price, 1.0))
    return pd.DataFrame({"close": closes})


def _ramp_df(n: int, start: float = 100.0, step: float = 0.5) -> pd.DataFrame:
    return pd.DataFrame({"close": [start + i * step for i in range(n)]})


def _append_spike(df: pd.DataFrame, multiplier: float = 5.0) -> pd.DataFrame:
    """Return a copy of df with one extra bar at close = last_close * multiplier."""
    last = float(df["close"].iloc[-1])
    return pd.concat(
        [df, pd.DataFrame({"close": [last * multiplier]})],
        ignore_index=True,
    )


def _ohlcv_df(n: int, base_price: float = 100.0) -> pd.DataFrame:
    """Minimal but valid OHLCV DataFrame with ascending daily timestamps."""
    dates = pd.date_range("2024-01-02", periods=n, freq="D", tz="UTC")
    closes = [base_price + i for i in range(n)]
    opens = closes[:]
    highs = [c * 1.005 for c in closes]
    lows = [c * 0.995 for c in closes]
    return pd.DataFrame(
        {
            "timestamp": dates,
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": [10_000.0] * n,
        }
    )


def _ohlcv_df_append_future(base_df: pd.DataFrame, spike_multiplier: float = 3.0) -> pd.DataFrame:
    """Append one valid OHLCV bar at base_df[-1].timestamp + 1 day with a price spike."""
    last_ts = pd.Timestamp(base_df["timestamp"].iloc[-1]) + pd.Timedelta(days=1)
    spike_close = float(base_df["close"].iloc[-1]) * spike_multiplier
    spike_row = pd.DataFrame(
        {
            "timestamp": [last_ts],
            "open": [spike_close],
            "high": [spike_close * 1.005],
            "low": [spike_close * 0.995],
            "close": [spike_close],
            "volume": [10_000.0],
        }
    )
    return pd.concat([base_df, spike_row], ignore_index=True)


# ── RSI lookahead tests ───────────────────────────────────────────────────────


@pytest.mark.parametrize("period", [2, 5, 14])
def test_rsi_bar_n_minus_1_unchanged_after_spike_at_bar_n(period: int) -> None:
    """RSI at bar N-1 must be identical whether or not a spike exists at bar N.

    Confirms Wilder's recursive smoothing is strictly causal: each step uses
    only the running averages and the current bar's gain/loss, never future bars.
    """
    n = period * 4
    df_base = _mixed_df(n)
    df_spiked = _append_spike(df_base, multiplier=10.0)

    rsi_base = rsi(df_base, period=period)
    rsi_spiked = rsi(df_spiked, period=period)

    last_base = rsi_base.iloc[-1]
    bar_n_minus_1_spiked = rsi_spiked.iloc[-2]

    if pd.isna(last_base):
        assert pd.isna(bar_n_minus_1_spiked), (
            f"RSI(period={period}): warm-up NaN at bar N-1 disappeared after spike."
        )
    else:
        assert last_base == pytest.approx(bar_n_minus_1_spiked, abs=1e-12), (
            f"RSI(period={period}) at bar N-1 changed after appending spike at bar N. "
            "Lookahead bias detected."
        )


@pytest.mark.parametrize("period", [2, 14])
def test_rsi_all_prior_values_unchanged_after_bar_appended(period: int) -> None:
    """Every RSI value in the base series must be identical when a future bar is added."""
    n = period * 3 + 5
    df_base = _ramp_df(n)
    df_extended = _append_spike(df_base)

    rsi_base = rsi(df_base, period=period)
    rsi_ext = rsi(df_extended, period=period)

    for i in range(len(df_base)):
        bv = rsi_base.iloc[i]
        ev = rsi_ext.iloc[i]
        if pd.isna(bv):
            assert pd.isna(ev), (
                f"RSI(period={period}): NaN at index {i} became {ev} after appending future bar."
            )
        else:
            assert bv == pytest.approx(ev, abs=1e-12), (
                f"RSI(period={period}) at index {i} changed from {bv} to {ev} "
                "after appending a future bar."
            )


def test_rsi_spike_only_affects_bar_n_not_earlier_bars() -> None:
    """RSI must reflect the spike only at the spike bar, never at earlier indices."""
    period = 2
    n = 20
    df_base = _mixed_df(n)
    df_spiked = _append_spike(df_base, multiplier=100.0)

    rsi_base = rsi(df_base, period=period)
    rsi_spiked = rsi(df_spiked, period=period)

    # All original N bars unchanged.
    for i in range(n):
        bv, sv = rsi_base.iloc[i], rsi_spiked.iloc[i]
        if not pd.isna(bv):
            assert bv == pytest.approx(sv, abs=1e-12), (
                f"RSI at index {i} changed after spike at bar {n}."
            )

    # The spike bar itself should produce a high RSI (strong up-move).
    spike_rsi = rsi_spiked.iloc[-1]
    assert not pd.isna(spike_rsi)
    assert float(spike_rsi) > float(rsi_base.iloc[-1]), (
        "Spike bar should have higher RSI than the pre-spike bar."
    )


# ── MACD lookahead tests ──────────────────────────────────────────────────────


@pytest.mark.parametrize("fast,slow,sig", [(12, 26, 9), (5, 13, 4)])
def test_macd_bar_n_minus_1_unchanged_after_spike_at_bar_n(
    fast: int, slow: int, sig: int
) -> None:
    """MACD/signal/hist at bar N-1 must be identical whether or not bar N exists.

    Confirms pandas EWM with adjust=False is strictly causal: y[t] depends
    only on y[t-1] and x[t], never on future x values.
    """
    n = slow * 3
    df_base = _mixed_df(n)
    df_spiked = _append_spike(df_base, multiplier=10.0)

    macd_base = macd(df_base, fast_period=fast, slow_period=slow, signal_period=sig)
    macd_spiked = macd(df_spiked, fast_period=fast, slow_period=slow, signal_period=sig)

    for col in ("macd", "signal", "hist"):
        bv = macd_base[col].iloc[-1]
        sv = macd_spiked[col].iloc[-2]
        assert bv == pytest.approx(sv, abs=1e-12), (
            f"MACD['{col}'] (fast={fast}, slow={slow}) at bar N-1 changed after spike. "
            "Lookahead bias detected."
        )


def test_macd_all_prior_values_unchanged_after_bar_appended() -> None:
    """Every MACD value in the base series must be identical when a future bar is added."""
    n = 60
    df_base = _mixed_df(n)
    df_extended = _append_spike(df_base, multiplier=50.0)

    macd_base = macd(df_base)
    macd_ext = macd(df_extended)

    for col in ("macd", "signal", "hist"):
        for i in range(n):
            bv = macd_base[col].iloc[i]
            ev = macd_ext[col].iloc[i]
            assert bv == pytest.approx(ev, abs=1e-12), (
                f"MACD['{col}'] at index {i} changed from {bv} to {ev} "
                "after appending a future bar."
            )


# ── Data pipeline sort-order and isolation tests ──────────────────────────────


def test_data_pipeline_output_is_sorted_ascending() -> None:
    """_validate_and_normalize_ohlcv must return rows in strictly ascending timestamp order."""
    from cilly_trading.engine.data import _validate_and_normalize_ohlcv

    df = _ohlcv_df(10)
    result = _validate_and_normalize_ohlcv(df, symbol="TEST", source="test")

    assert not result.empty, "Pipeline returned empty for valid sorted input."
    ts = pd.to_datetime(result["timestamp"], utc=True)
    diffs = ts.diff().dropna()
    assert (diffs > pd.Timedelta(0)).all(), (
        "Pipeline output has non-ascending timestamps — sort order violated."
    )


def test_data_pipeline_sort_is_stable_for_already_sorted_input() -> None:
    """Already-sorted data must keep the same order — not be reversed or shuffled."""
    from cilly_trading.engine.data import _validate_and_normalize_ohlcv

    df = _ohlcv_df(5)
    expected_closes = list(df["close"])
    result = _validate_and_normalize_ohlcv(df, symbol="TEST", source="test")

    assert not result.empty
    assert list(result["close"]) == expected_closes, (
        "Pipeline changed the order of already-sorted data."
    )


def test_data_pipeline_future_bar_does_not_change_prior_row_values() -> None:
    """Appending a future bar must leave all prior rows' values unchanged."""
    from cilly_trading.engine.data import _validate_and_normalize_ohlcv

    df_base = _ohlcv_df(10)
    df_extended = _ohlcv_df_append_future(df_base, spike_multiplier=3.0)

    result_base = _validate_and_normalize_ohlcv(df_base, symbol="TEST", source="test")
    result_ext = _validate_and_normalize_ohlcv(df_extended, symbol="TEST", source="test")

    assert not result_base.empty
    assert len(result_ext) == len(result_base) + 1, (
        "Extended result should have exactly one more row than the base."
    )

    for i in range(len(result_base)):
        for col in ("open", "high", "low", "close", "volume"):
            bv = float(result_base[col].iloc[i])
            ev = float(result_ext[col].iloc[i])
            assert bv == pytest.approx(ev, abs=1e-9), (
                f"Column '{col}' at row {i} changed from {bv} to {ev} "
                "after appending a future bar — pipeline isolation violated."
            )


def test_data_pipeline_spike_bar_is_last_in_output() -> None:
    """The appended spike bar must appear last in the sorted pipeline output."""
    from cilly_trading.engine.data import _validate_and_normalize_ohlcv

    df_base = _ohlcv_df(5, base_price=100.0)
    df_extended = _ohlcv_df_append_future(df_base, spike_multiplier=5.0)
    result = _validate_and_normalize_ohlcv(df_extended, symbol="TEST", source="test")

    assert not result.empty
    spike_close = float(df_base["close"].iloc[-1]) * 5.0
    last_close = float(result["close"].iloc[-1])
    assert last_close == pytest.approx(spike_close, rel=1e-6), (
        "Spike bar is not the last row — future bar did not sort to the end."
    )


def test_data_pipeline_no_future_data_in_rsi_computed_on_pipeline_output() -> None:
    """End-to-end: RSI computed on pipeline output shows no lookahead from appended bar.

    Combines the data pipeline and RSI tests: feed extended OHLCV through the
    pipeline, then verify RSI[N-1] equals RSI[N-1] computed on the base pipeline
    output.
    """
    from cilly_trading.engine.data import _validate_and_normalize_ohlcv

    df_base = _ohlcv_df(30)
    df_extended = _ohlcv_df_append_future(df_base, spike_multiplier=4.0)

    result_base = _validate_and_normalize_ohlcv(df_base, symbol="E2E", source="test")
    result_ext = _validate_and_normalize_ohlcv(df_extended, symbol="E2E", source="test")

    assert not result_base.empty
    assert not result_ext.empty

    rsi_base = rsi(result_base, period=2)
    rsi_ext = rsi(result_ext, period=2)

    bv = rsi_base.iloc[-1]
    ev = rsi_ext.iloc[-2]

    if pd.isna(bv):
        assert pd.isna(ev)
    else:
        assert bv == pytest.approx(ev, abs=1e-12), (
            "End-to-end: RSI at bar N-1 changed after a future bar was appended. "
            "Lookahead bias in the combined pipeline+indicator path."
        )
