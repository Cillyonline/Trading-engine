from __future__ import annotations

import json
import sqlite3
import uuid
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
    created_at: str = "2024-01-01T00:00:00+00:00",
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
            created_at,
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


def test_strategy_analyze_requires_ingestion_run_id() -> None:
    client = TestClient(api_main.app)
    response = client.post(
        "/strategy/analyze",
        json={
            "symbol": "AAPL",
            "strategy": "RSI2",
            "market_type": "stock",
            "lookback_days": 200,
        },
    )

    assert response.status_code == 422


def test_screener_basic_requires_ingestion_run_id() -> None:
    client = TestClient(api_main.app)
    response = client.post(
        "/screener/basic",
        json={
            "market_type": "stock",
            "lookback_days": 200,
            "min_score": 30.0,
        },
    )

    assert response.status_code == 422


def test_strategy_analyze_accepts_valid_ingestion_run_id(tmp_path: Path, monkeypatch) -> None:
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
        "/strategy/analyze",
        json={
            "ingestion_run_id": ingestion_run_id,
            "symbol": "AAPL",
            "strategy": "RSI2",
            "market_type": "stock",
            "lookback_days": 200,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "AAPL"
    assert payload["strategy"] == "RSI2"
    assert "signals" in payload


def test_strategy_analyze_rejects_missing_snapshot(tmp_path: Path, monkeypatch) -> None:
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

    def _fail_yahoo(*args, **kwargs):
        raise AssertionError("yfinance should not be called")

    def _fail_binance(*args, **kwargs):
        raise AssertionError("ccxt should not be called")

    monkeypatch.setattr("cilly_trading.engine.data._load_stock_yahoo", _fail_yahoo)
    monkeypatch.setattr("cilly_trading.engine.data._load_crypto_binance", _fail_binance)

    client = TestClient(api_main.app)
    response = client.post(
        "/strategy/analyze",
        json={
            "ingestion_run_id": ingestion_run_id,
            "symbol": "AAPL",
            "strategy": "RSI2",
            "market_type": "stock",
            "lookback_days": 200,
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "ingestion_run_not_ready"


def test_strategy_analyze_rejects_invalid_snapshot_rows(tmp_path: Path, monkeypatch) -> None:
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

    _insert_snapshot_rows(
        tmp_path / "analysis.db",
        ingestion_run_id,
        "AAPL",
        "D1",
        [("bad-ts", 101.0, 102.0, 100.0, 101.0, 1000.0)],
    )

    def _fail_yahoo(*args, **kwargs):
        raise AssertionError("yfinance should not be called")

    def _fail_binance(*args, **kwargs):
        raise AssertionError("ccxt should not be called")

    monkeypatch.setattr("cilly_trading.engine.data._load_stock_yahoo", _fail_yahoo)
    monkeypatch.setattr("cilly_trading.engine.data._load_crypto_binance", _fail_binance)

    client = TestClient(api_main.app)
    response = client.post(
        "/strategy/analyze",
        json={
            "ingestion_run_id": ingestion_run_id,
            "symbol": "AAPL",
            "strategy": "RSI2",
            "market_type": "stock",
            "lookback_days": 200,
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "snapshot_data_invalid"


def test_screener_basic_rejects_partial_snapshots(tmp_path: Path, monkeypatch) -> None:
    signal_repo = _make_signal_repo(tmp_path)
    analysis_repo = _make_analysis_repo(tmp_path)

    monkeypatch.setattr(api_main, "signal_repo", signal_repo)
    monkeypatch.setattr(api_main, "analysis_run_repo", analysis_repo)

    ingestion_run_id = str(uuid.uuid4())
    _insert_ingestion_run(
        tmp_path / "analysis.db",
        ingestion_run_id,
        symbols=["AAPL", "MSFT"],
        timeframe="D1",
    )

    rows = [
        (1735689600000, 101.0, 102.0, 100.0, 101.0, 1000.0),
        (1735776000000, 100.0, 101.0, 90.0, 91.0, 1000.0),
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
        "/screener/basic",
        json={
            "ingestion_run_id": ingestion_run_id,
            "market_type": "stock",
            "lookback_days": 200,
            "min_score": 30.0,
            "symbols": ["AAPL", "MSFT"],
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "ingestion_run_not_ready"


def test_screener_basic_accepts_ready_snapshots(tmp_path: Path, monkeypatch) -> None:
    signal_repo = _make_signal_repo(tmp_path)
    analysis_repo = _make_analysis_repo(tmp_path)

    monkeypatch.setattr(api_main, "signal_repo", signal_repo)
    monkeypatch.setattr(api_main, "analysis_run_repo", analysis_repo)

    ingestion_run_id = str(uuid.uuid4())
    _insert_ingestion_run(
        tmp_path / "analysis.db",
        ingestion_run_id,
        symbols=["AAPL", "MSFT"],
        timeframe="D1",
    )

    rows = [
        (1735689600000, 101.0, 102.0, 100.0, 101.0, 1000.0),
        (1735776000000, 100.0, 101.0, 90.0, 91.0, 1000.0),
    ]
    for symbol in ["AAPL", "MSFT"]:
        _insert_snapshot_rows(
            tmp_path / "analysis.db",
            ingestion_run_id,
            symbol,
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
        "/screener/basic",
        json={
            "ingestion_run_id": ingestion_run_id,
            "market_type": "stock",
            "lookback_days": 200,
            "min_score": 30.0,
            "symbols": ["AAPL", "MSFT"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["market_type"] == "stock"


def test_manual_analysis_rejects_missing_snapshot(tmp_path: Path, monkeypatch) -> None:
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

    client = TestClient(api_main.app)
    response = client.post(
        "/analysis/run",
        json={
            "ingestion_run_id": ingestion_run_id,
            "symbol": "AAPL",
            "strategy": "RSI2",
            "market_type": "stock",
            "lookback_days": 200,
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "ingestion_run_not_ready"


def test_manual_analysis_rejects_invalid_snapshot_rows(tmp_path: Path, monkeypatch) -> None:
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

    _insert_snapshot_rows(
        tmp_path / "analysis.db",
        ingestion_run_id,
        "AAPL",
        "D1",
        [("bad-ts", 101.0, 102.0, 100.0, 101.0, 1000.0)],
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
            "ingestion_run_id": ingestion_run_id,
            "symbol": "AAPL",
            "strategy": "RSI2",
            "market_type": "stock",
            "lookback_days": 200,
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "snapshot_data_invalid"


def test_manual_analysis_accepts_ready_snapshot(tmp_path: Path, monkeypatch) -> None:
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
            "ingestion_run_id": ingestion_run_id,
            "symbol": "AAPL",
            "strategy": "RSI2",
            "market_type": "stock",
            "lookback_days": 200,
        },
    )

    assert response.status_code == 200
