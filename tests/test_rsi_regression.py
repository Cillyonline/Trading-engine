from __future__ import annotations

import pandas as pd

from cilly_trading.indicators.rsi import rsi


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
