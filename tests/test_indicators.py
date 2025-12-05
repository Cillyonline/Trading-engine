import pandas as pd

from cilly_trading.indicators.rsi import rsi
from cilly_trading.indicators.macd import macd


def test_rsi_basic_shape():
    data = {
        "close": [1, 2, 3, 4, 5, 4, 3, 4, 5, 6],
    }
    df = pd.DataFrame(data)
    rsi_series = rsi(df, period=3)
    assert len(rsi_series) == len(df)


def test_macd_basic_shape():
    data = {
        "close": [1, 2, 3, 4, 5, 4, 3, 4, 5, 6],
    }
    df = pd.DataFrame(data)
    macd_df = macd(df)
    assert len(macd_df) == len(df)
    assert set(macd_df.columns) == {"macd", "signal", "hist"}
