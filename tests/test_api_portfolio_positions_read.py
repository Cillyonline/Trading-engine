from __future__ import annotations

import json

from fastapi.testclient import TestClient

import api.main as api_main
from tests.utils.json_schema_validator import validate_json_schema

READ_ONLY_HEADERS = {api_main.ROLE_HEADER_NAME: "read_only"}


def _test_client(monkeypatch: object) -> TestClient:
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")
    return TestClient(api_main.app)


def test_portfolio_positions_returns_current_positions(monkeypatch) -> None:
    positions_payload = [
        {
            "strategy_id": "alpha",
            "symbol": "MSFT",
            "size": 3.0,
            "average_price": 312.5,
            "unrealized_pnl": 21.1,
        },
        {
            "strategy_id": "beta",
            "symbol": "AAPL",
            "size": -1.0,
            "average_price": 201.0,
            "unrealized_pnl": -4.25,
        },
    ]
    monkeypatch.setenv("CILLY_PORTFOLIO_POSITIONS", json.dumps(positions_payload))

    with _test_client(monkeypatch) as client:
        response = client.get("/portfolio/positions", headers=READ_ONLY_HEADERS)

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert payload["positions"] == [
        {
            "symbol": "AAPL",
            "size": -1.0,
            "average_price": 201.0,
            "unrealized_pnl": -4.25,
            "strategy_id": "beta",
        },
        {
            "symbol": "MSFT",
            "size": 3.0,
            "average_price": 312.5,
            "unrealized_pnl": 21.1,
            "strategy_id": "alpha",
        },
    ]


def test_portfolio_positions_response_schema(monkeypatch) -> None:
    positions_payload = [
        {
            "strategy_id": "trend-a",
            "symbol": "NVDA",
            "size": 4.5,
            "average_price": 920.0,
            "unrealized_pnl": 12.0,
        }
    ]
    monkeypatch.setenv("CILLY_PORTFOLIO_POSITIONS", json.dumps(positions_payload))

    with _test_client(monkeypatch) as client:
        payload = client.get("/portfolio/positions", headers=READ_ONLY_HEADERS).json()

    schema = api_main.PortfolioPositionsResponse.model_json_schema()
    errors = validate_json_schema(payload, schema)
    assert errors == []


def test_portfolio_positions_output_is_deterministic(monkeypatch) -> None:
    positions_payload = [
        {
            "strategy_id": "zeta",
            "symbol": "TSLA",
            "size": 2.0,
            "average_price": 150.0,
            "unrealized_pnl": 1.0,
        },
        {
            "strategy_id": "alpha",
            "symbol": "AAPL",
            "size": 2.0,
            "average_price": 180.0,
            "unrealized_pnl": 5.0,
        },
        {
            "strategy_id": "beta",
            "symbol": "AAPL",
            "size": 1.0,
            "average_price": 181.0,
            "unrealized_pnl": 2.0,
        },
    ]
    monkeypatch.setenv("CILLY_PORTFOLIO_POSITIONS", json.dumps(positions_payload))

    with _test_client(monkeypatch) as client:
        first = client.get("/portfolio/positions", headers=READ_ONLY_HEADERS)
        second = client.get("/portfolio/positions", headers=READ_ONLY_HEADERS)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert [item["symbol"] for item in first.json()["positions"]] == ["AAPL", "AAPL", "TSLA"]
    assert [item["strategy_id"] for item in first.json()["positions"][:2]] == ["alpha", "beta"]
