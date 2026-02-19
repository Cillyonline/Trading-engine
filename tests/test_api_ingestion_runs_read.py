from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

import api.main as api_main
from cilly_trading.repositories.analysis_runs_sqlite import SqliteAnalysisRunRepository


def _insert_ingestion_run(
    db_path: Path,
    *,
    ingestion_run_id: str,
    created_at: str,
    symbols_json: str,
) -> None:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO ingestion_runs (
            ingestion_run_id,
            created_at,
            source,
            symbols_json,
            timeframe,
            fingerprint_hash
        )
        VALUES (?, ?, 'test-source', ?, 'D1', ?);
        """,
        (ingestion_run_id, created_at, symbols_json, ingestion_run_id),
    )
    conn.commit()
    conn.close()


def test_ingestion_runs_ordering_and_limit(monkeypatch, tmp_path: Path) -> None:
    repo = SqliteAnalysisRunRepository(db_path=tmp_path / "ingestion_runs.db")
    monkeypatch.setattr(api_main, "analysis_run_repo", repo)

    _insert_ingestion_run(
        repo._db_path,
        ingestion_run_id="b-run",
        created_at="2026-01-02T10:00:00+00:00",
        symbols_json='["AAPL", "MSFT", "NVDA"]',
    )
    _insert_ingestion_run(
        repo._db_path,
        ingestion_run_id="a-run",
        created_at="2026-01-02T10:00:00+00:00",
        symbols_json='["BTCUSDT"]',
    )
    _insert_ingestion_run(
        repo._db_path,
        ingestion_run_id="c-run",
        created_at="2026-01-01T10:00:00+00:00",
        symbols_json='["TSLA", "AMD"]',
    )

    client = TestClient(api_main.app)

    response = client.get("/ingestion/runs", params={"limit": 2})
    assert response.status_code == 200

    payload = response.json()
    assert payload == [
        {
            "ingestion_run_id": "a-run",
            "created_at": "2026-01-02T10:00:00+00:00",
            "symbols_count": 1,
        },
        {
            "ingestion_run_id": "b-run",
            "created_at": "2026-01-02T10:00:00+00:00",
            "symbols_count": 3,
        },
    ]


def test_ingestion_runs_limit_defaults_and_caps(monkeypatch, tmp_path: Path) -> None:
    repo = SqliteAnalysisRunRepository(db_path=tmp_path / "ingestion_runs_limits.db")
    monkeypatch.setattr(api_main, "analysis_run_repo", repo)

    for i in range(130):
        minute = i // 60
        second = i % 60
        _insert_ingestion_run(
            repo._db_path,
            ingestion_run_id=f"run-{i:03d}",
            created_at=f"2026-01-01T00:{minute:02d}:{second:02d}+00:00",
            symbols_json='["SYM"]',
        )

    client = TestClient(api_main.app)

    default_response = client.get("/ingestion/runs")
    assert default_response.status_code == 200
    assert len(default_response.json()) == 20

    capped_response = client.get("/ingestion/runs", params={"limit": 200})
    assert capped_response.status_code == 200
    capped_payload = capped_response.json()
    assert len(capped_payload) == 100

    for item in capped_payload:
        assert sorted(item.keys()) == ["created_at", "ingestion_run_id", "symbols_count"]
