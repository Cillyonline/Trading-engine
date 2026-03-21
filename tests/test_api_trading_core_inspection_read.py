from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient

import api.main as api_main
from cilly_trading.models import ExecutionEvent, Order, Trade
from cilly_trading.repositories.execution_core_sqlite import SqliteCanonicalExecutionRepository
from tests.utils.json_schema_validator import validate_json_schema

READ_ONLY_HEADERS = {api_main.ROLE_HEADER_NAME: "read_only"}


def _repo(tmp_path: Path) -> SqliteCanonicalExecutionRepository:
    return SqliteCanonicalExecutionRepository(db_path=tmp_path / "core-inspection.db")


def _order(
    order_id: str,
    *,
    strategy_id: str = "strategy-a",
    symbol: str = "AAPL",
    sequence: int = 1,
    created_at: str = "2025-01-01T09:00:00Z",
    position_id: str | None = None,
    trade_id: str | None = None,
) -> Order:
    return Order.model_validate(
        {
            "order_id": order_id,
            "strategy_id": strategy_id,
            "symbol": symbol,
            "sequence": sequence,
            "side": "BUY",
            "order_type": "market",
            "time_in_force": "day",
            "status": "created",
            "quantity": Decimal("1"),
            "filled_quantity": Decimal("0"),
            "created_at": created_at,
            "position_id": position_id,
            "trade_id": trade_id,
        }
    )


def _event(
    event_id: str,
    order_id: str,
    *,
    strategy_id: str = "strategy-a",
    symbol: str = "AAPL",
    occurred_at: str = "2025-01-01T09:01:00Z",
    sequence: int = 1,
    position_id: str | None = None,
    trade_id: str | None = None,
) -> ExecutionEvent:
    return ExecutionEvent.model_validate(
        {
            "event_id": event_id,
            "order_id": order_id,
            "strategy_id": strategy_id,
            "symbol": symbol,
            "side": "BUY",
            "event_type": "filled",
            "occurred_at": occurred_at,
            "sequence": sequence,
            "execution_quantity": Decimal("1"),
            "execution_price": Decimal("100"),
            "commission": Decimal("1"),
            "position_id": position_id,
            "trade_id": trade_id,
        }
    )


def _trade(
    trade_id: str,
    *,
    position_id: str,
    strategy_id: str = "strategy-a",
    symbol: str = "AAPL",
    status: str = "open",
    opened_at: str = "2025-01-01T09:00:00Z",
    closed_at: str | None = None,
    quantity_opened: str = "1",
    quantity_closed: str = "0",
    average_entry_price: str = "100",
    average_exit_price: str | None = None,
    realized_pnl: str | None = None,
    opening_order_ids: list[str] | None = None,
    closing_order_ids: list[str] | None = None,
    execution_event_ids: list[str] | None = None,
) -> Trade:
    payload: dict[str, object] = {
        "trade_id": trade_id,
        "position_id": position_id,
        "strategy_id": strategy_id,
        "symbol": symbol,
        "direction": "long",
        "status": status,
        "opened_at": opened_at,
        "closed_at": closed_at,
        "quantity_opened": Decimal(quantity_opened),
        "quantity_closed": Decimal(quantity_closed),
        "average_entry_price": Decimal(average_entry_price),
        "average_exit_price": Decimal(average_exit_price) if average_exit_price is not None else None,
        "realized_pnl": Decimal(realized_pnl) if realized_pnl is not None else None,
        "opening_order_ids": opening_order_ids or [],
        "closing_order_ids": closing_order_ids or [],
        "execution_event_ids": execution_event_ids or [],
    }
    return Trade.model_validate(payload)


def _test_client(monkeypatch, repo: SqliteCanonicalExecutionRepository) -> TestClient:
    monkeypatch.setattr(api_main, "canonical_execution_repo", repo)
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")
    monkeypatch.setattr(api_main, "shutdown_engine_runtime", lambda: "stopped")
    return TestClient(api_main.app)


def _seed_core_data(repo: SqliteCanonicalExecutionRepository) -> None:
    repo.save_order(
        _order(
            "ord-2",
            sequence=2,
            created_at="2025-01-01T09:02:00Z",
            position_id="pos-2",
            trade_id="trade-2",
        )
    )
    repo.save_order(
        _order(
            "ord-1",
            sequence=1,
            created_at="2025-01-01T09:01:00Z",
            position_id="pos-1",
            trade_id="trade-1",
        )
    )
    repo.save_order(
        _order(
            "ord-1b",
            sequence=1,
            created_at="2025-01-01T09:01:00Z",
            position_id="pos-1",
            trade_id="trade-1b",
        )
    )

    repo.save_execution_events(
        [
            _event(
                "evt-2",
                "ord-2",
                occurred_at="2025-01-01T09:02:00Z",
                sequence=2,
                position_id="pos-2",
                trade_id="trade-2",
            ),
            _event(
                "evt-1b",
                "ord-1",
                occurred_at="2025-01-01T09:01:00Z",
                sequence=1,
                position_id="pos-1",
                trade_id="trade-1b",
            ),
            _event(
                "evt-1",
                "ord-1",
                occurred_at="2025-01-01T09:01:00Z",
                sequence=1,
                position_id="pos-1",
                trade_id="trade-1",
            ),
        ]
    )

    repo.save_trade(
        _trade(
            "trade-2",
            position_id="pos-2",
            status="closed",
            opened_at="2025-01-01T09:02:00Z",
            closed_at="2025-01-01T09:10:00Z",
            quantity_opened="1",
            quantity_closed="1",
            average_entry_price="110",
            average_exit_price="111",
            realized_pnl="1",
            opening_order_ids=["ord-2"],
            execution_event_ids=["evt-2"],
        )
    )
    repo.save_trade(
        _trade(
            "trade-1",
            position_id="pos-1",
            status="closed",
            opened_at="2025-01-01T09:00:00Z",
            closed_at="2025-01-01T09:03:00Z",
            quantity_opened="1",
            quantity_closed="1",
            average_entry_price="100",
            average_exit_price="101",
            realized_pnl="1",
            opening_order_ids=["ord-1"],
            execution_event_ids=["evt-1"],
        )
    )
    repo.save_trade(
        _trade(
            "trade-1b",
            position_id="pos-1",
            status="open",
            opened_at="2025-01-01T09:01:30Z",
            quantity_opened="2",
            quantity_closed="0",
            average_entry_price="102",
            opening_order_ids=["ord-1b"],
            execution_event_ids=["evt-1b"],
        )
    )


