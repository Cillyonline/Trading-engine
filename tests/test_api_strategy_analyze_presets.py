from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

import api.main as api_main
from cilly_trading.engine import core as engine_core
from cilly_trading.repositories.analysis_runs_sqlite import SqliteAnalysisRunRepository
from cilly_trading.repositories.signals_sqlite import SqliteSignalRepository


def _make_repo(tmp_path: Path) -> SqliteSignalRepository:
    db_path = tmp_path / "strategy_analyze.db"
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


def _setup_client(tmp_path: Path, monkeypatch) -> TestClient:
    repo = _make_repo(tmp_path)
    analysis_db_path = tmp_path / "analysis_runs.db"
    analysis_repo = SqliteAnalysisRunRepository(db_path=analysis_db_path)
    monkeypatch.setattr(api_main, "signal_repo", repo)
    monkeypatch.setattr(api_main, "ANALYSIS_DB_PATH", analysis_db_path)
    monkeypatch.setattr(api_main, "analysis_run_repo", analysis_repo)
    monkeypatch.setattr(engine_core, "load_ohlcv", lambda **_: _mock_ohlcv_df())
    monkeypatch.setattr(engine_core, "_now_iso", lambda: "2025-01-03T00:00:00+00:00")
    return TestClient(api_main.app)


def test_strategy_analyze_multi_presets_returns_results(tmp_path: Path, monkeypatch) -> None:
    client = _setup_client(tmp_path, monkeypatch)

    payload = {
        "symbol": "AAPL",
        "strategy": "RSI2",
        "market_type": "stock",
        "lookback_days": 30,
        "preset_ids": ["fast", "slow"],
        "strategy_config": {"oversold_threshold": 15.0},
    }

    response = client.post("/strategy/analyze", json=payload)

    assert response.status_code == 200
    data = response.json()

    assert data["strategy"] == "RSI2"
    assert data["results_by_preset"] is not None
    assert list(data["results_by_preset"].keys()) == ["fast", "slow"]
    assert isinstance(data["results_by_preset"]["fast"], list)
    assert isinstance(data["results_by_preset"]["slow"], list)
    assert data["preset_results"] is not None
    assert [item["preset_id"] for item in data["preset_results"]] == ["fast", "slow"]


def test_strategy_analyze_duplicate_preset_ids_rejected(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _setup_client(tmp_path, monkeypatch)

    payload = {
        "symbol": "AAPL",
        "strategy": "RSI2",
        "market_type": "stock",
        "lookback_days": 30,
        "preset_ids": ["dup", "dup"],
    }

    response = client.post("/strategy/analyze", json=payload)

    assert response.status_code == 422


def test_strategy_analyze_missing_preset_id_rejected(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _setup_client(tmp_path, monkeypatch)

    payload = {
        "symbol": "AAPL",
        "strategy": "RSI2",
        "market_type": "stock",
        "lookback_days": 30,
        "preset_ids": [],
    }

    response = client.post("/strategy/analyze", json=payload)

    assert response.status_code == 422


def test_strategy_analyze_deterministic_output(tmp_path: Path, monkeypatch) -> None:
    client = _setup_client(tmp_path, monkeypatch)

    payload = {
        "symbol": "AAPL",
        "strategy": "RSI2",
        "market_type": "stock",
        "lookback_days": 30,
        "preset_ids": ["fast", "slow"],
        "strategy_config": {"oversold_threshold": 15.0},
    }

    response_one = client.post("/strategy/analyze", json=payload)
    response_two = client.post("/strategy/analyze", json=payload)

    assert response_one.status_code == 200
    assert response_two.status_code == 200
    assert response_one.json() == response_two.json()


def test_strategy_analyze_single_preset_backwards_compatible(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _setup_client(tmp_path, monkeypatch)

    payload = {
        "symbol": "AAPL",
        "strategy": "RSI2",
        "market_type": "stock",
        "lookback_days": 30,
        "strategy_config": {"oversold_threshold": 15.0},
    }

    response = client.post("/strategy/analyze", json=payload)

    assert response.status_code == 200
    data = response.json()

    assert data["strategy"] == "RSI2"
    assert isinstance(data["signals"], list)
