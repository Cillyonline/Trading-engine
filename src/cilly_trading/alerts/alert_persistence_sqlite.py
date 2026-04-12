"""SQLite-backed persistence for bounded alert configuration and delivery history."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from cilly_trading.db import DEFAULT_DB_PATH, init_db

from .alert_dispatcher import AlertDispatchResult
from .alert_models import AlertEvent

BOUNDED_DELIVERY_MODE = "bounded_non_live"


class SqliteAlertConfigurationRepository:
    """Persist alert configuration records in SQLite."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        if db_path is None:
            db_path = DEFAULT_DB_PATH
        self._db_path = Path(db_path)
        init_db(self._db_path)
        self._ensure_schema()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS alert_configurations (
                alert_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                source TEXT NOT NULL,
                metric TEXT NOT NULL,
                operator TEXT NOT NULL,
                threshold REAL NOT NULL,
                severity TEXT NOT NULL,
                enabled INTEGER NOT NULL,
                tags_json TEXT NOT NULL
            );
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_alert_configurations_name
              ON alert_configurations(name, alert_id);
            """
        )
        conn.commit()
        conn.close()

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO alert_configurations (
                    alert_id,
                    name,
                    description,
                    source,
                    metric,
                    operator,
                    threshold,
                    severity,
                    enabled,
                    tags_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                self._to_row_payload(payload),
            )
            conn.commit()
            return payload
        except sqlite3.IntegrityError as exc:
            raise ValueError("alert_configuration_exists") from exc
        finally:
            conn.close()

    def update(self, alert_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE alert_configurations
            SET
                name = ?,
                description = ?,
                source = ?,
                metric = ?,
                operator = ?,
                threshold = ?,
                severity = ?,
                enabled = ?,
                tags_json = ?
            WHERE alert_id = ?;
            """,
            (
                payload["name"],
                payload.get("description"),
                payload["source"],
                payload["metric"],
                payload["operator"],
                payload["threshold"],
                payload["severity"],
                1 if payload["enabled"] else 0,
                _serialize_tags(payload.get("tags", [])),
                alert_id,
            ),
        )
        updated = cur.rowcount > 0
        conn.commit()
        conn.close()
        if not updated:
            return None
        return payload

    def get(self, alert_id: str) -> dict[str, Any] | None:
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                alert_id,
                name,
                description,
                source,
                metric,
                operator,
                threshold,
                severity,
                enabled,
                tags_json
            FROM alert_configurations
            WHERE alert_id = ?
            LIMIT 1;
            """,
            (alert_id,),
        )
        row = cur.fetchone()
        conn.close()
        if row is None:
            return None
        return self._from_row(row)

    def list(self) -> list[dict[str, Any]]:
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                alert_id,
                name,
                description,
                source,
                metric,
                operator,
                threshold,
                severity,
                enabled,
                tags_json
            FROM alert_configurations
            ORDER BY alert_id ASC;
            """
        )
        rows = cur.fetchall()
        conn.close()
        return [self._from_row(row) for row in rows]

    def delete(self, alert_id: str) -> bool:
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM alert_configurations WHERE alert_id = ?;", (alert_id,))
        deleted = cur.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    @staticmethod
    def _to_row_payload(payload: dict[str, Any]) -> tuple[Any, ...]:
        return (
            payload["alert_id"],
            payload["name"],
            payload.get("description"),
            payload["source"],
            payload["metric"],
            payload["operator"],
            payload["threshold"],
            payload["severity"],
            1 if payload["enabled"] else 0,
            _serialize_tags(payload.get("tags", [])),
        )

    @staticmethod
    def _from_row(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "alert_id": row["alert_id"],
            "name": row["name"],
            "description": row["description"],
            "source": row["source"],
            "metric": row["metric"],
            "operator": row["operator"],
            "threshold": row["threshold"],
            "severity": row["severity"],
            "enabled": bool(row["enabled"]),
            "tags": _deserialize_tags(row["tags_json"]),
        }


