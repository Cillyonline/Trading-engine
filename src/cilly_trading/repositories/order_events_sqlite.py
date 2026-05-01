from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any, Optional

from cilly_trading.db import DEFAULT_DB_PATH, init_db
from cilly_trading.repositories import OrderEventRepository

ORDER_LIFECYCLE_STATES = (
    "created",
    "submitted",
    "filled",
    "partially_filled",
    "cancelled",
)


class SqliteOrderEventRepository(OrderEventRepository):
    """SQLite repository for deterministic order lifecycle event reads."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        if db_path is None:
            db_path = DEFAULT_DB_PATH
        self._db_path = Path(db_path)
        init_db(self._db_path)
        self._ensure_order_events_table()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        return conn

    def _connection(self):
        return closing(self._get_connection())

    def _ensure_order_events_table(self) -> None:
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS order_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                order_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                strategy TEXT NOT NULL,
                state TEXT NOT NULL,
                event_timestamp TEXT NOT NULL,
                event_sequence INTEGER NOT NULL,
                metadata_json TEXT
            );
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_order_events_filters
              ON order_events(symbol, strategy, run_id);
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_order_events_ordering
              ON order_events(event_timestamp, run_id, order_id, event_sequence, id);
            """
        )
        conn.commit()
        conn.close()

    def save_events(self, events: list[dict[str, Any]]) -> None:
        if not events:
            return

        payload_rows: list[dict[str, Any]] = []
        for event in events:
            state = str(event.get("state", ""))
            if state not in ORDER_LIFECYCLE_STATES:
                raise ValueError(f"invalid_order_lifecycle_state: {state}")

            metadata = event.get("metadata")
            metadata_json: Optional[str] = None
            if metadata is not None:
                metadata_json = json.dumps(
                    metadata,
                    separators=(",", ":"),
                    sort_keys=True,
                    ensure_ascii=False,
                )

            payload_rows.append(
                {
                    "run_id": str(event["run_id"]),
                    "order_id": str(event["order_id"]),
                    "symbol": str(event["symbol"]),
                    "strategy": str(event["strategy"]),
                    "state": state,
                    "event_timestamp": str(event["event_timestamp"]),
                    "event_sequence": int(event.get("event_sequence", 0)),
                    "metadata_json": metadata_json,
                }
            )

        conn = self._get_connection()
        cur = conn.cursor()
        cur.executemany(
            """
            INSERT INTO order_events (
                run_id,
                order_id,
                symbol,
                strategy,
                state,
                event_timestamp,
                event_sequence,
                metadata_json
            )
            VALUES (
                :run_id,
                :order_id,
                :symbol,
                :strategy,
                :state,
                :event_timestamp,
                :event_sequence,
                :metadata_json
            );
            """,
            payload_rows,
        )
        conn.commit()
        conn.close()

    def read_order_events(
        self,
        *,
        symbol: Optional[str] = None,
        strategy: Optional[str] = None,
        run_id: Optional[str] = None,
        order_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        where_clauses: list[str] = []
        params: list[object] = []

        if symbol is not None:
            where_clauses.append("symbol = ?")
            params.append(symbol)
        if strategy is not None:
            where_clauses.append("strategy = ?")
            params.append(strategy)
        if run_id is not None:
            where_clauses.append("run_id = ?")
            params.append(run_id)
        if order_id is not None:
            where_clauses.append("order_id = ?")
            params.append(order_id)

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        order_sql = """
            ORDER BY
                REPLACE(event_timestamp, 'Z', '+00:00') ASC,
                run_id ASC,
                symbol ASC,
                strategy ASC,
                order_id ASC,
                event_sequence ASC,
                id ASC
        """

        conn = self._get_connection()
        cur = conn.cursor()

        cur.execute(f"SELECT COUNT(*) FROM order_events {where_sql};", params)
        total = int(cur.fetchone()[0])

        cur.execute(
            f"""
            SELECT
                run_id,
                order_id,
                symbol,
                strategy,
                state,
                event_timestamp,
                event_sequence,
                metadata_json
            FROM order_events
            {where_sql}
            {order_sql}
            LIMIT ?
            OFFSET ?;
            """,
            [*params, limit, offset],
        )
        rows = cur.fetchall()
        conn.close()

        items: list[dict[str, Any]] = []
        for row in rows:
            metadata_json = row["metadata_json"]
            metadata: Any = None
            if metadata_json is not None:
                metadata = json.loads(metadata_json)

            items.append(
                {
                    "run_id": row["run_id"],
                    "order_id": row["order_id"],
                    "symbol": row["symbol"],
                    "strategy": row["strategy"],
                    "state": row["state"],
                    "event_timestamp": row["event_timestamp"],
                    "event_sequence": row["event_sequence"],
                    "metadata": metadata,
                }
            )

        return items, total
