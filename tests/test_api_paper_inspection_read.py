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
    return SqliteCanonicalExecutionRepository(db_path=tmp_path / "paper-inspection.db")


def _order(
    order_id: str,
    *,
    sequence: int,
    created_at: str,
    position_id: str,
    trade_id: str,
) -> Order:
    return Order.model_validate(
        {
            "order_id": order_id,
            "strategy_id": "paper-strategy",
            "symbol": "AAPL",
            "sequence": sequence,
            "side": "BUY",
            "order_type": "market",
            "time_in_force": "day",
            "status": "filled",
            "quantity": Decimal("1"),
            "filled_quantity": Decimal("1"),
            "created_at": created_at,
            "submitted_at": created_at,
            "average_fill_price": Decimal("100"),
            "last_execution_event_id": f"evt-{sequence}",
            "position_id": position_id,
            "trade_id": trade_id,
        }
    )


def _event(
    event_id: str,
    order_id: str,
    *,
    occurred_at: str,
    sequence: int,
    position_id: str,
    trade_id: str,
) -> ExecutionEvent:
    return ExecutionEvent.model_validate(
        {
            "event_id": event_id,
            "order_id": order_id,
            "strategy_id": "paper-strategy",
            "symbol": "AAPL",
            "side": "BUY",
            "event_type": "filled",
            "occurred_at": occurred_at,
            "sequence": sequence,
            "execution_quantity": Decimal("1"),
            "execution_price": Decimal("100"),
            "commission": Decimal("0"),
            "position_id": position_id,
            "trade_id": trade_id,
        }
    )


def _trade(
    trade_id: str,
    *,
    position_id: str,
    status: str,
    opened_at: str,
    closed_at: str | None,
    realized_pnl: str | None,
    unrealized_pnl: str | None,
    order_id: str,
    event_id: str,
) -> Trade:
    return Trade.model_validate(
        {
            "trade_id": trade_id,
            "position_id": position_id,
            "strategy_id": "paper-strategy",
            "symbol": "AAPL",
            "direction": "long",
            "status": status,
            "opened_at": opened_at,
            "closed_at": closed_at,
            "quantity_opened": Decimal("1"),
            "quantity_closed": Decimal("1") if status == "closed" else Decimal("0"),
            "average_entry_price": Decimal("100"),
            "average_exit_price": Decimal("101") if status == "closed" else None,
            "realized_pnl": Decimal(realized_pnl) if realized_pnl is not None else None,
            "unrealized_pnl": Decimal(unrealized_pnl) if unrealized_pnl is not None else None,
            "opening_order_ids": [order_id],
            "closing_order_ids": [order_id] if status == "closed" else [],
            "execution_event_ids": [event_id],
        }
    )


def _seed_core_data(repo: SqliteCanonicalExecutionRepository) -> None:
    repo.save_order(
        _order(
            "ord-1",
            sequence=1,
            created_at="2025-01-01T09:00:00Z",
            position_id="pos-1",
            trade_id="trade-1",
        )
    )
    repo.save_order(
        _order(
            "ord-2",
            sequence=2,
            created_at="2025-01-01T09:02:00Z",
            position_id="pos-2",
            trade_id="trade-2",
        )
    )
    repo.save_execution_events(
        [
            _event(
                "evt-1",
                "ord-1",
                occurred_at="2025-01-01T09:01:00Z",
                sequence=1,
                position_id="pos-1",
                trade_id="trade-1",
            ),
            _event(
                "evt-2",
                "ord-2",
                occurred_at="2025-01-01T09:03:00Z",
                sequence=2,
                position_id="pos-2",
                trade_id="trade-2",
            ),
        ]
    )
    repo.save_trade(
        _trade(
            "trade-1",
            position_id="pos-1",
            status="closed",
            opened_at="2025-01-01T09:00:00Z",
            closed_at="2025-01-01T09:10:00Z",
            realized_pnl="1.5",
            unrealized_pnl=None,
            order_id="ord-1",
            event_id="evt-1",
        )
    )
    repo.save_trade(
        _trade(
            "trade-2",
            position_id="pos-2",
            status="open",
            opened_at="2025-01-01T09:02:00Z",
            closed_at=None,
            realized_pnl=None,
            unrealized_pnl="2.25",
            order_id="ord-2",
            event_id="evt-2",
        )
    )


def _test_client(monkeypatch, repo: SqliteCanonicalExecutionRepository) -> TestClient:
    monkeypatch.setattr(api_main, "canonical_execution_repo", repo)
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")
    monkeypatch.setattr(api_main, "shutdown_engine_runtime", lambda: "stopped")
    return TestClient(api_main.app)


def test_paper_endpoints_are_exposed_and_schema_valid(tmp_path: Path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    _seed_core_data(repo)

    with _test_client(monkeypatch, repo) as client:
        trades = client.get("/paper/trades", headers=READ_ONLY_HEADERS)
        positions = client.get("/paper/positions", headers=READ_ONLY_HEADERS)
        account = client.get("/paper/account", headers=READ_ONLY_HEADERS)
        openapi = client.get("/openapi.json").json()

    assert trades.status_code == 200
    assert positions.status_code == 200
    assert account.status_code == 200
    assert "/paper/trades" in openapi["paths"]
    assert "/paper/positions" in openapi["paths"]
    assert "/paper/account" in openapi["paths"]

    assert validate_json_schema(trades.json(), api_main.PaperTradesReadResponse.model_json_schema()) == []
    assert validate_json_schema(positions.json(), api_main.PaperPositionsReadResponse.model_json_schema()) == []
    assert validate_json_schema(account.json(), api_main.PaperAccountReadResponse.model_json_schema()) == []


def test_paper_views_match_trading_core_authoritative_state(tmp_path: Path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    _seed_core_data(repo)

    with _test_client(monkeypatch, repo) as client:
        paper_trades = client.get("/paper/trades", headers=READ_ONLY_HEADERS).json()
        core_trades = client.get("/trading-core/trades", headers=READ_ONLY_HEADERS).json()
        paper_positions = client.get("/paper/positions", headers=READ_ONLY_HEADERS).json()
        core_positions = client.get("/trading-core/positions", headers=READ_ONLY_HEADERS).json()

    assert paper_trades == core_trades
    assert paper_positions == core_positions


def test_paper_account_is_derived_from_canonical_trades(tmp_path: Path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    _seed_core_data(repo)
    monkeypatch.setenv("CILLY_PAPER_ACCOUNT_STARTING_CASH", "100000")

    with _test_client(monkeypatch, repo) as client:
        first = client.get("/paper/account", headers=READ_ONLY_HEADERS)
        second = client.get("/paper/account", headers=READ_ONLY_HEADERS)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert first.json() == {
        "account": {
            "starting_cash": "100000",
            "cash": "100001.5",
            "equity": "100003.75",
            "realized_pnl": "1.5",
            "unrealized_pnl": "2.25",
            "total_pnl": "3.75",
            "open_positions": 1,
            "open_trades": 1,
            "closed_trades": 1,
            "as_of": "2025-01-01T09:10:00Z",
        }
    }
