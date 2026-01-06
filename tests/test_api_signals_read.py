from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

import api.main as api_main
from api.config import SIGNALS_READ_MAX_LIMIT
from cilly_trading.repositories.signals_sqlite import SqliteSignalRepository


def _make_repo(tmp_path: Path) -> SqliteSignalRepository:
    db_path = tmp_path / "signals_read.db"
    return SqliteSignalRepository(db_path=db_path)


def _base_signal(**overrides):
    base = {
        "symbol": "AAPL",
        "strategy": "RSI2",
        "direction": "long",
        "score": 0.9,
        "timestamp": "2025-01-01T00:00:00+00:00",
        "stage": "setup",
        "timeframe": "D1",
        "market_type": "stock",
        "data_source": "yahoo",
    }
    base.update(overrides)
    return base


def test_read_signals_happy_path(tmp_path: Path, monkeypatch) -> None:
    repo = _make_repo(tmp_path)
    repo.save_signals(
        [
            _base_signal(timestamp="2025-01-01T00:00:00+00:00"),
            _base_signal(timestamp="2025-01-02T00:00:00+00:00", strategy="TURTLE"),
            _base_signal(timestamp="2025-01-03T00:00:00+00:00", symbol="MSFT"),
            _base_signal(timestamp="2025-01-04T00:00:00+00:00"),
        ]
    )

    monkeypatch.setattr(api_main, "signal_repo", repo)
    client = TestClient(api_main.app)

    response = client.get(
        "/signals",
        params={
            "symbol": "AAPL",
            "from": "2025-01-01T00:00:00+00:00",
            "to": "2025-01-04T00:00:00+00:00",
            "sort": "created_at_asc",
            "limit": 1,
            "offset": 1,
        },
    )
    assert response.status_code == 200
    payload = response.json()

    assert payload["limit"] == 1
    assert payload["offset"] == 1
    assert payload["total"] == 3
    assert len(payload["items"]) == 1
    assert payload["items"][0]["created_at"] == "2025-01-02T00:00:00+00:00"
    assert payload["items"][0]["symbol"] == "AAPL"

    response_desc = client.get(
        "/signals",
        params={
            "symbol": "AAPL",
            "sort": "created_at_desc",
            "limit": 2,
            "offset": 0,
        },
    )
    assert response_desc.status_code == 200
    payload_desc = response_desc.json()
    assert [item["created_at"] for item in payload_desc["items"]] == [
        "2025-01-04T00:00:00+00:00",
        "2025-01-02T00:00:00+00:00",
    ]


def test_read_signals_empty_result(tmp_path: Path, monkeypatch) -> None:
    repo = _make_repo(tmp_path)
    repo.save_signals([_base_signal(symbol="AAPL")])

    monkeypatch.setattr(api_main, "signal_repo", repo)
    client = TestClient(api_main.app)

    response = client.get("/signals", params={"symbol": "MISSING"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["items"] == []
    assert payload["total"] == 0


def test_read_signals_invalid_params(tmp_path: Path, monkeypatch) -> None:
    repo = _make_repo(tmp_path)
    monkeypatch.setattr(api_main, "signal_repo", repo)
    client = TestClient(api_main.app)

    for params in [
        {"sort": "foo"},
        {"limit": SIGNALS_READ_MAX_LIMIT + 1},
        {"limit": 0},
        {"from": "2025-01-02T00:00:00+00:00", "to": "2025-01-01T00:00:00+00:00"},
    ]:
        response = client.get("/signals", params=params)
        assert response.status_code == 422


def test_read_signals_limit_boundary(tmp_path: Path, monkeypatch) -> None:
    repo = _make_repo(tmp_path)
    repo.save_signals([_base_signal(symbol="AAPL")])

    monkeypatch.setattr(api_main, "signal_repo", repo)
    client = TestClient(api_main.app)

    response = client.get("/signals", params={"limit": SIGNALS_READ_MAX_LIMIT})
    assert response.status_code == 200
