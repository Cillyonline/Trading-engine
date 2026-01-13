from __future__ import annotations

import logging

from cilly_trading.engine.core import add_signal_ids, compute_analysis_run_id, compute_signal_id


def test_analysis_run_id_deterministic_for_key_order_and_assets() -> None:
    payload_a = {
        "symbol": "AAPL",
        "strategy": "RSI2",
        "ingestion_run_id": "ingest-1",
        "assets": ["aapl", "msft"],
        "market_type": "stock",
    }
    payload_b = {
        "market_type": "stock",
        "assets": ["MSFT", "AAPL"],
        "ingestion_run_id": "ingest-1",
        "strategy": "RSI2",
        "symbol": "AAPL",
    }

    assert compute_analysis_run_id(payload_a) == compute_analysis_run_id(payload_b)


def test_signal_id_deterministic_for_key_order_and_assets() -> None:
    signal_a = {
        "symbol": "AAPL",
        "strategy": "RSI2",
        "timestamp": "2025-01-03T00:00:00+00:00",
        "timeframe": "D1",
        "market_type": "stock",
        "data_source": "yahoo",
        "direction": "long",
        "stage": "setup",
        "assets": ["aapl", "msft"],
    }
    signal_b = {
        "assets": ["MSFT", "AAPL"],
        "stage": "setup",
        "direction": "long",
        "data_source": "yahoo",
        "market_type": "stock",
        "timeframe": "D1",
        "timestamp": "2025-01-03T00:00:00+00:00",
        "strategy": "RSI2",
        "symbol": "AAPL",
    }

    assert compute_signal_id(signal_a) == compute_signal_id(signal_b)


def test_add_signal_ids_skips_missing_timestamp(caplog) -> None:
    caplog.set_level(logging.WARNING, logger="cilly_trading.engine.core")
    signals = [
        {
            "symbol": "AAPL",
            "strategy": "RSI2",
            "direction": "long",
            "stage": "setup",
        },
        {
            "symbol": "MSFT",
            "strategy": "RSI2",
            "direction": "long",
            "stage": "setup",
            "timestamp": "2025-01-03T00:00:00+00:00",
        },
    ]

    enriched = add_signal_ids(signals)

    assert len(enriched) == 1
    assert enriched[0]["symbol"] == "MSFT"
    assert "signal_id" in enriched[0]
    assert "Skipping signal without timestamp" in caplog.text
