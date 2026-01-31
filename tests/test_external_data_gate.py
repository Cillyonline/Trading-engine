from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List

import pandas as pd
import pytest

from cilly_trading.engine.core import (
    EngineConfig,
    ExternalDataGateClosedError,
    run_watchlist_analysis,
)


def _df_minimal() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "timestamp": "2025-01-01T00:00:00Z",
                "open": 1.0,
                "high": 1.0,
                "low": 1.0,
                "close": 1.0,
                "volume": 100.0,
            }
        ]
    )


@dataclass
class DummyRepo:
    saved: List[dict] | None = None

    def save_signals(self, signals: List[dict]) -> None:
        self.saved = list(signals)


class StrategyReturnsEmpty:
    name = "EMPTY"

    def generate_signals(self, df: Any, config: Dict[str, Any]) -> List[dict]:
        return []


def test_external_data_gate_disabled_blocks_execution(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.ERROR, logger="cilly_trading.engine.core")

    with pytest.raises(ExternalDataGateClosedError):
        run_watchlist_analysis(
            symbols=["AAPL"],
            strategies=[StrategyReturnsEmpty()],
            engine_config=EngineConfig(),
            strategy_configs={},
            signal_repo=DummyRepo(),
            ingestion_run_id="ingest-gate-001",
            snapshot_id="snapshot-gate-001",
        )

    assert "External data gate closed" in caplog.text
    assert "external_data_enabled" in caplog.text


def test_external_data_gate_enabled_allows_execution(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("cilly_trading.engine.core.load_ohlcv", lambda **_: _df_minimal())

    result = run_watchlist_analysis(
        symbols=["AAPL"],
        strategies=[StrategyReturnsEmpty()],
        engine_config=EngineConfig(external_data_enabled=True),
        strategy_configs={},
        signal_repo=DummyRepo(),
        ingestion_run_id="ingest-gate-002",
        snapshot_id="snapshot-gate-002",
    )

    assert result == []