class SqliteAlertDeliveryHistoryRepository:
    """Persist bounded alert delivery attempts and expose deterministic reads."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        if db_path is None:
            db_path = DEFAULT_DB_PATH
        self._db_path = Path(db_path)
        init_db(self._db_path)
        self._ensure_schema()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS alert_delivery_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL,
                event_payload_json TEXT NOT NULL,
                channel_name TEXT NOT NULL,
                delivered INTEGER NOT NULL,
                error TEXT,
                occurred_at TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                delivery_mode TEXT NOT NULL
            );
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_alert_delivery_history_ordering
              ON alert_delivery_history(
                  REPLACE(occurred_at, 'Z', '+00:00') DESC,
                  event_id DESC,
                  id DESC
              );
            """
        )
        conn.commit()
        conn.close()

    def record_dispatch(
        self,
        *,
        event: AlertEvent,
        dispatch_result: AlertDispatchResult,
        delivery_mode: str = BOUNDED_DELIVERY_MODE,
    ) -> None:
        if not dispatch_result.deliveries:
            return

        now = datetime.now(timezone.utc).isoformat()
        event_payload_json = event.model_dump_json()

        rows = [
            (
                dispatch_result.event_id,
                event_payload_json,
                delivery.channel_name,
                1 if delivery.delivered else 0,
                delivery.error,
                event.occurred_at,
                now,
                delivery_mode,
            )
            for delivery in dispatch_result.deliveries
        ]

        conn = self._get_connection()
        cur = conn.cursor()
        cur.executemany(
            """
            INSERT INTO alert_delivery_history (
                event_id,
                event_payload_json,
                channel_name,
                delivered,
                error,
                occurred_at,
                recorded_at,
                delivery_mode
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            rows,
        )
        conn.commit()
        conn.close()

    def list_events(self, *, limit: int, offset: int) -> tuple[list[dict[str, Any]], int]:
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM alert_delivery_history;")
        total = int(cur.fetchone()[0])
        cur.execute(
            """
            SELECT event_payload_json
            FROM alert_delivery_history
            ORDER BY
                REPLACE(occurred_at, 'Z', '+00:00') DESC,
                event_id DESC,
                id DESC
            LIMIT ?
            OFFSET ?;
            """,
            (limit, offset),
        )
        rows = cur.fetchall()
        conn.close()
        return ([json.loads(row["event_payload_json"]) for row in rows], total)

    def list_delivery_results(
        self,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[dict[str, Any]], int]:
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM alert_delivery_history;")
        total = int(cur.fetchone()[0])
        cur.execute(
            """
            SELECT
                event_id,
                channel_name,
                delivered,
                error,
                occurred_at,
                recorded_at,
                delivery_mode
            FROM alert_delivery_history
            ORDER BY
                REPLACE(occurred_at, 'Z', '+00:00') DESC,
                event_id DESC,
                id DESC
            LIMIT ?
            OFFSET ?;
            """,
            (limit, offset),
        )
        rows = cur.fetchall()
        conn.close()
        items = [
            {
                "event_id": row["event_id"],
                "channel_name": row["channel_name"],
                "delivered": bool(row["delivered"]),
                "error": row["error"],
                "occurred_at": row["occurred_at"],
                "recorded_at": row["recorded_at"],
                "delivery_mode": row["delivery_mode"],
            }
            for row in rows
        ]
        return items, total


def _serialize_tags(tags: list[str]) -> str:
    return json.dumps(tags, separators=(",", ":"), ensure_ascii=False)


def _deserialize_tags(tags_json: str) -> list[str]:
    try:
        decoded = json.loads(tags_json)
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    if not isinstance(decoded, list):
        return []
    return [str(item) for item in decoded]


__all__ = [
    "BOUNDED_DELIVERY_MODE",
    "SqliteAlertConfigurationRepository",
    "SqliteAlertDeliveryHistoryRepository",
]
