from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

import api.main as api_main
from cilly_trading.repositories.analysis_runs_sqlite import SqliteAnalysisRunRepository
from cilly_trading.repositories.signals_sqlite import SqliteSignalRepository


def _make_signal_repo(tmp_path: Path) -> SqliteSignalRepository:
    return SqliteSignalRepository(db_path=tmp_path / "signals.db")


def _make_analysis_repo(tmp_path: Path) -> SqliteAnalysisRunRepository:
    return SqliteAnalysisRunRepository(db_path=tmp_path / "analysis.db")


def _insert_ingestion_run(
    db_path: Path,
    ingestion_run_id: str,
    *,
    symbols: list[str],
    timeframe: str = "D1",
    source: str = "test",
    fingerprint_hash: str | None = None,
) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        INSERT INTO ingestion_runs (
            ingestion_run_id,
            created_at,
            source,
            symbols_json,
            timeframe,
            fingerprint_hash
        )
        VALUES (?, ?, ?, ?, ?, ?);
        """,
        (
            ingestion_run_id,
            datetime.now(timezone.utc).isoformat(),
            source,
            json.dumps(symbols),
            timeframe,
            fingerprint_hash,
        ),
    )
    conn.commit()
    conn.close()


def _insert_snapshot_rows(
    db_path: Path,
    ingestion_run_id: str,
    symbol: str,
    timeframe: str,
    rows: list[tuple[int, float, float, float, float, float]],
) -> None:
    conn = sqlite3.connect(db_path)
    conn.executemany(
        """
        INSERT INTO ohlcv_snapshots (
            ingestion_run_id,
            symbol,
            timeframe,
            ts,
            open,
            high,
            low,
            close,
            volume
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        [
            (
                ingestion_run_id,
                symbol,
                timeframe,
                ts,
                open_,
                high,
                low,
                close,
                volume,
            )
            for ts, open_, high, low, close, volume in rows
        ],
    )
    conn.commit()
    conn.close()


def test_manual_analysis_idempotent(tmp_path: Path, monkeypatch) -> None:
    signal_repo = _make_signal_repo(tmp_path)
    analysis_repo = _make_analysis_repo(tmp_path)

    monkeypatch.setattr(api_main, "signal_repo", signal_repo)
    monkeypatch.setattr(api_main, "analysis_run_repo", analysis_repo)

    def _fail_run_watchlist_analysis(*args, **kwargs):
        raise AssertionError("run_watchlist_analysis should not be called")

    monkeypatch.setattr(api_main, "run_watchlist_analysis", _fail_run_watchlist_analysis)

    ingestion_run_id = str(uuid.uuid4())
    _insert_ingestion_run(
        tmp_path / "analysis.db",
        ingestion_run_id,
        symbols=["AAPL"],
        timeframe="D1",
    )

    response_payload = {
        "analysis_run_id": "run-1",
        "ingestion_run_id": ingestion_run_id,
        "symbol": "AAPL",
        "strategy": "RSI2",
        "signals": [
            {
                "symbol": "AAPL",
                "strategy": "RSI2",
                "direction": "long",
                "score": 42.0,
                "timestamp": "2025-01-03T00:00:00+00:00",
                "stage": "setup",
                "timeframe": "D1",
                "market_type": "stock",
                "data_source": "yahoo",
            }
        ],
    }
    analysis_repo.save_run(
        analysis_run_id="run-1",
        ingestion_run_id=ingestion_run_id,
        request_payload={"analysis_run_id": "run-1", "ingestion_run_id": ingestion_run_id},
        result_payload=response_payload,
    )

    client = TestClient(api_main.app)
    payload = {
        "analysis_run_id": "run-1",
        "ingestion_run_id": ingestion_run_id,
        "symbol": "AAPL",
        "strategy": "RSI2",
        "market_type": "stock",
        "lookback_days": 200,
    }

    response_first = client.post("/analysis/run", json=payload)
    assert response_first.status_code == 200
    first_body = response_first.json()
    assert first_body["analysis_run_id"] == "run-1"
    assert first_body == response_payload

    response_second = client.post("/analysis/run", json=payload)
    assert response_second.status_code == 200
    second_body = response_second.json()
    assert second_body == first_body


def test_manual_analysis_rejects_invalid_ingestion_run(tmp_path: Path, monkeypatch) -> None:
    signal_repo = _make_signal_repo(tmp_path)
    analysis_repo = _make_analysis_repo(tmp_path)

    monkeypatch.setattr(api_main, "signal_repo", signal_repo)
    monkeypatch.setattr(api_main, "analysis_run_repo", analysis_repo)

    def _fail_run_watchlist_analysis(*args, **kwargs):
        raise AssertionError("run_watchlist_analysis should not be called")

    monkeypatch.setattr(api_main, "run_watchlist_analysis", _fail_run_watchlist_analysis)

    client = TestClient(api_main.app)
    response = client.post(
        "/analysis/run",
        json={
            "analysis_run_id": "run-missing",
            "ingestion_run_id": "not-a-uuid",
            "symbol": "AAPL",
            "strategy": "RSI2",
            "market_type": "stock",
            "lookback_days": 200,
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "invalid_ingestion_run_id"
    assert analysis_repo.get_run("run-missing") is None
    assert signal_repo.list_signals(limit=10) == []


def test_manual_analysis_uses_snapshot(tmp_path: Path, monkeypatch) -> None:
    signal_repo = _make_signal_repo(tmp_path)
    analysis_repo = _make_analysis_repo(tmp_path)

    monkeypatch.setattr(api_main, "signal_repo", signal_repo)
    monkeypatch.setattr(api_main, "analysis_run_repo", analysis_repo)

    ingestion_run_id = str(uuid.uuid4())
    _insert_ingestion_run(
        tmp_path / "analysis.db",
        ingestion_run_id,
        symbols=["AAPL"],
        timeframe="D1",
    )

    rows = [
        (1735689600000, 101.0, 102.0, 100.0, 101.0, 1000.0),
        (1735776000000, 100.0, 101.0, 90.0, 91.0, 1000.0),
        (1735862400000, 90.0, 91.0, 80.0, 81.0, 1000.0),
    ]
    _insert_snapshot_rows(
        tmp_path / "analysis.db",
        ingestion_run_id,
        "AAPL",
        "D1",
        rows,
    )

    def _fail_yahoo(*args, **kwargs):
        raise AssertionError("yfinance should not be called")

    def _fail_binance(*args, **kwargs):
        raise AssertionError("ccxt should not be called")

    monkeypatch.setattr("cilly_trading.engine.data._load_stock_yahoo", _fail_yahoo)
    monkeypatch.setattr("cilly_trading.engine.data._load_crypto_binance", _fail_binance)

    client = TestClient(api_main.app)
    response = client.post(
        "/analysis/run",
        json={
            "analysis_run_id": "run-snapshot",
            "ingestion_run_id": ingestion_run_id,
            "symbol": "AAPL",
            "strategy": "RSI2",
            "market_type": "stock",
            "lookback_days": 200,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["analysis_run_id"] == "run-snapshot"
    assert payload["ingestion_run_id"] == ingestion_run_id
    assert payload["symbol"] == "AAPL"
    assert payload["strategy"] == "RSI2"
    assert payload["signals"]
    assert analysis_repo.get_run("run-snapshot") is not None
    assert signal_repo.list_signals(limit=10)
