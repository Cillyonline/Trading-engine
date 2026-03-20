from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

import api.main as api_main
from cilly_trading.repositories.analysis_runs_sqlite import SqliteAnalysisRunRepository
from cilly_trading.repositories.signals_sqlite import SqliteSignalRepository
from cilly_trading.repositories.watchlists_sqlite import SqliteWatchlistRepository

OPERATOR_HEADERS = {api_main.ROLE_HEADER_NAME: "operator"}
READ_ONLY_HEADERS = {api_main.ROLE_HEADER_NAME: "read_only"}


class _RuntimeControllerStub:
    def __init__(self, state: str) -> None:
        self.state = state


def _make_signal_repo(tmp_path: Path) -> SqliteSignalRepository:
    return SqliteSignalRepository(db_path=tmp_path / "signals.db")


def _make_analysis_repo(tmp_path: Path) -> SqliteAnalysisRunRepository:
    return SqliteAnalysisRunRepository(db_path=tmp_path / "analysis.db")


def _make_watchlist_repo(tmp_path: Path) -> SqliteWatchlistRepository:
    return SqliteWatchlistRepository(db_path=tmp_path / "watchlists.db")


def _insert_ingestion_run(
    db_path: Path,
    ingestion_run_id: str,
    *,
    symbols: list[str],
    timeframe: str = "D1",
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
            "test",
            json.dumps(symbols),
            timeframe,
            None,
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


class _ScoreFromCloseStrategy:
    name = "WATCHLIST_FAKE"

    def generate_signals(self, df: Any, config: dict[str, Any]) -> list[dict[str, Any]]:
        last_row = df.iloc[-1]
        return [
            {
                "score": float(last_row["volume"]),
                "signal_strength": float(last_row["close"]),
                "stage": "setup",
            }
        ]


def test_ui_browser_flow_uses_existing_runtime_api_surface(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")
    monkeypatch.setattr(api_main, "get_runtime_controller", lambda: _RuntimeControllerStub("running"))
    signal_repo = _make_signal_repo(tmp_path)
    analysis_repo = _make_analysis_repo(tmp_path)
    watchlist_repo = _make_watchlist_repo(tmp_path)

    monkeypatch.setattr(api_main, "signal_repo", signal_repo)
    monkeypatch.setattr(api_main, "analysis_run_repo", analysis_repo)
    monkeypatch.setattr(api_main, "watchlist_repo", watchlist_repo)
    monkeypatch.setattr(api_main, "_require_engine_runtime_running", lambda: None)
    monkeypatch.setattr(api_main, "create_registered_strategies", lambda: [_ScoreFromCloseStrategy()])

    ingestion_run_id = str(uuid.uuid4())
    _insert_ingestion_run(
        tmp_path / "analysis.db",
        ingestion_run_id,
        symbols=["AAPL", "MSFT", "NVDA"],
    )
    _insert_snapshot_rows(
        tmp_path / "analysis.db",
        ingestion_run_id,
        "AAPL",
        "D1",
        [
            (1735689600000, 101.0, 102.0, 100.0, 101.0, 1000.0),
            (1735776000000, 100.0, 101.0, 90.0, 91.0, 1000.0),
            (1735862400000, 90.0, 91.0, 80.0, 81.0, 1000.0),
        ],
    )
    _insert_snapshot_rows(
        tmp_path / "analysis.db",
        ingestion_run_id,
        "MSFT",
        "D1",
        [
            (1735689600000, 201.0, 202.0, 200.0, 201.0, 70.0),
            (1735776000000, 205.0, 206.0, 204.0, 205.0, 72.0),
        ],
    )
    _insert_snapshot_rows(
        tmp_path / "analysis.db",
        ingestion_run_id,
        "NVDA",
        "D1",
        [
            (1735689600000, 301.0, 302.0, 300.0, 301.0, 95.0),
            (1735776000000, 306.0, 307.0, 305.0, 306.0, 96.0),
        ],
    )

    monkeypatch.setattr(
        api_main,
        "get_system_state_payload",
        lambda: {
            "schema_version": "v1",
            "status": "running",
                "runtime": {
                    "schema_version": "v1",
                    "runtime_id": "runtime-ui-flow",
                    "mode": "running",
                    "timestamps": {
                        "started_at": "2025-01-01T00:00:00+00:00",
                        "updated_at": "2025-01-01T00:00:00+00:00",
                    },
                    "ownership": {"owner_tag": "engine"},
                    "extensions": [],
                },
            "metadata": {
                "read_only": True,
                "source": "engine_control_plane",
            },
        },
    )

    def _fail_yahoo(*args, **kwargs):
        raise AssertionError("yfinance should not be called")

    def _fail_binance(*args, **kwargs):
        raise AssertionError("ccxt should not be called")

    monkeypatch.setattr("cilly_trading.engine.data._load_stock_yahoo", _fail_yahoo)
    monkeypatch.setattr("cilly_trading.engine.data._load_crypto_binance", _fail_binance)

    with TestClient(api_main.app) as client:
        ui_response = client.get("/ui")
        assert ui_response.status_code == 200
        assert "/system/state" in ui_response.text
        assert 'roleHeaderName="X-Cilly-Role"' in ui_response.text
        assert 'readOnlyHeaders={[roleHeaderName]:"read_only"}' in ui_response.text
        assert 'operatorHeaders={[roleHeaderName]:"operator"}' in ui_response.text
        assert "/analysis/run" in ui_response.text
        assert "/alerts/history" in ui_response.text
        assert 'id="alert-status"' in ui_response.text
        assert 'id="alert-list"' in ui_response.text
        assert "/signals?limit=20&sort=created_at_desc" in ui_response.text
        assert "/watchlists" in ui_response.text
        assert "/watchlists/{watchlist_id}" in ui_response.text
        assert "/watchlists/{watchlist_id}/execute" in ui_response.text
        assert 'id="watchlist-form"' in ui_response.text
        assert 'id="watchlist-ranked-result-list"' in ui_response.text

        state_response = client.get("/system/state", headers=READ_ONLY_HEADERS)
        assert state_response.status_code == 200
        assert state_response.json()["status"] == "running"

        analysis_response = client.post(
            "/analysis/run",
            headers=OPERATOR_HEADERS,
            json={
                "ingestion_run_id": ingestion_run_id,
                "symbol": "AAPL",
                "strategy": "RSI2",
                "market_type": "stock",
                "lookback_days": 200,
            },
        )
        assert analysis_response.status_code == 200
        analysis_payload = analysis_response.json()
        assert analysis_payload["analysis_run_id"]
        assert analysis_payload["signals"]

        signals_response = client.get(
            "/signals",
            headers=READ_ONLY_HEADERS,
            params={
                "ingestion_run_id": ingestion_run_id,
                "symbol": "AAPL",
                "sort": "created_at_desc",
            },
        )
        assert signals_response.status_code == 200
        signals_payload = signals_response.json()
        assert signals_payload["total"] >= 1
        assert any(item["symbol"] == "AAPL" for item in signals_payload["items"])

        create_watchlist_response = client.post(
            "/watchlists",
            headers=OPERATOR_HEADERS,
            json={
                "watchlist_id": "phase37-tech",
                "name": "Phase 37 Tech",
                "symbols": ["MSFT", "NVDA"],
            },
        )
        assert create_watchlist_response.status_code == 200
        assert create_watchlist_response.json()["watchlist_id"] == "phase37-tech"

        list_watchlists_response = client.get("/watchlists", headers=READ_ONLY_HEADERS)
        assert list_watchlists_response.status_code == 200
        assert list_watchlists_response.json()["total"] == 1

        update_watchlist_response = client.put(
            "/watchlists/phase37-tech",
            headers=OPERATOR_HEADERS,
            json={
                "name": "Phase 37 Ranked Tech",
                "symbols": ["NVDA", "MSFT"],
            },
        )
        assert update_watchlist_response.status_code == 200
        assert update_watchlist_response.json()["name"] == "Phase 37 Ranked Tech"

        read_watchlist_response = client.get(
            "/watchlists/phase37-tech",
            headers=READ_ONLY_HEADERS,
        )
        assert read_watchlist_response.status_code == 200
        assert read_watchlist_response.json()["symbols"] == ["NVDA", "MSFT"]

        execute_watchlist_response = client.post(
            "/watchlists/phase37-tech/execute",
            headers=OPERATOR_HEADERS,
            json={
                "ingestion_run_id": ingestion_run_id,
                "market_type": "stock",
                "lookback_days": 200,
                "min_score": 60.0,
            },
        )
        assert execute_watchlist_response.status_code == 200
        execute_payload = execute_watchlist_response.json()
        assert execute_payload["watchlist_id"] == "phase37-tech"
        assert execute_payload["watchlist_name"] == "Phase 37 Ranked Tech"
        assert [item["symbol"] for item in execute_payload["ranked_results"]] == ["NVDA", "MSFT"]
        assert [item["rank"] for item in execute_payload["ranked_results"]] == [1, 2]
        assert execute_payload["failures"] == []

        delete_watchlist_response = client.delete(
            "/watchlists/phase37-tech",
            headers=OPERATOR_HEADERS,
        )
        assert delete_watchlist_response.status_code == 200
        assert delete_watchlist_response.json() == {
            "watchlist_id": "phase37-tech",
            "deleted": True,
        }
