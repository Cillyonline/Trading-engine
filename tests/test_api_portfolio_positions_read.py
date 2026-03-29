from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient

import api.main as api_main
from cilly_trading.models import Trade
from tests.utils.json_schema_validator import validate_json_schema

READ_ONLY_HEADERS = {api_main.ROLE_HEADER_NAME: "read_only"}


class _FakeCanonicalExecutionRepo:
    def __init__(self, trades: list[Trade]) -> None:
        self._trades = trades

    def list_orders(
        self,
        *,
        strategy_id: str | None = None,
        symbol: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[object]:
        return []

    def list_execution_events(
        self,
        *,
        strategy_id: str | None = None,
        symbol: str | None = None,
        order_id: str | None = None,
        trade_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[object]:
        return []

    def list_trades(
        self,
        *,
        strategy_id: str | None = None,
        symbol: str | None = None,
        position_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Trade]:
        items = self._trades
        if strategy_id is not None:
            items = [item for item in items if item.strategy_id == strategy_id]
        if symbol is not None:
            items = [item for item in items if item.symbol == symbol]
        if position_id is not None:
            items = [item for item in items if item.position_id == position_id]
        return items[offset : offset + limit]


def _trade(
    *,
    trade_id: str,
    position_id: str,
    strategy_id: str,
    symbol: str,
    quantity_opened: str,
    quantity_closed: str = "0",
    average_entry_price: str,
    unrealized_pnl: str | None = None,
    status: str = "open",
) -> Trade:
    closed_quantity = Decimal(quantity_closed)
    return Trade.model_validate(
        {
            "trade_id": trade_id,
            "position_id": position_id,
            "strategy_id": strategy_id,
            "symbol": symbol,
            "direction": "long",
            "status": status,
            "opened_at": "2026-03-25T09:30:00Z",
            "closed_at": "2026-03-25T15:30:00Z" if status == "closed" else None,
            "quantity_opened": Decimal(quantity_opened),
            "quantity_closed": closed_quantity,
            "average_entry_price": Decimal(average_entry_price),
            "average_exit_price": Decimal("105") if status == "closed" or closed_quantity > Decimal("0") else None,
            "exposure_notional": (
                (Decimal(quantity_opened) - closed_quantity)
                * Decimal(average_entry_price)
            ),
            "realized_pnl": Decimal("0") if status == "closed" else None,
            "unrealized_pnl": Decimal(unrealized_pnl) if unrealized_pnl is not None else None,
            "opening_order_ids": ["ord-open"],
            "closing_order_ids": ["ord-close"] if status == "closed" else [],
            "execution_event_ids": ["evt-1"],
        }
    )


def _test_client(monkeypatch: object) -> TestClient:
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")
    return TestClient(api_main.app)


def test_portfolio_positions_returns_current_positions(monkeypatch) -> None:
    trades = [
        _trade(
            trade_id="t-aapl-beta",
            position_id="p-aapl-beta",
            strategy_id="beta",
            symbol="AAPL",
            quantity_opened="2",
            quantity_closed="0",
            average_entry_price="201",
            unrealized_pnl="-4.25",
        ),
        _trade(
            trade_id="t-msft-alpha",
            position_id="p-msft-alpha",
            strategy_id="alpha",
            symbol="MSFT",
            quantity_opened="3",
            quantity_closed="0",
            average_entry_price="312.5",
            unrealized_pnl="21.1",
        ),
    ]
    monkeypatch.setattr(api_main, "canonical_execution_repo", _FakeCanonicalExecutionRepo(trades))

    with _test_client(monkeypatch) as client:
        response = client.get("/portfolio/positions", headers=READ_ONLY_HEADERS)

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert payload["positions"] == [
        {
            "symbol": "AAPL",
            "size": 2.0,
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
    trades = [
        _trade(
            trade_id="t-nvda-trend-a",
            position_id="p-nvda-trend-a",
            strategy_id="trend-a",
            symbol="NVDA",
            quantity_opened="4.5",
            quantity_closed="0",
            average_entry_price="920",
            unrealized_pnl="12",
        )
    ]
    monkeypatch.setattr(api_main, "canonical_execution_repo", _FakeCanonicalExecutionRepo(trades))

    with _test_client(monkeypatch) as client:
        payload = client.get("/portfolio/positions", headers=READ_ONLY_HEADERS).json()

    schema = api_main.PortfolioPositionsResponse.model_json_schema()
    errors = validate_json_schema(payload, schema)
    assert errors == []


def test_portfolio_positions_output_is_deterministic(monkeypatch) -> None:
    trades = [
        _trade(
            trade_id="t-zeta-tsla",
            position_id="p-zeta-tsla",
            strategy_id="zeta",
            symbol="TSLA",
            quantity_opened="2",
            quantity_closed="0",
            average_entry_price="150",
            unrealized_pnl="1",
        ),
        _trade(
            trade_id="t-alpha-aapl-1",
            position_id="p-alpha-aapl",
            strategy_id="alpha",
            symbol="AAPL",
            quantity_opened="1",
            quantity_closed="0",
            average_entry_price="180",
            unrealized_pnl="2",
        ),
        _trade(
            trade_id="t-alpha-aapl-2",
            position_id="p-alpha-aapl",
            strategy_id="alpha",
            symbol="AAPL",
            quantity_opened="1",
            quantity_closed="0",
            average_entry_price="182",
            unrealized_pnl="3",
        ),
        _trade(
            trade_id="t-beta-aapl",
            position_id="p-beta-aapl",
            strategy_id="beta",
            symbol="AAPL",
            quantity_opened="1",
            quantity_closed="0",
            average_entry_price="181",
            unrealized_pnl="2",
        ),
        _trade(
            trade_id="t-closed-ignored",
            position_id="p-closed",
            strategy_id="ignored",
            symbol="QQQ",
            quantity_opened="2",
            quantity_closed="2",
            average_entry_price="300",
            unrealized_pnl="0",
            status="closed",
        ),
    ]
    monkeypatch.setattr(api_main, "canonical_execution_repo", _FakeCanonicalExecutionRepo(trades))

    with _test_client(monkeypatch) as client:
        first = client.get("/portfolio/positions", headers=READ_ONLY_HEADERS)
        second = client.get("/portfolio/positions", headers=READ_ONLY_HEADERS)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert [item["symbol"] for item in first.json()["positions"]] == ["AAPL", "AAPL", "TSLA"]
    assert [item["strategy_id"] for item in first.json()["positions"][:2]] == ["alpha", "beta"]
    assert first.json()["positions"][0]["size"] == 2.0
    assert first.json()["positions"][0]["average_price"] == 181.0
    assert first.json()["positions"][0]["unrealized_pnl"] == 5.0
