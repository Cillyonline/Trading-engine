from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

import api.main as api_main
from api.config import SIGNALS_READ_MAX_LIMIT
from cilly_trading.repositories.signals_sqlite import SqliteSignalRepository

READ_ONLY_HEADERS = {api_main.ROLE_HEADER_NAME: "read_only"}


def _make_repo(tmp_path: Path) -> SqliteSignalRepository:
    db_path = tmp_path / "signals_read.db"
    return SqliteSignalRepository(db_path=db_path)


def _base_signal(**overrides):
    base = {
        "ingestion_run_id": "test-run-001",
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
        headers=READ_ONLY_HEADERS,
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
        headers=READ_ONLY_HEADERS,
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


def test_read_signals_openapi_exposes_timeframe_not_legacy_filters(tmp_path: Path, monkeypatch) -> None:
    repo = _make_repo(tmp_path)
    monkeypatch.setattr(api_main, "signal_repo", repo)
    client = TestClient(api_main.app)

    response = client.get("/openapi.json")

    assert response.status_code == 200
    parameters = response.json()["paths"]["/signals"]["get"]["parameters"]
    parameter_names = {item["name"] for item in parameters}

    assert "timeframe" in parameter_names
    assert "preset" not in parameter_names
    assert "start" not in parameter_names
    assert "end" not in parameter_names


def test_read_signals_empty_result(tmp_path: Path, monkeypatch) -> None:
    repo = _make_repo(tmp_path)
    repo.save_signals([_base_signal(symbol="AAPL")])

    monkeypatch.setattr(api_main, "signal_repo", repo)
    client = TestClient(api_main.app)

    response = client.get("/signals", headers=READ_ONLY_HEADERS, params={"symbol": "MISSING"})
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
        {"preset": "D1"},
        {"start": "2025-01-01T00:00:00+00:00"},
        {"end": "2025-01-01T00:00:00+00:00"},
    ]:
        response = client.get("/signals", headers=READ_ONLY_HEADERS, params=params)
        assert response.status_code == 422


def test_read_signals_limit_boundary(tmp_path: Path, monkeypatch) -> None:
    repo = _make_repo(tmp_path)
    repo.save_signals([_base_signal(symbol="AAPL")])

    monkeypatch.setattr(api_main, "signal_repo", repo)
    client = TestClient(api_main.app)

    response = client.get("/signals", headers=READ_ONLY_HEADERS, params={"limit": SIGNALS_READ_MAX_LIMIT})
    assert response.status_code == 200


def test_read_signals_time_filters_from_to(tmp_path: Path, monkeypatch) -> None:
    repo = _make_repo(tmp_path)
    repo.save_signals(
        [
            _base_signal(timestamp="2025-01-01T00:00:00+00:00"),
            _base_signal(timestamp="2025-01-02T00:00:00+00:00"),
            _base_signal(timestamp="2025-01-03T00:00:00+00:00"),
        ]
    )

    monkeypatch.setattr(api_main, "signal_repo", repo)
    client = TestClient(api_main.app)

    response_start = client.get(
        "/signals",
        headers=READ_ONLY_HEADERS,
        params={"from": "2025-01-02T00:00:00+00:00"},
    )
    assert response_start.status_code == 200
    payload_start = response_start.json()
    assert payload_start["total"] == 2
    assert [item["created_at"] for item in payload_start["items"]] == [
        "2025-01-03T00:00:00+00:00",
        "2025-01-02T00:00:00+00:00",
    ]

    response_end = client.get(
        "/signals",
        headers=READ_ONLY_HEADERS,
        params={"to": "2025-01-02T00:00:00+00:00"},
    )
    assert response_end.status_code == 200
    payload_end = response_end.json()
    assert payload_end["total"] == 2
    assert [item["created_at"] for item in payload_end["items"]] == [
        "2025-01-02T00:00:00+00:00",
        "2025-01-01T00:00:00+00:00",
    ]

    response_range = client.get(
        "/signals",
        headers=READ_ONLY_HEADERS,
        params={
            "from": "2025-01-02T00:00:00+00:00",
            "to": "2025-01-02T00:00:00+00:00",
        },
    )
    assert response_range.status_code == 200
    payload_range = response_range.json()
    assert payload_range["total"] == 1
    assert payload_range["items"][0]["created_at"] == "2025-01-02T00:00:00+00:00"


