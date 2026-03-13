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


READ_ONLY_HEADERS = {api_main.ROLE_HEADER_NAME: "read_only"}
OPERATOR_HEADERS = {api_main.ROLE_HEADER_NAME: "operator"}
OWNER_HEADERS = {api_main.ROLE_HEADER_NAME: "owner"}


def _make_repo(tmp_path: Path) -> SqliteWatchlistRepository:
    return SqliteWatchlistRepository(db_path=tmp_path / "watchlists.db")


def _make_analysis_repo(tmp_path: Path) -> SqliteAnalysisRunRepository:
    return SqliteAnalysisRunRepository(db_path=tmp_path / "analysis.db")


def _make_signal_repo(tmp_path: Path) -> SqliteSignalRepository:
    return SqliteSignalRepository(db_path=tmp_path / "signals.db")


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
        score = float(last_row["volume"])
        signal_strength = float(last_row["close"])
        return [{"score": score, "signal_strength": signal_strength, "stage": "setup"}]


class _NoSignalStrategy:
    name = "WATCHLIST_FAKE"

    def generate_signals(self, df: Any, config: dict[str, Any]) -> list[dict[str, Any]]:
        return []


def test_watchlist_create_endpoint_persists_and_reads_back(tmp_path: Path, monkeypatch) -> None:
    repo = _make_repo(tmp_path)
    monkeypatch.setattr(api_main, "watchlist_repo", repo)
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")

    with TestClient(api_main.app) as client:
        create_response = client.post(
            "/watchlists",
            headers=OPERATOR_HEADERS,
            json={
                "watchlist_id": "tech-growth",
                "name": "Tech Growth",
                "symbols": ["NVDA", "MSFT", "AAPL"],
            },
        )
        read_response = client.get(
            "/watchlists/tech-growth",
            headers=READ_ONLY_HEADERS,
        )

    assert create_response.status_code == 200
    assert create_response.json() == {
        "watchlist_id": "tech-growth",
        "name": "Tech Growth",
        "symbols": ["NVDA", "MSFT", "AAPL"],
    }

    assert read_response.status_code == 200
    assert read_response.json() == create_response.json()


def test_watchlist_list_endpoint_is_deterministic(tmp_path: Path, monkeypatch) -> None:
    repo = _make_repo(tmp_path)
    repo.create_watchlist(
        watchlist_id="beta-list",
        name="Beta",
        symbols=["TSLA", "META"],
    )
    repo.create_watchlist(
        watchlist_id="alpha-list",
        name="Alpha",
        symbols=["MSFT", "AAPL"],
    )
    monkeypatch.setattr(api_main, "watchlist_repo", repo)
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")

    with TestClient(api_main.app) as client:
        response = client.get("/watchlists", headers=READ_ONLY_HEADERS)

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "watchlist_id": "alpha-list",
                "name": "Alpha",
                "symbols": ["MSFT", "AAPL"],
            },
            {
                "watchlist_id": "beta-list",
                "name": "Beta",
                "symbols": ["TSLA", "META"],
            },
        ],
        "total": 2,
    }


