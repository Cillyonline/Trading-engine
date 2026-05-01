from __future__ import annotations

import pytest
import pandas as pd

from cilly_trading.indicators.rsi import rsi


def test_rsi_wilders_sma_seed_differs_from_ewma_for_period_gt_2() -> None:
    """Wilder's uses SMA seed; EWMA would produce a different value for period=3+."""
    # 3 up moves, then 3 down moves — EWMA and Wilder's diverge here
    closes = [10.0, 11.0, 12.0, 13.0, 12.0, 11.0, 10.0]
    df = pd.DataFrame({"close": closes})
    result = rsi(df, period=3)

    # SMA seed: avg_gain=1.0 (mean of first 3 diffs: +1,+1,+1), avg_loss=0.0
    # → RSI at index 3 = 100.0
    assert result.iloc[3] == 100.0

    # After index 4 (loss=1): avg_gain=(1*2+0)/3=2/3, avg_loss=(0*2+1)/3=1/3
    # RS = 2, RSI = 100 - 100/3 ≈ 66.67
    assert result.iloc[4] == pytest.approx(66.6667, abs=1e-3)

    # Warm-up indices must be NaN
    assert all(pd.isna(result.iloc[i]) for i in range(3))


def test_rsi_warm_up_indices_are_nan() -> None:
    df = pd.DataFrame({"close": [float(i) for i in range(1, 21)]})
    result = rsi(df, period=14)
    assert all(pd.isna(result.iloc[i]) for i in range(14))
    assert not pd.isna(result.iloc[14])


def test_rsi_too_short_returns_all_nan() -> None:
    df = pd.DataFrame({"close": [1.0, 2.0, 3.0]})
    result = rsi(df, period=14)
    assert all(pd.isna(v) for v in result)
    assert len(result) == 3


def test_rsi_saturates_at_100_when_average_loss_is_zero_and_gain_positive() -> None:
    df = pd.DataFrame({"close": [float(value) for value in range(1, 21)]})

    result = rsi(df, period=14)

    assert result.iloc[-1] == 100.0
    assert not pd.isna(result.iloc[-1])


def test_rsi_returns_neutral_value_for_flat_warm_window() -> None:
    df = pd.DataFrame({"close": [100.0] * 20})

    result = rsi(df, period=14)

    assert result.iloc[-1] == 50.0
    assert not pd.isna(result.iloc[-1])
