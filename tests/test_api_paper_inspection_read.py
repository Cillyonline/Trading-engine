from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient

import api.main as api_main
from cilly_trading.engine.paper_order_lifecycle import (
    PaperOrderLifecycleRequest,
    PaperOrderLifecycleSimulator,
    PaperOrderStep,
)
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


def _seed_lifecycle_data(repo: SqliteCanonicalExecutionRepository) -> None:
    simulator = PaperOrderLifecycleSimulator()
    lifecycle = simulator.run(
        request=PaperOrderLifecycleRequest(
            order_id="ord-lifecycle-1",
            strategy_id="paper-strategy",
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("2"),
            created_at="2025-01-01T09:00:00Z",
            submitted_at="2025-01-01T09:00:01Z",
            sequence=1,
            position_id="pos-lifecycle-1",
            trade_id="trade-lifecycle-1",
        ),
        steps=[
            PaperOrderStep(
                occurred_at="2025-01-01T09:00:10Z",
                action="fill",
                quantity=Decimal("1"),
                price=Decimal("100"),
                commission=Decimal("0"),
            ),
            PaperOrderStep(
                occurred_at="2025-01-01T09:00:20Z",
                action="fill",
                quantity=Decimal("1"),
                price=Decimal("101"),
                commission=Decimal("0"),
            ),
        ],
    )

    repo.save_order(lifecycle.final_order)
    repo.save_execution_events(list(lifecycle.execution_events))
    repo.save_trade(
        Trade.model_validate(
            {
                "trade_id": "trade-lifecycle-1",
                "position_id": "pos-lifecycle-1",
                "strategy_id": "paper-strategy",
                "symbol": "AAPL",
                "direction": "long",
                "status": "open",
                "opened_at": "2025-01-01T09:00:00Z",
                "closed_at": None,
                "quantity_opened": Decimal("2"),
                "quantity_closed": Decimal("0"),
                "average_entry_price": Decimal("100.5"),
                "average_exit_price": None,
                "realized_pnl": None,
                "unrealized_pnl": Decimal("2"),
                "opening_order_ids": ["ord-lifecycle-1"],
                "closing_order_ids": [],
                "execution_event_ids": [event.event_id for event in lifecycle.execution_events],
            }
        )
    )


