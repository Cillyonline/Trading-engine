import pandas as pd

from src.data_layer.normalization import TARGET_COLUMNS, normalize_ohlcv


def test_normalize_columns_and_order() -> None:
    df = pd.DataFrame(
        {
            "timestamp": ["2024-01-02", "2024-01-01"],
            "open": [101, 100],
            "high": [106, 105],
            "low": [100, 99],
            "close": [105, 104],
            "volume": [1100, 1000],
        }
    )

    result = normalize_ohlcv(df, symbol="TEST", source="pytest")

    assert result.empty is False
    assert list(result.df.columns) == list(TARGET_COLUMNS)
    assert result.df["timestamp"].is_monotonic_increasing


def test_normalize_empty_input_is_safe() -> None:
    empty = pd.DataFrame()
    result = normalize_ohlcv(empty, symbol="TEST", source="pytest")

    assert result.empty is True
    assert list(result.df.columns) == list(TARGET_COLUMNS)
    assert result.df.empty is True


def test_normalize_missing_columns_returns_empty() -> None:
    df = pd.DataFrame({"timestamp": ["2024-01-01"], "open": [1]})  # missing others
    result = normalize_ohlcv(df, symbol="TEST", source="pytest")

    assert result.empty is True
    assert list(result.df.columns) == list(TARGET_COLUMNS)
    assert result.df.empty is True


def test_normalize_timestamp_alias_is_supported() -> None:
    df = pd.DataFrame(
        {
            "timeStamp": ["2024-01-01", "2024-01-02"],  # alias, mixed case
            "open": [100, 101],
            "high": [105, 106],
            "low": [99, 100],
            "close": [104, 105],
            "volume": [1000, 1100],
        }
    )

    result = normalize_ohlcv(df, symbol="TEST", source="pytest")

    assert result.empty is False
    assert list(result.df.columns) == list(TARGET_COLUMNS)
    assert result.df["timestamp"].is_monotonic_increasing
