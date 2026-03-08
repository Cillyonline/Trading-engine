import pandas as pd
import pytest

from data_layer.ingestion_validation import (
    SnapshotValidationError,
    validate_market_data_integrity,
    validate_ohlcv_uniqueness,
    validate_snapshot_ingestion,
    validate_snapshot_source,
    validate_single_source_rows,
)


def _base_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "symbol": "AAPL",
                "timeframe": "D1",
                "timestamp": "2024-01-01T00:00:00Z",
                "open": 1,
                "high": 2,
                "low": 1,
                "close": 2,
                "volume": 10,
            },
            {
                "symbol": "AAPL",
                "timeframe": "D1",
                "timestamp": "2024-01-02T00:00:00Z",
                "open": 2,
                "high": 3,
                "low": 2,
                "close": 3,
                "volume": 11,
            },
        ]
    )


def test_validate_ohlcv_uniqueness_detects_duplicates() -> None:
    df = _base_df()
    df = pd.concat([df, df.iloc[[0]]], ignore_index=True)
    with pytest.raises(SnapshotValidationError, match="snapshot_duplicate_rows"):
        validate_ohlcv_uniqueness(df)


def test_validate_single_source_rows_rejects_mixed_sources() -> None:
    df = _base_df()
    df["source"] = ["yahoo", "binance"]
    with pytest.raises(SnapshotValidationError, match="snapshot_mixed_sources"):
        validate_single_source_rows(df, source="yahoo")


def test_validate_single_source_rows_requires_source_column() -> None:
    df = _base_df()
    with pytest.raises(
        SnapshotValidationError,
        match="snapshot_source_column_missing",
    ):
        validate_single_source_rows(df, source="yahoo")


def test_validate_snapshot_source_rejects_demo_seed() -> None:
    with pytest.raises(SnapshotValidationError, match="snapshot_source_forbidden"):
        validate_snapshot_source("demo")
    with pytest.raises(SnapshotValidationError, match="snapshot_source_forbidden"):
        validate_snapshot_source("seed")


def test_validate_snapshot_source_immutable() -> None:
    with pytest.raises(SnapshotValidationError, match="snapshot_source_immutable"):
        validate_snapshot_source("binance", existing_source="yahoo")


def test_validate_snapshot_ingestion_allows_single_source() -> None:
    df = _base_df()
    df["source"] = ["yahoo", "yahoo"]
    result = validate_snapshot_ingestion(
        df,
        source="yahoo",
        ingestion_run_id="run-1",
        symbols=["AAPL"],
        timeframe="D1",
    )
    assert result.source == "yahoo"
    assert result.ingestion_run_id == "run-1"


def test_validate_market_data_integrity_rejects_invalid_ohlc() -> None:
    df = _base_df()
    df.loc[0, "high"] = 0
    with pytest.raises(SnapshotValidationError, match="snapshot_ohlc_integrity_invalid"):
        validate_market_data_integrity(df)


def test_validate_market_data_integrity_rejects_timestamp_out_of_order() -> None:
    df = _base_df().iloc[[1, 0]].reset_index(drop=True)
    with pytest.raises(SnapshotValidationError, match="snapshot_timestamp_out_of_order"):
        validate_market_data_integrity(df)


def test_validate_market_data_integrity_rejects_duplicate_candles() -> None:
    df = _base_df()
    df = pd.concat([df, df.iloc[[0]]], ignore_index=True)
    with pytest.raises(SnapshotValidationError, match="snapshot_duplicate_candle"):
        validate_market_data_integrity(df)


def test_validate_snapshot_ingestion_rejects_integrity_violations() -> None:
    df = _base_df()
    df["source"] = ["yahoo", "yahoo"]
    df.loc[0, "low"] = 10
    with pytest.raises(SnapshotValidationError, match="snapshot_ohlc_integrity_invalid"):
        validate_snapshot_ingestion(
            df,
            source="yahoo",
            ingestion_run_id="run-1",
            symbols=["AAPL"],
            timeframe="D1",
        )
