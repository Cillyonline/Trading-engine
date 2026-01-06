from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

import api.main as api_main
from cilly_trading.engine import core as engine_core
from cilly_trading.engine.core import EngineConfig, run_watchlist_analysis
from cilly_trading.repositories.signals_sqlite import SqliteSignalRepository
from cilly_trading.strategies.rsi2 import Rsi2Strategy


def _make_repo(tmp_path: Path) -> SqliteSignalRepository:
    db_path = tmp_path / "api_smoke.db"
    return SqliteSignalRepository(db_path=db_path)


def _mock_ohlcv_df() -> pd.DataFrame:
    timestamps = pd.to_datetime(
        [
            "2025-01-01T00:00:00+00:00",
            "2025-01-02T00:00:00+00:00",
            "2025-01-03T00:00:00+00:00",
        ],
        utc=True,
    )
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": [101.0, 91.0, 81.0],
            "high": [102.0, 92.0, 82.0],
            "low": [99.0, 89.0, 79.0],
            "close": [100.0, 90.0, 80.0],
            "volume": [1000.0, 1000.0, 1000.0],
        }
    )


def test_api_smoke_engine_db_api(tmp_path: Path, monkeypatch) -> None:
    repo = _make_repo(tmp_path)
    # Assumption: API endpoints read api_main.signal_repo at request time
    # (repo is not bound at import or startup time).
    monkeypatch.setattr(api_main, "signal_repo", repo)

    fixed_timestamp = "2025-01-03T00:00:00+00:00"
    monkeypatch.setattr(engine_core, "_now_iso", lambda: fixed_timestamp)
    monkeypatch.setattr(engine_core, "load_ohlcv", lambda **_: _mock_ohlcv_df())

    engine_config = EngineConfig(
        timeframe="D1",
        lookback_days=5,
        market_type="stock",
        data_source="yahoo",
    )

    signals = run_watchlist_analysis(
        symbols=["AAPL"],
        strategies=[Rsi2Strategy()],
        engine_config=engine_config,
        strategy_configs={"RSI2": {}},
        signal_repo=repo,
    )

    assert len(signals) >= 1

    client = TestClient(api_main.app)
    response = client.get("/signals", params={"symbol": "AAPL", "strategy": "RSI2"})

    assert response.status_code == 200
    payload = response.json()

    assert payload["total"] >= 1
    items = payload["items"]
    assert any(
        item.get("symbol") == "AAPL"
        and item.get("strategy") == "RSI2"
        and item.get("created_at") == fixed_timestamp
        for item in items
    ), f"Expected signal not found in payload items: {items}"


def test_api_smoke_signals_empty(tmp_path: Path, monkeypatch) -> None:
    repo = _make_repo(tmp_path)
    monkeypatch.setattr(api_main, "signal_repo", repo)

    client = TestClient(api_main.app)
    response = client.get("/signals")

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"] == []
    assert payload["total"] == 0