def test_watchlist_update_endpoint_allows_owner_and_replaces_membership(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _make_repo(tmp_path)
    repo.create_watchlist(
        watchlist_id="swing-core",
        name="Swing Core",
        symbols=["AAPL", "MSFT"],
    )
    monkeypatch.setattr(api_main, "watchlist_repo", repo)
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")

    with TestClient(api_main.app) as client:
        response = client.put(
            "/watchlists/swing-core",
            headers=OWNER_HEADERS,
            json={
                "name": "Swing Updated",
                "symbols": ["NVDA", "AMD", "AAPL"],
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "watchlist_id": "swing-core",
        "name": "Swing Updated",
        "symbols": ["NVDA", "AMD", "AAPL"],
    }


def test_watchlist_delete_endpoint_removes_watchlist(tmp_path: Path, monkeypatch) -> None:
    repo = _make_repo(tmp_path)
    repo.create_watchlist(
        watchlist_id="to-delete",
        name="Delete Me",
        symbols=["BTC/USDT"],
    )
    monkeypatch.setattr(api_main, "watchlist_repo", repo)
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")

    with TestClient(api_main.app) as client:
        delete_response = client.delete(
            "/watchlists/to-delete",
            headers=OPERATOR_HEADERS,
        )
        read_response = client.get(
            "/watchlists/to-delete",
            headers=READ_ONLY_HEADERS,
        )

    assert delete_response.status_code == 200
    assert delete_response.json() == {
        "watchlist_id": "to-delete",
        "deleted": True,
    }
    assert read_response.status_code == 404
    assert read_response.json() == {"detail": "watchlist_not_found"}


def test_watchlist_create_rejects_invalid_payload_without_persisting(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _make_repo(tmp_path)
    monkeypatch.setattr(api_main, "watchlist_repo", repo)
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")

    with TestClient(api_main.app) as client:
        response = client.post(
            "/watchlists",
            headers=OPERATOR_HEADERS,
            json={
                "watchlist_id": "broken-list",
                "name": "Broken",
                "symbols": ["AAPL", " "],
            },
        )

    assert response.status_code == 422
    assert response.json() == {"detail": "watchlist symbols must not contain empty values"}
    assert repo.get_watchlist("broken-list") is None
    assert repo.list_watchlists() == []


def test_watchlist_update_rejects_invalid_payload_without_partial_persistence(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _make_repo(tmp_path)
    repo.create_watchlist(
        watchlist_id="core-list",
        name="Core",
        symbols=["AAPL", "MSFT"],
    )
    monkeypatch.setattr(api_main, "watchlist_repo", repo)
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")

    with TestClient(api_main.app) as client:
        response = client.put(
            "/watchlists/core-list",
            headers=OPERATOR_HEADERS,
            json={
                "name": "Core",
                "symbols": ["NVDA", "NVDA"],
            },
        )

    assert response.status_code == 422
    assert response.json() == {"detail": "watchlist name and symbols must remain unique"}

    stored = repo.get_watchlist("core-list")
    assert stored is not None
    assert stored.name == "Core"
    assert stored.symbols == ("AAPL", "MSFT")


def test_watchlist_endpoints_require_authenticated_role(tmp_path: Path, monkeypatch) -> None:
    repo = _make_repo(tmp_path)
    monkeypatch.setattr(api_main, "watchlist_repo", repo)
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")

    with TestClient(api_main.app) as client:
        response = client.get("/watchlists")

    assert response.status_code == 401
    assert response.json() == {"detail": "unauthorized"}


def test_watchlist_mutations_forbid_read_only_role(tmp_path: Path, monkeypatch) -> None:
    repo = _make_repo(tmp_path)
    monkeypatch.setattr(api_main, "watchlist_repo", repo)
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")

    with TestClient(api_main.app) as client:
        response = client.post(
            "/watchlists",
            headers=READ_ONLY_HEADERS,
            json={
                "watchlist_id": "read-only-write",
                "name": "Read Only",
                "symbols": ["AAPL"],
            },
        )

    assert response.status_code == 403
    assert response.json() == {"detail": "forbidden"}
    assert repo.list_watchlists() == []


def test_watchlist_execute_returns_deterministic_ranked_results(
    tmp_path: Path, monkeypatch
) -> None:
    watchlist_repository = _make_repo(tmp_path)
    watchlist_repository.create_watchlist(
        watchlist_id="ranked-tech",
        name="Ranked Tech",
        symbols=["BBB", "AAA", "AAC"],
    )
    analysis_repo = _make_analysis_repo(tmp_path)
    signal_repo = _make_signal_repo(tmp_path)
    ingestion_run_id = str(uuid.uuid4())
    _insert_ingestion_run(
        tmp_path / "analysis.db",
        ingestion_run_id,
        symbols=["AAA", "AAC", "BBB"],
    )
    _insert_snapshot_rows(
        tmp_path / "analysis.db",
        ingestion_run_id,
        "AAA",
        "D1",
        [(1735689600000, 1.0, 2.0, 0.5, 0.6, 80.0)],
    )
    _insert_snapshot_rows(
        tmp_path / "analysis.db",
        ingestion_run_id,
        "AAC",
        "D1",
        [(1735689600000, 1.0, 2.0, 0.5, 0.7, 80.0)],
    )
    _insert_snapshot_rows(
        tmp_path / "analysis.db",
        ingestion_run_id,
        "BBB",
        "D1",
        [(1735689600000, 1.0, 2.0, 0.5, 0.9, 75.0)],
    )

    monkeypatch.setattr(api_main, "watchlist_repo", watchlist_repository)
    monkeypatch.setattr(api_main, "analysis_run_repo", analysis_repo)
    monkeypatch.setattr(api_main, "signal_repo", signal_repo)
    monkeypatch.setattr(api_main, "create_registered_strategies", lambda: [_ScoreFromCloseStrategy()])
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")
    monkeypatch.setattr(api_main, "_require_engine_runtime_running", lambda: None)

    with TestClient(api_main.app) as client:
        response = client.post(
            "/watchlists/ranked-tech/execute",
            headers=OPERATOR_HEADERS,
            json={
                "ingestion_run_id": ingestion_run_id,
                "market_type": "stock",
                "lookback_days": 200,
                "min_score": 70.0,
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["watchlist_id"] == "ranked-tech"
    assert payload["watchlist_name"] == "Ranked Tech"
    assert [item["symbol"] for item in payload["ranked_results"]] == ["AAC", "AAA", "BBB"]
    assert [item["rank"] for item in payload["ranked_results"]] == [1, 2, 3]
    assert payload["failures"] == []


def test_watchlist_execute_returns_empty_results_when_no_signals(
    tmp_path: Path, monkeypatch
) -> None:
    watchlist_repository = _make_repo(tmp_path)
    watchlist_repository.create_watchlist(
        watchlist_id="empty-watchlist",
        name="Empty Watchlist",
        symbols=["AAPL"],
    )
    analysis_repo = _make_analysis_repo(tmp_path)
    signal_repo = _make_signal_repo(tmp_path)
    ingestion_run_id = str(uuid.uuid4())
    _insert_ingestion_run(tmp_path / "analysis.db", ingestion_run_id, symbols=["AAPL"])
    _insert_snapshot_rows(
        tmp_path / "analysis.db",
        ingestion_run_id,
        "AAPL",
        "D1",
        [(1735689600000, 1.0, 2.0, 0.5, 1.0, 20.0)],
    )

    monkeypatch.setattr(api_main, "watchlist_repo", watchlist_repository)
    monkeypatch.setattr(api_main, "analysis_run_repo", analysis_repo)
    monkeypatch.setattr(api_main, "signal_repo", signal_repo)
    monkeypatch.setattr(api_main, "create_registered_strategies", lambda: [_NoSignalStrategy()])
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")
    monkeypatch.setattr(api_main, "_require_engine_runtime_running", lambda: None)

    with TestClient(api_main.app) as client:
        response = client.post(
            "/watchlists/empty-watchlist/execute",
            headers=OPERATOR_HEADERS,
            json={
                "ingestion_run_id": ingestion_run_id,
                "market_type": "stock",
                "lookback_days": 200,
                "min_score": 30.0,
            },
        )

    assert response.status_code == 200
    assert response.json()["ranked_results"] == []
    assert response.json()["failures"] == []


def test_watchlist_execute_isolates_partial_symbol_failures(
    tmp_path: Path, monkeypatch
) -> None:
    watchlist_repository = _make_repo(tmp_path)
    watchlist_repository.create_watchlist(
        watchlist_id="partial-watchlist",
        name="Partial Watchlist",
        symbols=["MSFT", "AAPL"],
    )
    analysis_repo = _make_analysis_repo(tmp_path)
    signal_repo = _make_signal_repo(tmp_path)
    ingestion_run_id = str(uuid.uuid4())
    _insert_ingestion_run(
        tmp_path / "analysis.db",
        ingestion_run_id,
        symbols=["AAPL", "MSFT"],
    )
    _insert_snapshot_rows(
        tmp_path / "analysis.db",
        ingestion_run_id,
        "AAPL",
        "D1",
        [(1735689600000, 1.0, 2.0, 0.5, 0.8, 75.0)],
    )

    monkeypatch.setattr(api_main, "watchlist_repo", watchlist_repository)
    monkeypatch.setattr(api_main, "analysis_run_repo", analysis_repo)
    monkeypatch.setattr(api_main, "signal_repo", signal_repo)
    monkeypatch.setattr(api_main, "create_registered_strategies", lambda: [_ScoreFromCloseStrategy()])
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")
    monkeypatch.setattr(api_main, "_require_engine_runtime_running", lambda: None)

    with TestClient(api_main.app) as client:
        response = client.post(
            "/watchlists/partial-watchlist/execute",
            headers=OPERATOR_HEADERS,
            json={
                "ingestion_run_id": ingestion_run_id,
                "market_type": "stock",
                "lookback_days": 200,
                "min_score": 30.0,
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert [item["symbol"] for item in payload["ranked_results"]] == ["AAPL"]
    assert payload["failures"] == [
        {
            "symbol": "MSFT",
            "code": "snapshot_data_invalid",
            "detail": "snapshot data unavailable or invalid for symbol",
        }
    ]


def test_screener_basic_ranking_is_not_regressed_by_watchlist_execution_changes(
    monkeypatch,
) -> None:
    signals = [
        {
            "symbol": "BBB",
            "stage": "setup",
            "score": 50,
            "signal_strength": 0.5,
            "strategy": "RSI2",
        },
        {
            "symbol": "AAA",
            "stage": "setup",
            "score": 50,
            "signal_strength": 0.7,
            "strategy": "RSI2",
        },
        {
            "symbol": "AAC",
            "stage": "setup",
            "score": 50,
            "signal_strength": 0.7,
            "strategy": "TURTLE",
        },
    ]

    monkeypatch.setattr(api_main, "_require_ingestion_run", lambda *_: None)
    monkeypatch.setattr(api_main, "_require_snapshot_ready", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(api_main, "_run_snapshot_analysis", lambda **_kwargs: signals)

    response = api_main.basic_screener(
        api_main.ScreenerRequest(
            ingestion_run_id="11111111-1111-4111-8111-111111111111",
            symbols=["BBB", "AAA", "AAC"],
            market_type="stock",
            lookback_days=200,
            min_score=0.0,
        )
    )

    assert [item.symbol for item in response.symbols] == ["AAA", "AAC", "BBB"]
