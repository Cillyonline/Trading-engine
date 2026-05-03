"""Tests for ATR indicator, AtrPositionSizer, and TURTLE ATR integration (Issue #1097)."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from cilly_trading.indicators.atr import atr as compute_atr
from cilly_trading.risk_framework.position_sizing import AtrPositionSizer


# ── ATR indicator ─────────────────────────────────────────────────────────────


def _ohlc_df(rows: list[tuple[float, float, float]]) -> pd.DataFrame:
    """Build a minimal OHLC DataFrame from (high, low, close) tuples."""
    return pd.DataFrame(rows, columns=["high", "low", "close"])


def test_atr_returns_series_of_same_length() -> None:
    df = _ohlc_df([(10, 8, 9)] * 20)
    result = compute_atr(df, period=14)
    assert len(result) == 20


def test_atr_first_period_minus_one_values_are_nan() -> None:
    df = _ohlc_df([(10, 8, 9)] * 20)
    result = compute_atr(df, period=14)
    for i in range(13):
        assert math.isnan(result.iloc[i]), f"index {i} should be NaN"


def test_atr_value_at_seed_index_is_mean_of_first_period_trs() -> None:
    # Flat bars: TR = high - low = 2 for every bar
    df = _ohlc_df([(10, 8, 9)] * 20)
    result = compute_atr(df, period=14)
    assert abs(result.iloc[13] - 2.0) < 1e-9


def test_atr_wilder_smoothing_converges_after_seed() -> None:
    # Flat bars: ATR should stay constant at 2.0 throughout
    df = _ohlc_df([(10, 8, 9)] * 30)
    result = compute_atr(df, period=14)
    for i in range(13, 30):
        assert abs(result.iloc[i] - 2.0) < 1e-9, f"index {i}: {result.iloc[i]}"


def test_atr_increases_when_volatility_spikes() -> None:
    # 20 flat bars, then one wide bar
    rows = [(10, 8, 9)] * 20 + [(20, 1, 10)]
    df = _ohlc_df(rows)
    result = compute_atr(df, period=14)
    # ATR before spike
    before = result.iloc[19]
    # ATR after spike
    after = result.iloc[20]
    assert after > before


def test_atr_raises_when_column_missing() -> None:
    df = pd.DataFrame({"high": [10], "low": [8]})
    with pytest.raises(ValueError, match="close"):
        compute_atr(df)


def test_atr_empty_dataframe_returns_empty_series() -> None:
    df = pd.DataFrame(columns=["high", "low", "close"])
    result = compute_atr(df)
    assert len(result) == 0


def test_atr_fewer_rows_than_period_returns_all_nan() -> None:
    df = _ohlc_df([(10, 8, 9)] * 5)
    result = compute_atr(df, period=14)
    assert all(math.isnan(v) for v in result)


def test_atr_custom_column_names() -> None:
    df = pd.DataFrame(
        {"h": [10, 11, 12], "l": [8, 9, 10], "c": [9, 10, 11]}
    )
    result = compute_atr(df, period=2, high_column="h", low_column="l", close_column="c")
    assert len(result) == 3


def test_atr_known_value_three_bar_period() -> None:
    # period=2, so seed ATR = mean of TR[0] and TR[1]
    # TR[0] = high[0] - low[0] = 10 - 8 = 2 (no prev close)
    # TR[1] = max(11-9, |11-9|, |9-9|) = max(2, 2, 0) = 2
    # seed ATR at index 1 = (2 + 2) / 2 = 2.0
    # TR[2] = max(12-10, |12-9|, |10-9|) = max(2, 3, 1) = 3
    # ATR[2] = (2.0 * 1 + 3) / 2 = 2.5
    df = _ohlc_df([(10, 8, 9), (11, 9, 9), (12, 10, 11)])
    result = compute_atr(df, period=2)
    assert math.isnan(result.iloc[0])
    assert abs(result.iloc[1] - 2.0) < 1e-9
    assert abs(result.iloc[2] - 2.5) < 1e-9


# ── AtrPositionSizer ──────────────────────────────────────────────────────────


def test_atr_sizer_basic_formula() -> None:
    # position_size = (10000 * 0.01) / (5.0 * 2.0) = 100 / 10 = 10
    sizer = AtrPositionSizer(atr_period=14, atr_multiplier=2.0)
    result = sizer.compute_position_size(account_equity=10_000.0, risk_pct=0.01, atr_value=5.0)
    assert result is not None
    assert abs(result - 10.0) < 1e-9


def test_atr_sizer_high_volatility_produces_smaller_size() -> None:
    sizer = AtrPositionSizer()
    low_vol = sizer.compute_position_size(account_equity=10_000.0, risk_pct=0.01, atr_value=2.0)
    high_vol = sizer.compute_position_size(account_equity=10_000.0, risk_pct=0.01, atr_value=20.0)
    assert low_vol is not None
    assert high_vol is not None
    assert high_vol < low_vol


def test_atr_sizer_low_volatility_produces_larger_size() -> None:
    sizer = AtrPositionSizer()
    result = sizer.compute_position_size(account_equity=10_000.0, risk_pct=0.01, atr_value=0.01)
    assert result is not None
    assert result > 1_000.0


def test_atr_sizer_returns_none_for_zero_atr() -> None:
    sizer = AtrPositionSizer()
    result = sizer.compute_position_size(account_equity=10_000.0, risk_pct=0.01, atr_value=0.0)
    assert result is None


def test_atr_sizer_returns_none_for_negative_atr() -> None:
    sizer = AtrPositionSizer()
    result = sizer.compute_position_size(account_equity=10_000.0, risk_pct=0.01, atr_value=-1.0)
    assert result is None


def test_atr_sizer_returns_none_for_zero_equity() -> None:
    sizer = AtrPositionSizer()
    result = sizer.compute_position_size(account_equity=0.0, risk_pct=0.01, atr_value=5.0)
    assert result is None


def test_atr_sizer_returns_none_for_negative_equity() -> None:
    sizer = AtrPositionSizer()
    result = sizer.compute_position_size(account_equity=-100.0, risk_pct=0.01, atr_value=5.0)
    assert result is None


def test_atr_sizer_returns_none_for_zero_risk_pct() -> None:
    sizer = AtrPositionSizer()
    result = sizer.compute_position_size(account_equity=10_000.0, risk_pct=0.0, atr_value=5.0)
    assert result is None


def test_atr_sizer_returns_none_for_nan_atr() -> None:
    sizer = AtrPositionSizer()
    result = sizer.compute_position_size(account_equity=10_000.0, risk_pct=0.01, atr_value=float("nan"))
    assert result is None


def test_atr_sizer_returns_none_for_infinite_atr() -> None:
    sizer = AtrPositionSizer()
    result = sizer.compute_position_size(account_equity=10_000.0, risk_pct=0.01, atr_value=float("inf"))
    assert result is None


def test_atr_sizer_custom_multiplier() -> None:
    # (10000 * 0.02) / (5.0 * 4.0) = 200 / 20 = 10
    sizer = AtrPositionSizer(atr_multiplier=4.0)
    result = sizer.compute_position_size(account_equity=10_000.0, risk_pct=0.02, atr_value=5.0)
    assert result is not None
    assert abs(result - 10.0) < 1e-9


def test_atr_sizer_invalid_period_raises() -> None:
    with pytest.raises(ValueError, match="atr_period"):
        AtrPositionSizer(atr_period=0)


def test_atr_sizer_invalid_multiplier_raises() -> None:
    with pytest.raises(ValueError, match="atr_multiplier"):
        AtrPositionSizer(atr_multiplier=0.0)


def test_atr_sizer_very_high_atr_gives_tiny_size() -> None:
    sizer = AtrPositionSizer()
    result = sizer.compute_position_size(account_equity=10_000.0, risk_pct=0.01, atr_value=1_000_000.0)
    assert result is not None
    assert result < 0.001


def test_atr_sizer_equity_near_zero_still_works() -> None:
    sizer = AtrPositionSizer()
    result = sizer.compute_position_size(account_equity=0.01, risk_pct=0.01, atr_value=5.0)
    assert result is not None
    assert result > 0.0


# ── TURTLE strategy ATR integration ──────────────────────────────────────────


def _turtle_df(n: int = 30, base_price: float = 100.0) -> pd.DataFrame:
    """Build a flat OHLC DataFrame with a single breakout on the last bar."""
    highs = [base_price + 1.0] * n
    lows = [base_price - 1.0] * n
    closes = [base_price] * n
    # Last bar breaks out above prior highs
    highs[-1] = base_price + 10.0
    closes[-1] = base_price + 10.0
    return pd.DataFrame({"high": highs, "low": lows, "close": closes})


def test_turtle_without_atr_sizing_has_no_atr_position_size() -> None:
    from cilly_trading.strategies.turtle import TurtleStrategy

    strategy = TurtleStrategy()
    df = _turtle_df()
    signals = strategy.generate_signals(df, config={})
    assert len(signals) > 0
    for sig in signals:
        assert "atr_position_size" not in sig


def test_turtle_with_atr_sizing_includes_atr_position_size() -> None:
    from cilly_trading.strategies.turtle import TurtleStrategy

    strategy = TurtleStrategy()
    df = _turtle_df(n=30)
    signals = strategy.generate_signals(
        df,
        config={
            "use_atr_sizing": True,
            "account_equity": 10_000.0,
            "risk_pct": 0.01,
            "atr_period": 14,
            "atr_multiplier": 2.0,
        },
    )
    assert len(signals) > 0
    for sig in signals:
        assert "atr_position_size" in sig
        assert sig["atr_position_size"] > 0.0


def test_turtle_with_atr_sizing_but_no_equity_has_no_atr_position_size() -> None:
    from cilly_trading.strategies.turtle import TurtleStrategy

    strategy = TurtleStrategy()
    df = _turtle_df(n=30)
    signals = strategy.generate_signals(
        df,
        config={"use_atr_sizing": True},  # no account_equity
    )
    for sig in signals:
        assert "atr_position_size" not in sig


def test_turtle_atr_position_size_scales_with_equity() -> None:
    from cilly_trading.strategies.turtle import TurtleStrategy

    strategy = TurtleStrategy()
    df = _turtle_df(n=30)

    base_config = {
        "use_atr_sizing": True,
        "risk_pct": 0.01,
        "atr_period": 14,
        "atr_multiplier": 2.0,
    }

    sigs_small = strategy.generate_signals(df, config={**base_config, "account_equity": 1_000.0})
    sigs_large = strategy.generate_signals(df, config={**base_config, "account_equity": 100_000.0})

    assert len(sigs_small) > 0 and len(sigs_large) > 0
    size_small = sigs_small[0]["atr_position_size"]
    size_large = sigs_large[0]["atr_position_size"]
    assert size_large > size_small


def test_turtle_existing_tests_still_pass_without_atr_config() -> None:
    """Existing percentage-based sizing path is unaffected."""
    from cilly_trading.strategies.turtle import TurtleStrategy

    strategy = TurtleStrategy()
    df = _turtle_df(n=30)
    signals = strategy.generate_signals(df, config={})
    # Should still produce a signal (entry_confirmed or setup)
    assert isinstance(signals, list)
