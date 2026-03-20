from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import api.main as api_main
from cilly_trading.engine.core import compute_analysis_run_id
from cilly_trading.repositories.analysis_runs_sqlite import SqliteAnalysisRunRepository
from cilly_trading.repositories.signals_sqlite import SqliteSignalRepository

OPERATOR_HEADERS = {api_main.ROLE_HEADER_NAME: "operator"}


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
    payload = {
        "ingestion_run_id": ingestion_run_id,
        "symbol": "AAPL",
        "strategy": "RSI2",
        "market_type": "stock",
        "lookback_days": 200,
    }
    run_request_payload = {
        "ingestion_run_id": ingestion_run_id,
        "symbol": "AAPL",
        "strategy": "RSI2",
        "market_type": "stock",
        "lookback_days": 200,
    }
    expected_run_id = compute_analysis_run_id(run_request_payload)

    response_first = client.post("/analysis/run", headers=OPERATOR_HEADERS, json=payload)
    assert response_first.status_code == 200
    first_body = response_first.json()
    assert first_body["analysis_run_id"] == expected_run_id

    def _fail_run_watchlist_analysis(*args, **kwargs):
        raise AssertionError("run_watchlist_analysis should not be called")

    monkeypatch.setattr(api_main, "run_watchlist_analysis", _fail_run_watchlist_analysis)

    response_second = client.post("/analysis/run", headers=OPERATOR_HEADERS, json=payload)
    assert response_second.status_code == 200
    second_body = response_second.json()
    assert second_body["analysis_run_id"] == expected_run_id
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
        headers=OPERATOR_HEADERS,
        json={
            "ingestion_run_id": "not-a-uuid",
            "symbol": "AAPL",
            "strategy": "RSI2",
            "market_type": "stock",
            "lookback_days": 200,
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "invalid_ingestion_run_id"
    run_request_payload = {
        "ingestion_run_id": "not-a-uuid",
        "symbol": "AAPL",
        "strategy": "RSI2",
        "market_type": "stock",
        "lookback_days": 200,
    }
    expected_run_id = compute_analysis_run_id(run_request_payload)
    assert analysis_repo.get_run(expected_run_id) is None
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
        headers=OPERATOR_HEADERS,
        json={
            "analysis_run_id": "client-run",
            "ingestion_run_id": ingestion_run_id,
            "symbol": "AAPL",
            "strategy": "RSI2",
            "market_type": "stock",
            "lookback_days": 200,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    run_request_payload = {
        "ingestion_run_id": ingestion_run_id,
        "symbol": "AAPL",
        "strategy": "RSI2",
        "market_type": "stock",
        "lookback_days": 200,
    }
    expected_run_id = compute_analysis_run_id(run_request_payload)
    assert payload["analysis_run_id"] == expected_run_id
    assert payload["analysis_run_id"] != "client-run"
    assert payload["ingestion_run_id"] == ingestion_run_id
    assert payload["symbol"] == "AAPL"
    assert payload["strategy"] == "RSI2"
    assert payload["signals"]
    assert analysis_repo.get_run(expected_run_id) is not None
    assert signal_repo.list_signals(limit=10)


def test_manual_analysis_changes_id_for_different_payload(tmp_path: Path, monkeypatch) -> None:
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
    payload_base = {
        "ingestion_run_id": ingestion_run_id,
        "symbol": "AAPL",
        "strategy": "RSI2",
        "market_type": "stock",
    }
    response_first = client.post(
        "/analysis/run",
        headers=OPERATOR_HEADERS,
        json={**payload_base, "lookback_days": 200},
    )
    assert response_first.status_code == 200
    first_body = response_first.json()

    response_second = client.post(
        "/analysis/run",
        headers=OPERATOR_HEADERS,
        json={**payload_base, "lookback_days": 201},
    )
    assert response_second.status_code == 200
    second_body = response_second.json()

    assert first_body["analysis_run_id"] != second_body["analysis_run_id"]


def test_manual_analysis_strategy_config_float_idempotent(
    tmp_path: Path,
    monkeypatch,
) -> None:
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
    payload = {
        "ingestion_run_id": ingestion_run_id,
        "symbol": "AAPL",
        "strategy": "RSI2",
        "market_type": "stock",
        "lookback_days": 200,
        "strategy_config": {"oversold_threshold": 15.0},
    }

    original_run_watchlist_analysis = api_main.run_watchlist_analysis

    response_first = client.post("/analysis/run", headers=OPERATOR_HEADERS, json=payload)
    assert response_first.status_code == 200
    first_body = response_first.json()
    assert first_body["analysis_run_id"]

    def _fail_run_watchlist_analysis(*args, **kwargs):
        raise AssertionError("run_watchlist_analysis should not be called")

    monkeypatch.setattr(api_main, "run_watchlist_analysis", _fail_run_watchlist_analysis)

    response_second = client.post("/analysis/run", headers=OPERATOR_HEADERS, json=payload)
    assert response_second.status_code == 200
    second_body = response_second.json()
    assert second_body["analysis_run_id"] == first_body["analysis_run_id"]

    monkeypatch.setattr(api_main, "run_watchlist_analysis", original_run_watchlist_analysis)

    response_third = client.post(
        "/analysis/run",
        headers=OPERATOR_HEADERS,
        json={
            **payload,
            "strategy_config": {"oversold_threshold": 16.0},
        },
    )
    assert response_third.status_code == 200
    third_body = response_third.json()
    assert third_body["analysis_run_id"] != first_body["analysis_run_id"]


def test_manual_analysis_requires_authenticated_role(tmp_path: Path, monkeypatch) -> None:
    signal_repo = _make_signal_repo(tmp_path)
    analysis_repo = _make_analysis_repo(tmp_path)

    monkeypatch.setattr(api_main, "signal_repo", signal_repo)
    monkeypatch.setattr(api_main, "analysis_run_repo", analysis_repo)

    client = TestClient(api_main.app)
    response = client.post(
        "/analysis/run",
        json={
            "ingestion_run_id": str(uuid.uuid4()),
            "symbol": "AAPL",
            "strategy": "RSI2",
            "market_type": "stock",
            "lookback_days": 200,
        },
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "unauthorized"}


def test_manual_analysis_returns_persisted_result_when_duplicate_save_races(
    tmp_path: Path,
    monkeypatch,
) -> None:
    signal_repo = _make_signal_repo(tmp_path)
    analysis_repo = _make_analysis_repo(tmp_path)
    persisted_lookup = analysis_repo.get_run
    queued_signals = [
        [{"symbol": "AAPL", "strategy": "RSI2", "score": 1.0}],
        [{"symbol": "AAPL", "strategy": "RSI2", "score": 2.0}],
    ]

    monkeypatch.setattr(api_main, "signal_repo", signal_repo)
    monkeypatch.setattr(api_main, "analysis_run_repo", analysis_repo)
    monkeypatch.setattr(api_main, "_require_ingestion_run", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(api_main, "_require_snapshot_ready", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(api_main, "create_strategy", lambda _name: object())
    monkeypatch.setattr(
        api_main,
        "trigger_operator_analysis_run",
        lambda **_kwargs: queued_signals.pop(0),
    )

    state = {"calls": 0}

    def _stale_get_run(run_id: str) -> dict[str, object] | None:
        state["calls"] += 1
        if state["calls"] == 1:
            return None
        if state["calls"] == 2:
            return None
        return persisted_lookup(run_id)

    monkeypatch.setattr(analysis_repo, "get_run", _stale_get_run)

    client = TestClient(api_main.app)
    payload = {
        "ingestion_run_id": str(uuid.uuid4()),
        "symbol": "AAPL",
        "strategy": "RSI2",
        "market_type": "stock",
        "lookback_days": 200,
    }

    first_response = client.post("/analysis/run", headers=OPERATOR_HEADERS, json=payload)
    second_response = client.post("/analysis/run", headers=OPERATOR_HEADERS, json=payload)

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json() == second_response.json()
    assert first_response.json()["signals"] == [{"symbol": "AAPL", "strategy": "RSI2", "score": 1.0}]


def test_analysis_run_repository_duplicate_save_is_idempotent(tmp_path: Path) -> None:
    repo = _make_analysis_repo(tmp_path)
    run_id = "run-001"
    request_payload = {"symbol": "AAPL", "strategy": "RSI2"}
    result_payload = {"analysis_run_id": run_id, "signals": []}

    repo.save_run(
        analysis_run_id=run_id,
        ingestion_run_id="ingestion-001",
        request_payload=request_payload,
        result_payload=result_payload,
    )
    repo.save_run(
        analysis_run_id=run_id,
        ingestion_run_id="ingestion-001",
        request_payload=request_payload,
        result_payload=result_payload,
    )

    saved = repo.get_run(run_id)
    assert saved is not None
    assert saved["ingestion_run_id"] == "ingestion-001"
    assert saved["request"] == request_payload
    assert saved["result"] == result_payload


def test_analysis_run_repository_duplicate_save_reuses_persisted_result_for_same_request(
    tmp_path: Path,
) -> None:
    repo = _make_analysis_repo(tmp_path)
    run_id = "run-001"
    request_payload = {"symbol": "AAPL", "strategy": "RSI2"}
    first_result = {"analysis_run_id": run_id, "signals": []}
    second_result = {"analysis_run_id": run_id, "signals": [{"symbol": "AAPL"}]}

    persisted_first = repo.save_run(
        analysis_run_id=run_id,
        ingestion_run_id="ingestion-001",
        request_payload=request_payload,
        result_payload=first_result,
    )
    persisted_second = repo.save_run(
        analysis_run_id=run_id,
        ingestion_run_id="ingestion-999",
        request_payload=request_payload,
        result_payload=second_result,
    )

    assert persisted_first["result"] == first_result
    assert persisted_second["result"] == first_result
    assert repo.get_run(run_id) == persisted_first


def test_analysis_run_repository_duplicate_save_is_safe_under_concurrent_requests(
    tmp_path: Path,
) -> None:
    repo = _make_analysis_repo(tmp_path)
    run_id = "run-001"
    request_payload = {"symbol": "AAPL", "strategy": "RSI2"}
    result_payload = {"analysis_run_id": run_id, "signals": []}

    def _save() -> dict[str, object]:
        return repo.save_run(
            analysis_run_id=run_id,
            ingestion_run_id="ingestion-001",
            request_payload=request_payload,
            result_payload=result_payload,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        persisted = [future.result() for future in [executor.submit(_save), executor.submit(_save)]]

    assert persisted[0]["result"] == result_payload
    assert persisted[1]["result"] == result_payload

    conn = sqlite3.connect(tmp_path / "analysis.db")
    try:
        row_count = conn.execute("SELECT COUNT(*) FROM analysis_runs WHERE analysis_run_id = ?;", (run_id,)).fetchone()[0]
    finally:
        conn.close()

    assert row_count == 1


def test_analysis_run_repository_rejects_conflicting_duplicate_save(tmp_path: Path) -> None:
    repo = _make_analysis_repo(tmp_path)
    run_id = "run-001"

    repo.save_run(
        analysis_run_id=run_id,
        ingestion_run_id="ingestion-001",
        request_payload={"symbol": "AAPL", "strategy": "RSI2"},
        result_payload={"analysis_run_id": run_id, "signals": []},
    )

    with pytest.raises(ValueError, match="analysis_run_id already exists"):
        repo.save_run(
            analysis_run_id=run_id,
            ingestion_run_id="ingestion-002",
            request_payload={"symbol": "MSFT", "strategy": "RSI2"},
            result_payload={"analysis_run_id": run_id, "signals": [{"symbol": "MSFT"}]},
        )
