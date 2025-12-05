"""
MACD-Indikator für die Cilly Trading Engine.

Berechnet MACD-Linie, Signallinie und Histogramm.
"""

from __future__ import annotations

import pandas as pd


def macd(
    df: pd.DataFrame,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
    price_column: str = "close",
) -> pd.DataFrame:
    """
    Berechnet MACD für einen Kurs-DataFrame.

    :param df: DataFrame mit mindestens einer Spalte für Schlusskurse
    :param fast_period: Periode der schnellen EMA (Standard 12)
    :param slow_period: Periode der langsamen EMA (Standard 26)
    :param signal_period: Periode der Signallinie (EMA über MACD, Standard 9)
    :param price_column: Name der Schlusskurs-Spalte
    :return: DataFrame mit Spalten: ["macd", "signal", "hist"]
    """
    if price_column not in df.columns:
        raise ValueError(f"Column '{price_column}' not found in DataFrame")

    close = df[price_column].astype(float)

    ema_fast = close.ewm(span=fast_period, adjust=False).mean()
    ema_slow = close.ewm(span=slow_period, adjust=False).mean()

    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
    hist = macd_line - signal_line

    result = pd.DataFrame(
        {
            "macd": macd_line,
            "signal": signal_line,
            "hist": hist,
        },
        index=df.index,
    )
    return result
