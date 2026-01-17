from __future__ import annotations

from pathlib import Path

from datetime import datetime

from fastapi.testclient import TestClient

import api.main as api_main
from cilly_trading.repositories.signals_sqlite import SqliteSignalRepository


def _make_repo(tmp_path: Path) -> SqliteSignalRepository:
    db_path = tmp_path / "signals_read_v1.db"
    return SqliteSignalRepository(db_path=db_path)


def _base_signal(**overrides):
    base = {
        "analysis_run_id": "run-1",
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


def test_v1_signals_identical_queries_stable(tmp_path: Path, monkeypatch) -> None:
    repo = _make_repo(tmp_path)
    repo.save_signals(
        [
            _base_signal(symbol="AAPL", timestamp="2025-01-01T00:00:00+00:00"),
            _base_signal(symbol="MSFT", timestamp="2025-01-02T00:00:00+00:00"),
        ]
    )

    monkeypatch.setattr(api_main, "signal_repo", repo)
    client = TestClient(api_main.app)

    params = {"asset": "AAPL", "limit": 10}
    response_first = client.get("/api/v1/signals", params=params)
    response_second = client.get("/api/v1/signals", params=params)

    assert response_first.status_code == 200
    assert response_second.status_code == 200
    assert response_first.json() == response_second.json()


def test_v1_signals_pagination_cursor_stable(tmp_path: Path, monkeypatch) -> None:
    repo = _make_repo(tmp_path)
    repo.save_signals(
        [
            _base_signal(symbol="AAA", timestamp="2025-01-01T00:00:00+00:00"),
            _base_signal(symbol="BBB", timestamp="2025-01-01T00:00:00+00:00"),
            _base_signal(symbol="CCC", timestamp="2025-01-02T00:00:00+00:00"),
        ]
    )

    monkeypatch.setattr(api_main, "signal_repo", repo)
    client = TestClient(api_main.app)

    response_page_1 = client.get("/api/v1/signals", params={"limit": 2})
    assert response_page_1.status_code == 200
    payload_page_1 = response_page_1.json()
    assert payload_page_1["count"] == 2
    assert payload_page_1["next_cursor"]

    response_page_2 = client.get(
        "/api/v1/signals",
        params={"limit": 2, "cursor": payload_page_1["next_cursor"]},
    )
    assert response_page_2.status_code == 200
    payload_page_2 = response_page_2.json()

    combined_items = payload_page_1["items"] + payload_page_2["items"]
    combined_ids = [item["signal_id"] for item in combined_items]

    assert len(combined_ids) == len(set(combined_ids))

    combined_order = []
    for item in combined_items:
        normalized_time = item["signal_time"]
        if normalized_time.endswith("Z"):
            normalized_time = normalized_time[:-1] + "+00:00"
        combined_order.append((datetime.fromisoformat(normalized_time), item["signal_id"]))
    assert combined_order == sorted(combined_order)


def test_v1_signals_read_only_methods(tmp_path: Path, monkeypatch) -> None:
    repo = _make_repo(tmp_path)
    repo.save_signals([_base_signal()])

    monkeypatch.setattr(api_main, "signal_repo", repo)
    client = TestClient(api_main.app)

    for method in ("post", "put", "patch", "delete"):
        response = getattr(client, method)("/api/v1/signals")
        assert response.status_code == 405


def test_v1_signals_response_shape(tmp_path: Path, monkeypatch) -> None:
    repo = _make_repo(tmp_path)
    repo.save_signals([_base_signal(analysis_run_id="run-123")])

    monkeypatch.setattr(api_main, "signal_repo", repo)
    client = TestClient(api_main.app)

    response = client.get("/api/v1/signals")
    assert response.status_code == 200
    payload = response.json()

    assert {"items", "next_cursor", "count"}.issubset(payload.keys())
    assert payload["count"] == 1

    item = payload["items"][0]
    required_keys = {
        "signal_id",
        "run_id",
        "asset",
        "strategy",
        "signal_time",
        "direction",
        "confidence",
        "metadata",
    }
    assert required_keys.issubset(item.keys())
    assert item["run_id"] == "run-123"
    normalized_time = item["signal_time"].replace("Z", "+00:00")
    assert datetime.fromisoformat(normalized_time).isoformat() == normalized_time