def test_read_signals_filters_strategy_and_timeframe(tmp_path: Path, monkeypatch) -> None:
    repo = _make_repo(tmp_path)
    repo.save_signals(
        [
            _base_signal(strategy="RSI2", timeframe="D1", symbol="AAA"),
            _base_signal(strategy="RSI2", timeframe="H1", symbol="BBB"),
            _base_signal(strategy="TURTLE", timeframe="H1", symbol="CCC"),
        ]
    )

    monkeypatch.setattr(api_main, "signal_repo", repo)
    client = TestClient(api_main.app)

    response = client.get(
        "/signals",
        headers=READ_ONLY_HEADERS,
        params={"strategy": "RSI2", "timeframe": "H1"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["symbol"] == "BBB"


def test_read_signals_unfiltered_dedupes_same_signal_across_ingestion_runs(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _make_repo(tmp_path)
    repo.save_signals(
        [
            _base_signal(
                ingestion_run_id="ing-run-001",
                analysis_run_id="analysis-run-001",
                symbol="AAPL",
                timestamp="2025-01-03T00:00:00+00:00",
            ),
            _base_signal(
                ingestion_run_id="ing-run-002",
                analysis_run_id="analysis-run-002",
                symbol="AAPL",
                timestamp="2025-01-03T00:00:00+00:00",
            ),
        ]
    )

    monkeypatch.setattr(api_main, "signal_repo", repo)
    client = TestClient(api_main.app)

    response_all = client.get("/signals", headers=READ_ONLY_HEADERS, params={"limit": 20})
    assert response_all.status_code == 200
    payload_all = response_all.json()
    assert payload_all["total"] == 1
    assert len(payload_all["items"]) == 1
    assert payload_all["items"][0]["symbol"] == "AAPL"

    response_first_run = client.get(
        "/signals",
        headers=READ_ONLY_HEADERS,
        params={"ingestion_run_id": "ing-run-001", "limit": 20},
    )
    assert response_first_run.status_code == 200
    payload_first_run = response_first_run.json()
    assert payload_first_run["total"] == 1
    assert payload_first_run["items"][0]["symbol"] == "AAPL"

    response_second_run = client.get(
        "/signals",
        headers=READ_ONLY_HEADERS,
        params={"ingestion_run_id": "ing-run-002", "limit": 20},
    )
    assert response_second_run.status_code == 200
    payload_second_run = response_second_run.json()
    assert payload_second_run["total"] == 1
    assert payload_second_run["items"][0]["symbol"] == "AAPL"


def test_read_signals_default_limit_applied(tmp_path: Path, monkeypatch) -> None:
    repo = _make_repo(tmp_path)
    repo.save_signals(
        [
            _base_signal(symbol=f"SYM{i}", timestamp="2025-01-01T00:00:00+00:00")
            for i in range(1, 61)
        ]
    )

    monkeypatch.setattr(api_main, "signal_repo", repo)
    client = TestClient(api_main.app)

    response = client.get("/signals", headers=READ_ONLY_HEADERS)
    assert response.status_code == 200
    payload = response.json()
    assert payload["limit"] == 50
    assert payload["total"] == 60
    assert len(payload["items"]) == 50


def test_read_signals_requires_authenticated_role(tmp_path: Path, monkeypatch) -> None:
    repo = _make_repo(tmp_path)
    monkeypatch.setattr(api_main, "signal_repo", repo)
    client = TestClient(api_main.app)

    response = client.get("/signals")

    assert response.status_code == 401
    assert response.json() == {"detail": "unauthorized"}
