"""
RSI-Indikator für die Cilly Trading Engine.

Berechnet den Relative Strength Index (RSI) auf Basis der Schlusskurse.
Verwendet Wilder's Smoothing (SMA-Seed + rekursive Glättung) — den von Wilder
ursprünglich definierten Algorithmus, nicht EWMA.
"""

from __future__ import annotations

import pandas as pd


def rsi(
    df: pd.DataFrame,
    period: int = 14,
    price_column: str = "close",
) -> pd.Series:
    """
    Berechnet den RSI nach Wilder's Smoothing-Methode.

    :param df: DataFrame mit mindestens einer Spalte für Schlusskurse
    :param period: Länge des RSI-Fensters (Standard: 14)
    :param price_column: Name der Spalte mit Schlusskursen (Standard: "close")
    :return: Pandas Series mit RSI-Werten (0–100), index-aligned mit df;
             die ersten `period` Werte sind NaN (Warm-up-Phase)
    """
    if price_column not in df.columns:
        raise ValueError(f"Column '{price_column}' not found in DataFrame")

    close = df[price_column].astype(float)
    n = len(close)

    if n <= period:
        return pd.Series([float("nan")] * n, index=df.index, dtype=float)

    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)

    # Wilder's SMA seed: average of first `period` up/down moves (indices 1..period)
    avg_gain = gain.iloc[1 : period + 1].mean()
    avg_loss = loss.iloc[1 : period + 1].mean()

    rsi_values = [float("nan")] * n
    rsi_values[period] = _rs_to_rsi(avg_gain, avg_loss)

    for i in range(period + 1, n):
        avg_gain = (avg_gain * (period - 1) + gain.iloc[i]) / period
        avg_loss = (avg_loss * (period - 1) + loss.iloc[i]) / period
        rsi_values[i] = _rs_to_rsi(avg_gain, avg_loss)

    return pd.Series(rsi_values, index=df.index, dtype=float).clip(0, 100)


def _rs_to_rsi(avg_gain: float, avg_loss: float) -> float:
    """Convert average gain/loss to RSI value, handling zero-division edge cases."""
    if avg_loss == 0.0 and avg_gain == 0.0:
        return 50.0  # flat market: neutral
    if avg_loss == 0.0:
        return 100.0  # pure uptrend: saturate at 100
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))
