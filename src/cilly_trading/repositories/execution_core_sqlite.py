"""SQLite repository for canonical trading-core execution persistence."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Optional

from cilly_trading.db import DEFAULT_DB_PATH, init_db
from cilly_trading.models import ExecutionEvent, Order, Trade
from cilly_trading.repositories import CanonicalExecutionRepository


class SqliteCanonicalExecutionRepository(CanonicalExecutionRepository):
    """Deterministic persistence for canonical orders, execution events, and trades."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self._db_path = Path(db_path or DEFAULT_DB_PATH)
        init_db(self._db_path)
        self._ensure_tables()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        return conn

    def _connection(self):
        return closing(self._get_connection())

    def _ensure_tables(self) -> None:
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS core_orders (
                order_id TEXT PRIMARY KEY,
                strategy_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                created_at TEXT NOT NULL,
                sequence INTEGER NOT NULL,
                payload_json TEXT NOT NULL
            );
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_core_orders_deterministic
            ON core_orders(strategy_id, symbol, created_at, sequence, order_id);
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS core_execution_events (
                event_id TEXT PRIMARY KEY,
                order_id TEXT NOT NULL,
                strategy_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                trade_id TEXT NULL,
                occurred_at TEXT NOT NULL,
                sequence INTEGER NOT NULL,
                payload_json TEXT NOT NULL
            );
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_core_execution_events_deterministic
            ON core_execution_events(
                strategy_id,
                symbol,
                order_id,
                trade_id,
                occurred_at,
                sequence,
                event_id
            );
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS core_trades (
                trade_id TEXT PRIMARY KEY,
                position_id TEXT NOT NULL,
                strategy_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                opened_at TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_core_trades_deterministic
            ON core_trades(strategy_id, symbol, position_id, opened_at, trade_id);
            """
        )
        conn.commit()
        conn.close()

    def save_order(self, order: Order) -> None:
        normalized_order = Order.model_validate(order)
        payload_json = normalized_order.to_canonical_json()

        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO core_orders (
                order_id,
                strategy_id,
                symbol,
                created_at,
                sequence,
                payload_json
            )
            VALUES (
                :order_id,
                :strategy_id,
                :symbol,
                :created_at,
                :sequence,
                :payload_json
            )
            ON CONFLICT(order_id) DO UPDATE SET
                strategy_id = excluded.strategy_id,
                symbol = excluded.symbol,
                created_at = excluded.created_at,
                sequence = excluded.sequence,
                payload_json = excluded.payload_json;
            """,
            {
                "order_id": normalized_order.order_id,
                "strategy_id": normalized_order.strategy_id,
                "symbol": normalized_order.symbol,
                "created_at": normalized_order.created_at,
                "sequence": normalized_order.sequence,
                "payload_json": payload_json,
            },
        )
        conn.commit()
        conn.close()

    def get_order(self, order_id: str) -> Optional[Order]:
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT payload_json
            FROM core_orders
            WHERE order_id = ?;
            """,
            (order_id,),
        )
        row = cur.fetchone()
        conn.close()
        if row is None:
            return None
        return Order.model_validate_json(row["payload_json"])

    def list_orders(
        self,
        *,
        strategy_id: Optional[str] = None,
        symbol: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Order]:
        where_parts: list[str] = []
        params: list[object] = []

        if strategy_id is not None:
            where_parts.append("strategy_id = ?")
            params.append(strategy_id)
        if symbol is not None:
            where_parts.append("symbol = ?")
            params.append(symbol)

        where_sql = ""
        if where_parts:
            where_sql = "WHERE " + " AND ".join(where_parts)

        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT payload_json
            FROM core_orders
            {where_sql}
            ORDER BY
                REPLACE(created_at, 'Z', '+00:00') ASC,
                sequence ASC,
                order_id ASC
            LIMIT ?
            OFFSET ?;
            """,
            [*params, limit, offset],
        )
        rows = cur.fetchall()
        conn.close()
        return [Order.model_validate_json(row["payload_json"]) for row in rows]

    def save_execution_events(self, events: list[ExecutionEvent]) -> None:
        if not events:
            return

        normalized_events = [ExecutionEvent.model_validate(event) for event in events]

        conn = self._get_connection()
        cur = conn.cursor()
        for event in normalized_events:
            payload_json = event.to_canonical_json()
            cur.execute(
                """
                INSERT OR IGNORE INTO core_execution_events (
                    event_id,
                    order_id,
                    strategy_id,
                    symbol,
                    trade_id,
                    occurred_at,
                    sequence,
                    payload_json
                )
                VALUES (
                    :event_id,
                    :order_id,
                    :strategy_id,
                    :symbol,
                    :trade_id,
                    :occurred_at,
                    :sequence,
                    :payload_json
                );
                """,
                {
                    "event_id": event.event_id,
                    "order_id": event.order_id,
                    "strategy_id": event.strategy_id,
                    "symbol": event.symbol,
                    "trade_id": event.trade_id,
                    "occurred_at": event.occurred_at,
                    "sequence": event.sequence,
                    "payload_json": payload_json,
                },
            )
            if cur.rowcount == 0:
                cur.execute(
                    """
                    SELECT payload_json
                    FROM core_execution_events
                    WHERE event_id = ?;
                    """,
                    (event.event_id,),
                )
                existing = cur.fetchone()
                if existing is None or existing["payload_json"] != payload_json:
                    conn.close()
                    raise ValueError(
                        f"conflicting_execution_event_payload: {event.event_id}"
                    )
        conn.commit()
        conn.close()

    def list_execution_events(
        self,
        *,
        strategy_id: Optional[str] = None,
        symbol: Optional[str] = None,
        order_id: Optional[str] = None,
        trade_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ExecutionEvent]:
        where_parts: list[str] = []
        params: list[object] = []

        if strategy_id is not None:
            where_parts.append("strategy_id = ?")
            params.append(strategy_id)
        if symbol is not None:
            where_parts.append("symbol = ?")
            params.append(symbol)
        if order_id is not None:
            where_parts.append("order_id = ?")
            params.append(order_id)
        if trade_id is not None:
            where_parts.append("trade_id = ?")
            params.append(trade_id)

        where_sql = ""
        if where_parts:
            where_sql = "WHERE " + " AND ".join(where_parts)

        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT payload_json
            FROM core_execution_events
            {where_sql}
            ORDER BY
                REPLACE(occurred_at, 'Z', '+00:00') ASC,
                sequence ASC,
                event_id ASC
            LIMIT ?
            OFFSET ?;
            """,
            [*params, limit, offset],
        )
        rows = cur.fetchall()
        conn.close()
        return [ExecutionEvent.model_validate_json(row["payload_json"]) for row in rows]

    def save_trade(self, trade: Trade) -> None:
        normalized_trade = Trade.model_validate(trade)
        payload_json = normalized_trade.to_canonical_json()

        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO core_trades (
                trade_id,
                position_id,
                strategy_id,
                symbol,
                opened_at,
                payload_json
            )
            VALUES (
                :trade_id,
                :position_id,
                :strategy_id,
                :symbol,
                :opened_at,
                :payload_json
            )
            ON CONFLICT(trade_id) DO UPDATE SET
                position_id = excluded.position_id,
                strategy_id = excluded.strategy_id,
                symbol = excluded.symbol,
                opened_at = excluded.opened_at,
                payload_json = excluded.payload_json;
            """,
            {
                "trade_id": normalized_trade.trade_id,
                "position_id": normalized_trade.position_id,
                "strategy_id": normalized_trade.strategy_id,
                "symbol": normalized_trade.symbol,
                "opened_at": normalized_trade.opened_at,
                "payload_json": payload_json,
            },
        )
        conn.commit()
        conn.close()

    def get_trade(self, trade_id: str) -> Optional[Trade]:
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT payload_json
            FROM core_trades
            WHERE trade_id = ?;
            """,
            (trade_id,),
        )
        row = cur.fetchone()
        conn.close()
        if row is None:
            return None
        return Trade.model_validate_json(row["payload_json"])

    def list_trades(
        self,
        *,
        strategy_id: Optional[str] = None,
        symbol: Optional[str] = None,
        position_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Trade]:
        where_parts: list[str] = []
        params: list[object] = []

        if strategy_id is not None:
            where_parts.append("strategy_id = ?")
            params.append(strategy_id)
        if symbol is not None:
            where_parts.append("symbol = ?")
            params.append(symbol)
        if position_id is not None:
            where_parts.append("position_id = ?")
            params.append(position_id)

        where_sql = ""
        if where_parts:
            where_sql = "WHERE " + " AND ".join(where_parts)

        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT payload_json
            FROM core_trades
            {where_sql}
            ORDER BY
                REPLACE(opened_at, 'Z', '+00:00') ASC,
                trade_id ASC
            LIMIT ?
            OFFSET ?;
            """,
            [*params, limit, offset],
        )
        rows = cur.fetchall()
        conn.close()
        return [Trade.model_validate_json(row["payload_json"]) for row in rows]

