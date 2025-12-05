"""
RSI-Indikator für die Cilly Trading Engine.

Berechnet den Relative Strength Index (RSI) auf Basis der Schlusskurse.
"""

from __future__ import annotations

import pandas as pd


def rsi(
    df: pd.DataFrame,
    period: int = 14,
    price_column: str = "close",
) -> pd.Series:
    """
    Berechnet den RSI auf Basis eines DataFrames mit einer Kurs-Spalte.

    :param df: DataFrame mit mindestens einer Spalte für Schlusskurse
    :param period: Länge des RSI-Fensters (Standard: 14)
    :param price_column: Name der Spalte mit Schlusskursen (Standard: "close")
    :return: Pandas Series mit RSI-Werten (0–100), index-align mit df
    """
    if price_column not in df.columns:
        raise ValueError(f"Column '{price_column}' not found in DataFrame")

    close = df[price_column].astype(float)

    delta = close.diff()

    # Gewinne/Verluste trennen
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    # Glättung via EWMA (klassischer RSI-Ansatz)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi_series = 100 - (100 / (1 + rs))

    return rsi_series
