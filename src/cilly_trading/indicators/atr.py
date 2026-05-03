"""ATR (Average True Range) indicator for the Cilly Trading Engine.

Computes ATR using Wilder's smoothing method — the same smoothing approach
used by the RSI indicator in this package.
"""

from __future__ import annotations

import pandas as pd


def atr(
    df: pd.DataFrame,
    period: int = 14,
    high_column: str = "high",
    low_column: str = "low",
    close_column: str = "close",
) -> pd.Series:
    """Compute ATR using Wilder's smoothing method.

    :param df: DataFrame with high, low, and close columns.
    :param period: ATR period (default: 14).
    :param high_column: Column name for highs.
    :param low_column: Column name for lows.
    :param close_column: Column name for closes.
    :return: Series of ATR values, index-aligned with df.
             The first ``period`` values are NaN (warm-up phase).
    """
    for col in (high_column, low_column, close_column):
        if col not in df.columns:
            raise ValueError(f"Column '{col}' not found in DataFrame")

    high = df[high_column].astype(float)
    low = df[low_column].astype(float)
    close = df[close_column].astype(float)
    n = len(close)

    if n == 0:
        return pd.Series([], index=df.index, dtype=float)

    # True Range: max of (high-low, |high-prev_close|, |low-prev_close|)
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    # First bar has no previous close — TR is just high - low
    tr.iloc[0] = high.iloc[0] - low.iloc[0]

    if n <= period:
        return pd.Series([float("nan")] * n, index=df.index, dtype=float)

    # Wilder's SMA seed: mean of first `period` true ranges
    atr_values = [float("nan")] * n
    atr_values[period - 1] = float(tr.iloc[:period].mean())

    for i in range(period, n):
        atr_values[i] = (atr_values[i - 1] * (period - 1) + tr.iloc[i]) / period

    return pd.Series(atr_values, index=df.index, dtype=float)
