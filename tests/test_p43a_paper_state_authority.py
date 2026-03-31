"""Integration tests for P43A — one authoritative bounded paper portfolio state.

These tests prove:
- Account, positions, orders, and trades consistency across restart
  (AC3: Restart and reload behavior preserves authoritative state).
- One canonical state-authority interpretation
  (AC1: One bounded paper portfolio source of truth is explicitly defined).
- Reconciliation semantics are explicit
  (AC4: Reconciliation semantics are explicit).
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient

import api.main as api_main
from cilly_trading.models import ExecutionEvent, Order, Trade
from cilly_trading.portfolio.paper_state_authority import (
    CANONICAL_TABLES,
    DERIVED_VIEWS,
    PAPER_STATE_AUTHORITY_ID,
    PAPER_STATE_AUTHORITY_LABEL,
    PERMITTED_ENV_CONSTANTS,
    assert_state_authority,
)
from cilly_trading.repositories.execution_core_sqlite import SqliteCanonicalExecutionRepository

READ_ONLY_HEADERS = {api_main.ROLE_HEADER_NAME: "read_only"}


# ---------------------------------------------------------------------------
# Helpers — reuse the same entity builders as existing paper-inspection tests
# ---------------------------------------------------------------------------


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


def _seed(repo: SqliteCanonicalExecutionRepository) -> None:
    repo.save_order(
        _order("ord-1", sequence=1, created_at="2025-01-01T09:00:00Z", position_id="pos-1", trade_id="trade-1")
    )
    repo.save_order(
        _order("ord-2", sequence=2, created_at="2025-01-01T09:02:00Z", position_id="pos-2", trade_id="trade-2")
    )
    repo.save_execution_events(
        [
            _event(
                "evt-1", "ord-1",
                occurred_at="2025-01-01T09:01:00Z",
                sequence=1,
                position_id="pos-1",
                trade_id="trade-1",
            ),
            _event(
                "evt-2", "ord-2",
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


# ---------------------------------------------------------------------------
# AC3 — Restart and reload behavior preserves authoritative state
# ---------------------------------------------------------------------------


def test_paper_state_survives_process_restart(tmp_path: Path, monkeypatch) -> None:
    """Seed data, close repo, create new repo on same DB → state is identical."""
    db_path = tmp_path / "restart-test.db"
    monkeypatch.setenv("CILLY_PAPER_ACCOUNT_STARTING_CASH", "100000")

    # --- session 1: seed data and capture state ---
    repo1 = SqliteCanonicalExecutionRepository(db_path=db_path)
    _seed(repo1)
    with _test_client(monkeypatch, repo1) as client:
        account_before = client.get("/paper/account", headers=READ_ONLY_HEADERS).json()
        trades_before = client.get("/paper/trades", headers=READ_ONLY_HEADERS).json()
        positions_before = client.get("/paper/positions", headers=READ_ONLY_HEADERS).json()
        reconciliation_before = client.get("/paper/reconciliation", headers=READ_ONLY_HEADERS).json()
        portfolio_before = client.get("/portfolio/positions", headers=READ_ONLY_HEADERS).json()

    # --- session 2: new repo instance on same file (simulates restart) ---
    repo2 = SqliteCanonicalExecutionRepository(db_path=db_path)
    with _test_client(monkeypatch, repo2) as client:
        account_after = client.get("/paper/account", headers=READ_ONLY_HEADERS).json()
        trades_after = client.get("/paper/trades", headers=READ_ONLY_HEADERS).json()
        positions_after = client.get("/paper/positions", headers=READ_ONLY_HEADERS).json()
        reconciliation_after = client.get("/paper/reconciliation", headers=READ_ONLY_HEADERS).json()
        portfolio_after = client.get("/portfolio/positions", headers=READ_ONLY_HEADERS).json()

    assert account_before == account_after
    assert trades_before == trades_after
    assert positions_before == positions_after
    assert reconciliation_before == reconciliation_after
    assert portfolio_before == portfolio_after

    # Reconciliation must be clean in both sessions
    assert reconciliation_before["ok"] is True
    assert reconciliation_before["summary"]["mismatches"] == 0
    assert reconciliation_after["ok"] is True
    assert reconciliation_after["summary"]["mismatches"] == 0


def test_canonical_entity_counts_match_across_restart(tmp_path: Path) -> None:
    """Verify raw entity counts from repository survive restart."""
    db_path = tmp_path / "counts-restart.db"

    repo1 = SqliteCanonicalExecutionRepository(db_path=db_path)
    _seed(repo1)
    orders1 = repo1.list_orders(limit=1_000_000, offset=0)
    events1 = repo1.list_execution_events(limit=1_000_000, offset=0)
    trades1 = repo1.list_trades(limit=1_000_000, offset=0)

    repo2 = SqliteCanonicalExecutionRepository(db_path=db_path)
    orders2 = repo2.list_orders(limit=1_000_000, offset=0)
    events2 = repo2.list_execution_events(limit=1_000_000, offset=0)
    trades2 = repo2.list_trades(limit=1_000_000, offset=0)

    assert len(orders1) == len(orders2) == 2
    assert len(events1) == len(events2) == 2
    assert len(trades1) == len(trades2) == 2

    assert [o.order_id for o in orders1] == [o.order_id for o in orders2]
    assert [e.event_id for e in events1] == [e.event_id for e in events2]
    assert [t.trade_id for t in trades1] == [t.trade_id for t in trades2]


# ---------------------------------------------------------------------------
# AC1 — One canonical state-authority interpretation
# ---------------------------------------------------------------------------


def test_state_authority_contract_is_singular_and_explicit() -> None:
    """The state-authority contract exposes exactly one authority ID."""
    assert PAPER_STATE_AUTHORITY_ID == "canonical_execution_repository"
    assert "SqliteCanonicalExecutionRepository" in PAPER_STATE_AUTHORITY_LABEL
    assert len(CANONICAL_TABLES) == 3
    assert set(CANONICAL_TABLES) == {"core_orders", "core_execution_events", "core_trades"}
    assert "account" in DERIVED_VIEWS
    assert "positions" in DERIVED_VIEWS
    assert "portfolio_positions" in DERIVED_VIEWS
    assert "reconciliation" in DERIVED_VIEWS
    assert PERMITTED_ENV_CONSTANTS == ("CILLY_PAPER_ACCOUNT_STARTING_CASH",)


def test_assert_state_authority_returns_consistent_snapshot(tmp_path: Path) -> None:
    """assert_state_authority reflects canonical entity counts."""
    repo = SqliteCanonicalExecutionRepository(db_path=tmp_path / "authority.db")
    _seed(repo)
    orders = repo.list_orders(limit=1_000_000, offset=0)
    events = repo.list_execution_events(limit=1_000_000, offset=0)
    trades = repo.list_trades(limit=1_000_000, offset=0)

    assertion = assert_state_authority(orders=orders, execution_events=events, trades=trades)

    assert assertion.authority_id == PAPER_STATE_AUTHORITY_ID
    assert assertion.restart_safe is True
    assert assertion.canonical_orders == 2
    assert assertion.canonical_execution_events == 2
    assert assertion.canonical_trades == 2


def test_all_paper_surfaces_derive_from_same_canonical_source(tmp_path: Path, monkeypatch) -> None:
    """Every paper endpoint reads from the same canonical execution repository."""
    db_path = tmp_path / "single-source.db"
    repo = SqliteCanonicalExecutionRepository(db_path=db_path)
    _seed(repo)
    monkeypatch.setenv("CILLY_PAPER_ACCOUNT_STARTING_CASH", "100000")

    with _test_client(monkeypatch, repo) as client:
        account = client.get("/paper/account", headers=READ_ONLY_HEADERS).json()
        trades = client.get("/paper/trades", headers=READ_ONLY_HEADERS).json()
        positions = client.get("/paper/positions", headers=READ_ONLY_HEADERS).json()
        reconciliation = client.get("/paper/reconciliation", headers=READ_ONLY_HEADERS).json()
        portfolio = client.get("/portfolio/positions", headers=READ_ONLY_HEADERS).json()
        core_trades = client.get("/trading-core/trades", headers=READ_ONLY_HEADERS).json()
        core_positions = client.get("/trading-core/positions", headers=READ_ONLY_HEADERS).json()

    # Paper views MUST equal canonical views
    assert trades == core_trades
    assert positions == core_positions

    # Account trade/position counts must match canonical entity counts
    assert account["account"]["open_trades"] == 1
    assert account["account"]["closed_trades"] == 1
    assert account["account"]["open_positions"] == 1

    # Reconciliation confirms zero mismatches from the single authority
    assert reconciliation["ok"] is True
    assert reconciliation["summary"]["mismatches"] == 0
    assert reconciliation["summary"]["orders"] == 2
    assert reconciliation["summary"]["trades"] == 2
    assert reconciliation["summary"]["positions"] == 2

    # Portfolio positions aggregate open trades from the same canonical source
    open_portfolio = portfolio["positions"]
    assert len(open_portfolio) == 1
    assert open_portfolio[0]["strategy_id"] == "paper-strategy"
    assert open_portfolio[0]["symbol"] == "AAPL"


# ---------------------------------------------------------------------------
# AC4 — Reconciliation semantics are explicit
# ---------------------------------------------------------------------------


def test_reconciliation_detects_equation_mismatch_after_manual_corruption(
    tmp_path: Path, monkeypatch
) -> None:
    """Verify that reconciliation catches any state inconsistency.

    We seed valid data, then overwrite a trade with mismatched execution_event_ids
    so reconciliation reports a mismatch — proving it validates cross-references.
    """
    db_path = tmp_path / "corruption.db"
    repo = SqliteCanonicalExecutionRepository(db_path=db_path)
    _seed(repo)
    monkeypatch.setenv("CILLY_PAPER_ACCOUNT_STARTING_CASH", "100000")

    # Overwrite trade-2 with an intentionally invalid execution-event reference
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
            event_id="evt-invalid-reference",
        )
    )

    with _test_client(monkeypatch, repo) as client:
        reconciliation = client.get("/paper/reconciliation", headers=READ_ONLY_HEADERS).json()

    assert reconciliation["ok"] is False
    assert reconciliation["summary"]["mismatches"] > 0
    mismatch_codes = [item["code"] for item in reconciliation["mismatch_items"]]
    assert any("missing" in code for code in mismatch_codes)