def test_paper_endpoints_are_exposed_and_schema_valid(tmp_path: Path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    _seed_core_data(repo)

    with _test_client(monkeypatch, repo) as client:
        workflow = client.get("/paper/workflow", headers=READ_ONLY_HEADERS)
        trades = client.get("/paper/trades", headers=READ_ONLY_HEADERS)
        positions = client.get("/paper/positions", headers=READ_ONLY_HEADERS)
        account = client.get("/paper/account", headers=READ_ONLY_HEADERS)
        reconciliation = client.get("/paper/reconciliation", headers=READ_ONLY_HEADERS)
        openapi = client.get("/openapi.json").json()

    assert workflow.status_code == 200
    assert trades.status_code == 200
    assert positions.status_code == 200
    assert account.status_code == 200
    assert reconciliation.status_code == 200
    assert "/paper/workflow" in openapi["paths"]
    assert "/paper/trades" in openapi["paths"]
    assert "/paper/positions" in openapi["paths"]
    assert "/paper/account" in openapi["paths"]
    assert "/paper/reconciliation" in openapi["paths"]
    for path in (
        "/paper/workflow",
        "/paper/trades",
        "/paper/positions",
        "/paper/account",
        "/paper/reconciliation",
    ):
        assert set(openapi["paths"][path].keys()) == {"get"}

    assert (
        validate_json_schema(
            workflow.json(),
            api_main.PaperOperatorWorkflowReadResponse.model_json_schema(),
        )
        == []
    )
    assert validate_json_schema(trades.json(), api_main.PaperTradesReadResponse.model_json_schema()) == []
    assert validate_json_schema(positions.json(), api_main.PaperPositionsReadResponse.model_json_schema()) == []
    assert validate_json_schema(account.json(), api_main.PaperAccountReadResponse.model_json_schema()) == []
    assert (
        validate_json_schema(
            reconciliation.json(),
            api_main.PaperReconciliationReadResponse.model_json_schema(),
        )
        == []
    )


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


def test_paper_reconciliation_matches_deterministic_lifecycle_outputs(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _repo(tmp_path)
    _seed_lifecycle_data(repo)
    monkeypatch.setenv("CILLY_PAPER_ACCOUNT_STARTING_CASH", "100000")

    with _test_client(monkeypatch, repo) as client:
        first_reconciliation = client.get("/paper/reconciliation", headers=READ_ONLY_HEADERS)
        second_reconciliation = client.get("/paper/reconciliation", headers=READ_ONLY_HEADERS)
        core_orders = client.get("/trading-core/orders", headers=READ_ONLY_HEADERS).json()
        core_events = client.get("/trading-core/execution-events", headers=READ_ONLY_HEADERS).json()
        core_trades = client.get("/trading-core/trades", headers=READ_ONLY_HEADERS).json()
        core_positions = client.get("/trading-core/positions", headers=READ_ONLY_HEADERS).json()
        paper_trades = client.get("/paper/trades", headers=READ_ONLY_HEADERS).json()
        paper_positions = client.get("/paper/positions", headers=READ_ONLY_HEADERS).json()
        paper_account = client.get("/paper/account", headers=READ_ONLY_HEADERS).json()

    assert first_reconciliation.status_code == 200
    assert second_reconciliation.status_code == 200
    assert first_reconciliation.json() == second_reconciliation.json()

    reconciliation = first_reconciliation.json()
    assert reconciliation["ok"] is True
    assert reconciliation["summary"] == {
        "orders": 1,
        "execution_events": 4,
        "trades": 1,
        "positions": 1,
        "open_trades": 1,
        "closed_trades": 0,
        "open_positions": 1,
        "mismatches": 0,
    }
    assert reconciliation["mismatch_items"] == []
    assert reconciliation["account"] == paper_account["account"]

    assert [item["status"] for item in core_orders["items"]] == ["filled"]
    assert [item["event_type"] for item in core_events["items"]] == [
        "created",
        "submitted",
        "partially_filled",
        "filled",
    ]
    assert [item["trade_id"] for item in core_trades["items"]] == ["trade-lifecycle-1"]
    assert [item["position_id"] for item in core_positions["items"]] == ["pos-lifecycle-1"]
    assert paper_trades == core_trades
    assert paper_positions == core_positions
    assert paper_account == {
        "account": {
            "starting_cash": "100000",
            "cash": "100000",
            "equity": "100002",
            "realized_pnl": "0",
            "unrealized_pnl": "2",
            "total_pnl": "2",
            "open_positions": 1,
            "open_trades": 1,
            "closed_trades": 0,
            "as_of": "2025-01-01T09:00:00Z",
        }
    }


def test_paper_workflow_contract_is_explicit_and_aligned_to_surfaces(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _repo(tmp_path)
    _seed_lifecycle_data(repo)
    monkeypatch.setenv("CILLY_PAPER_ACCOUNT_STARTING_CASH", "100000")

    with _test_client(monkeypatch, repo) as client:
        response = client.get("/paper/workflow", headers=READ_ONLY_HEADERS)

    assert response.status_code == 200
    payload = response.json()

    assert payload["boundary"]["workflow_id"] == "phase44_bounded_paper_operator"
    assert "read-only" in payload["boundary"]["description"]
    assert payload["boundary"]["in_scope"] == [
        "deterministic simulator lifecycle evidence",
        "canonical inspection of orders, execution events, trades, and positions",
        "paper inspection of account, trades, and positions",
        "reconciliation validation with mismatch accounting",
    ]
    assert payload["boundary"]["out_of_scope"] == [
        "live trading",
        "broker integrations",
        "broad dashboard expansion",
        "production trading operations",
    ]

    assert payload["steps"] == [
        {
            "step": 1,
            "action": "Inspect canonical order lifecycle entities.",
            "endpoint": "GET /trading-core/orders",
            "expected_result": "Deterministic order set is readable (items=1).",
        },
        {
            "step": 2,
            "action": "Inspect canonical execution lifecycle events.",
            "endpoint": "GET /trading-core/execution-events",
            "expected_result": "Deterministic execution-event set is readable (items=4).",
        },
        {
            "step": 3,
            "action": "Inspect canonical trade and position state.",
            "endpoint": "GET /trading-core/trades + GET /trading-core/positions",
            "expected_result": "Canonical trade/position sets are readable (trades=1, positions=1).",
        },
        {
            "step": 4,
            "action": "Inspect paper-facing views derived from canonical entities.",
            "endpoint": "GET /paper/trades + GET /paper/positions + GET /paper/account",
            "expected_result": "Paper views are readable (trades=1, positions=1).",
        },
        {
            "step": 5,
            "action": "Run reconciliation and require zero mismatches.",
            "endpoint": "GET /paper/reconciliation",
            "expected_result": "Reconciliation ok=true mismatches=0.",
        },
    ]
    assert payload["surfaces"] == {
        "canonical_inspection": [
            "/trading-core/orders",
            "/trading-core/execution-events",
            "/trading-core/trades",
            "/trading-core/positions",
        ],
        "paper_inspection": [
            "/paper/trades",
            "/paper/positions",
            "/paper/account",
        ],
        "reconciliation": "/paper/reconciliation",
    }
    assert payload["validation"] == {
        "ok": True,
        "checks": [
            {
                "code": "reconciliation_ok",
                "ok": True,
                "expected": "true",
                "actual": "true",
            },
            {
                "code": "reconciliation_mismatches_zero",
                "ok": True,
                "expected": "0",
                "actual": "0",
            },
            {
                "code": "paper_trades_match_canonical_trades",
                "ok": True,
                "expected": "true",
                "actual": "true",
            },
            {
                "code": "paper_positions_match_canonical_positions",
                "ok": True,
                "expected": "true",
                "actual": "true",
            },
        ],
    }


def test_paper_reconciliation_detects_missing_execution_event_reference(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _repo(tmp_path)
    _seed_core_data(repo)
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
            event_id="evt-missing",
        )
    )

    with _test_client(monkeypatch, repo) as client:
        response = client.get("/paper/reconciliation", headers=READ_ONLY_HEADERS)

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is False
    assert payload["summary"]["mismatches"] == 2
    assert payload["mismatch_items"] == [
        {
            "code": "position_execution_event_missing",
            "message": "position references unknown execution_event_id=evt-missing",
            "entity_type": "position",
            "entity_id": "pos-2",
        },
        {
            "code": "trade_execution_event_missing",
            "message": "trade references unknown execution_event_id=evt-missing",
            "entity_type": "trade",
            "entity_id": "trade-2",
        },
    ]


def test_paper_workflow_validation_fails_closed_on_reconciliation_mismatches(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _repo(tmp_path)
    _seed_core_data(repo)
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
            event_id="evt-missing",
        )
    )

    with _test_client(monkeypatch, repo) as client:
        response = client.get("/paper/workflow", headers=READ_ONLY_HEADERS)

    assert response.status_code == 200
    payload = response.json()
    assert payload["validation"] == {
        "ok": False,
        "checks": [
            {
                "code": "reconciliation_ok",
                "ok": False,
                "expected": "true",
                "actual": "false",
            },
            {
                "code": "reconciliation_mismatches_zero",
                "ok": False,
                "expected": "0",
                "actual": "2",
            },
            {
                "code": "paper_trades_match_canonical_trades",
                "ok": True,
                "expected": "true",
                "actual": "true",
            },
            {
                "code": "paper_positions_match_canonical_positions",
                "ok": True,
                "expected": "true",
                "actual": "true",
            },
        ],
    }
