from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

import api.main as api_main
from cilly_trading.repositories.order_events_sqlite import SqliteOrderEventRepository

READ_ONLY_HEADERS = {api_main.ROLE_HEADER_NAME: "read_only"}


def _make_repo(tmp_path: Path) -> SqliteOrderEventRepository:
    db_path = tmp_path / "order_events.db"
    return SqliteOrderEventRepository(db_path=db_path)


def _event(**overrides):
    base = {
        "run_id": "run-1",
        "order_id": "ord-1",
        "symbol": "AAPL",
        "strategy": "RSI2",
        "state": "created",
        "event_timestamp": "2025-01-01T00:00:00+00:00",
        "event_sequence": 1,
        "metadata": {"source": "test"},
    }
    base.update(overrides)
    return base


def test_execution_orders_api_contract(tmp_path: Path, monkeypatch) -> None:
    repo = _make_repo(tmp_path)
    repo.save_events(
        [
            _event(state="created", event_sequence=1),
            _event(state="submitted", event_sequence=2),
            _event(state="partially_filled", event_sequence=3),
            _event(state="filled", event_sequence=4),
            _event(state="cancelled", order_id="ord-2", event_sequence=1),
        ]
    )

    monkeypatch.setattr(api_main, "order_event_repo", repo)
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")
    monkeypatch.setattr(api_main, "shutdown_engine_runtime", lambda: "stopped")
    with TestClient(api_main.app) as client:
        response = client.get(
            "/execution/orders",
            headers=READ_ONLY_HEADERS,
            params={"limit": 10, "offset": 0},
        )
        openapi = client.get("/openapi.json").json()

    assert response.status_code == 200
    payload = response.json()
    assert payload["limit"] == 10
    assert payload["offset"] == 0
    assert payload["total"] == 5
    assert len(payload["items"]) == 5
    assert "/execution/orders" in openapi["paths"]

    allowed_states = {"created", "submitted", "filled", "partially_filled", "cancelled"}
    for item in payload["items"]:
        assert set(item.keys()) == {
            "run_id",
            "order_id",
            "symbol",
            "strategy",
            "state",
            "event_timestamp",
            "event_sequence",
            "metadata",
        }
        assert item["state"] in allowed_states


def test_execution_orders_are_deterministically_sorted(tmp_path: Path, monkeypatch) -> None:
    repo = _make_repo(tmp_path)
    repo.save_events(
        [
            _event(run_id="run-b", symbol="MSFT", order_id="ord-2", event_sequence=2),
            _event(run_id="run-a", symbol="AAPL", order_id="ord-2", event_sequence=1),
            _event(
                run_id="run-a",
                symbol="AAPL",
                order_id="ord-1",
                event_timestamp="2024-12-31T00:00:00+00:00",
                event_sequence=9,
            ),
            _event(run_id="run-a", symbol="AAPL", order_id="ord-1", event_sequence=1),
            _event(run_id="run-a", symbol="AAPL", order_id="ord-1", event_sequence=0),
        ]
    )

    monkeypatch.setattr(api_main, "order_event_repo", repo)
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")
    monkeypatch.setattr(api_main, "shutdown_engine_runtime", lambda: "stopped")
    with TestClient(api_main.app) as client:
        first = client.get("/execution/orders", headers=READ_ONLY_HEADERS)
        second = client.get("/execution/orders", headers=READ_ONLY_HEADERS)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()

    payload = first.json()
    order_keys = [
        (
            item["event_timestamp"],
            item["run_id"],
            item["symbol"],
            item["strategy"],
            item["order_id"],
            item["event_sequence"],
        )
        for item in payload["items"]
    ]
    assert order_keys == [
        ("2024-12-31T00:00:00+00:00", "run-a", "AAPL", "RSI2", "ord-1", 9),
        ("2025-01-01T00:00:00+00:00", "run-a", "AAPL", "RSI2", "ord-1", 0),
        ("2025-01-01T00:00:00+00:00", "run-a", "AAPL", "RSI2", "ord-1", 1),
        ("2025-01-01T00:00:00+00:00", "run-a", "AAPL", "RSI2", "ord-2", 1),
        ("2025-01-01T00:00:00+00:00", "run-b", "MSFT", "RSI2", "ord-2", 2),
    ]


def test_execution_orders_filtering_and_pagination(tmp_path: Path, monkeypatch) -> None:
    repo = _make_repo(tmp_path)
    repo.save_events(
        [
            _event(run_id="run-1", symbol="AAPL", strategy="RSI2", order_id="a-1", event_sequence=1),
            _event(run_id="run-1", symbol="AAPL", strategy="TURTLE", order_id="a-2", event_sequence=1),
            _event(run_id="run-2", symbol="MSFT", strategy="RSI2", order_id="m-1", event_sequence=1),
            _event(run_id="run-3", symbol="AAPL", strategy="RSI2", order_id="a-3", event_sequence=1),
        ]
    )

    monkeypatch.setattr(api_main, "order_event_repo", repo)
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")
    monkeypatch.setattr(api_main, "shutdown_engine_runtime", lambda: "stopped")
    with TestClient(api_main.app) as client:
        by_symbol = client.get("/execution/orders", headers=READ_ONLY_HEADERS, params={"symbol": "AAPL"})
        by_strategy = client.get(
            "/execution/orders",
            headers=READ_ONLY_HEADERS,
            params={"strategy": "RSI2"},
        )
        by_run = client.get("/execution/orders", headers=READ_ONLY_HEADERS, params={"run_id": "run-1"})
        by_order = client.get("/execution/orders", headers=READ_ONLY_HEADERS, params={"order_id": "a-1"})
        paged = client.get(
            "/execution/orders",
            headers=READ_ONLY_HEADERS,
            params={"symbol": "AAPL", "strategy": "RSI2", "limit": 1, "offset": 1},
        )

    assert by_symbol.status_code == 200
    assert by_strategy.status_code == 200
    assert by_run.status_code == 200
    assert by_order.status_code == 200
    assert paged.status_code == 200

    by_symbol_payload = by_symbol.json()
    by_strategy_payload = by_strategy.json()
    by_run_payload = by_run.json()
    by_order_payload = by_order.json()
    paged_payload = paged.json()

    assert by_symbol_payload["total"] == 3
    assert all(item["symbol"] == "AAPL" for item in by_symbol_payload["items"])

    assert by_strategy_payload["total"] == 3
    assert all(item["strategy"] == "RSI2" for item in by_strategy_payload["items"])

    assert by_run_payload["total"] == 2
    assert all(item["run_id"] == "run-1" for item in by_run_payload["items"])

    assert by_order_payload["total"] == 1
    assert all(item["order_id"] == "a-1" for item in by_order_payload["items"])

    assert paged_payload["total"] == 2
    assert paged_payload["limit"] == 1
    assert paged_payload["offset"] == 1
    assert len(paged_payload["items"]) == 1


def test_execution_orders_require_authenticated_role(tmp_path: Path, monkeypatch) -> None:
    repo = _make_repo(tmp_path)
    monkeypatch.setattr(api_main, "order_event_repo", repo)
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")
    monkeypatch.setattr(api_main, "shutdown_engine_runtime", lambda: "stopped")

    with TestClient(api_main.app) as client:
        response = client.get("/execution/orders")

    assert response.status_code == 401
    assert response.json() == {"detail": "unauthorized"}