def test_trading_core_inspection_endpoints_exposed_read_only(tmp_path: Path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    _seed_core_data(repo)
    with _test_client(monkeypatch, repo) as client:
        orders = client.get("/trading-core/orders", headers=READ_ONLY_HEADERS)
        events = client.get("/trading-core/execution-events", headers=READ_ONLY_HEADERS)
        trades = client.get("/trading-core/trades", headers=READ_ONLY_HEADERS)
        positions = client.get("/trading-core/positions", headers=READ_ONLY_HEADERS)
        openapi = client.get("/openapi.json").json()

    assert orders.status_code == 200
    assert events.status_code == 200
    assert trades.status_code == 200
    assert positions.status_code == 200
    assert "/trading-core/orders" in openapi["paths"]
    assert "/trading-core/execution-events" in openapi["paths"]
    assert "/trading-core/trades" in openapi["paths"]
    assert "/trading-core/positions" in openapi["paths"]


def test_trading_core_ordering_is_deterministic(tmp_path: Path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    _seed_core_data(repo)

    with _test_client(monkeypatch, repo) as client:
        first = client.get("/trading-core/orders", headers=READ_ONLY_HEADERS)
        second = client.get("/trading-core/orders", headers=READ_ONLY_HEADERS)
        events = client.get("/trading-core/execution-events", headers=READ_ONLY_HEADERS).json()
        trades = client.get("/trading-core/trades", headers=READ_ONLY_HEADERS).json()
        positions = client.get("/trading-core/positions", headers=READ_ONLY_HEADERS).json()

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()

    assert [item["order_id"] for item in first.json()["items"]] == ["ord-1", "ord-1b", "ord-2"]
    assert [item["event_id"] for item in events["items"]] == ["evt-1", "evt-1b", "evt-2"]
    assert [item["trade_id"] for item in trades["items"]] == ["trade-1", "trade-1b", "trade-2"]
    assert [item["position_id"] for item in positions["items"]] == ["pos-1", "pos-2"]


def test_trading_core_response_schemas_validate(tmp_path: Path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    _seed_core_data(repo)

    with _test_client(monkeypatch, repo) as client:
        orders = client.get("/trading-core/orders", headers=READ_ONLY_HEADERS).json()
        events = client.get("/trading-core/execution-events", headers=READ_ONLY_HEADERS).json()
        trades = client.get("/trading-core/trades", headers=READ_ONLY_HEADERS).json()
        positions = client.get("/trading-core/positions", headers=READ_ONLY_HEADERS).json()

    assert validate_json_schema(orders, api_main.TradingCoreOrdersReadResponse.model_json_schema()) == []
    assert (
        validate_json_schema(
            events,
            api_main.TradingCoreExecutionEventsReadResponse.model_json_schema(),
        )
        == []
    )
    assert validate_json_schema(trades, api_main.TradingCoreTradesReadResponse.model_json_schema()) == []
    assert (
        validate_json_schema(
            positions,
            api_main.TradingCorePositionsReadResponse.model_json_schema(),
        )
        == []
    )


def test_trading_core_empty_and_error_cases(tmp_path: Path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    with _test_client(monkeypatch, repo) as client:
        assert client.get("/trading-core/orders", headers=READ_ONLY_HEADERS).json() == {
            "items": [],
            "limit": 50,
            "offset": 0,
            "total": 0,
        }
        assert client.get("/trading-core/execution-events", headers=READ_ONLY_HEADERS).json() == {
            "items": [],
            "limit": 50,
            "offset": 0,
            "total": 0,
        }
        assert client.get("/trading-core/trades", headers=READ_ONLY_HEADERS).json() == {
            "items": [],
            "limit": 50,
            "offset": 0,
            "total": 0,
        }
        assert client.get("/trading-core/positions", headers=READ_ONLY_HEADERS).json() == {
            "items": [],
            "limit": 50,
            "offset": 0,
            "total": 0,
        }

        unauthorized = client.get("/trading-core/orders")
        invalid_limit = client.get(
            "/trading-core/orders",
            headers=READ_ONLY_HEADERS,
            params={"limit": 0},
        )
        unknown_trade = client.get(
            "/trading-core/trades",
            headers=READ_ONLY_HEADERS,
            params={"trade_id": "does-not-exist"},
        )

    assert unauthorized.status_code == 401
    assert unauthorized.json() == {"detail": "unauthorized"}
    assert invalid_limit.status_code == 422
    assert unknown_trade.status_code == 200
    assert unknown_trade.json()["items"] == []
    assert unknown_trade.json()["total"] == 0
