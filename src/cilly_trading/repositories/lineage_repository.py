"""SQLite repository for analysis lineage records."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from cilly_trading.db import DEFAULT_DB_PATH, init_db
from cilly_trading.engine.lineage import LineageContext


@dataclass(frozen=True)
class LineageRecord:
    """Persisted lineage record."""

    analysis_run_id: str
    snapshot_id: str
    ingestion_run_id: str
    created_at: str


class SqliteLineageRepository:
    """Persist and query lineage records in SQLite."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        if db_path is None:
            db_path = DEFAULT_DB_PATH

        self._db_path = Path(db_path)
        init_db(self._db_path)
        self._ensure_table()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_table(self) -> None:
        """Ensure the lineage table and indexes exist."""
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS analysis_lineage (
                analysis_run_id TEXT PRIMARY KEY,
                snapshot_id TEXT NOT NULL,
                ingestion_run_id TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_analysis_lineage_snapshot
              ON analysis_lineage(snapshot_id);
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_analysis_lineage_ingestion
              ON analysis_lineage(ingestion_run_id);
            """
        )
        conn.commit()
        conn.close()

    def save_lineage(self, ctx: LineageContext) -> None:
        """Persist a lineage context.

        Args:
            ctx: Lineage context to persist.
        """
        conn = self._get_connection()
        cur = conn.cursor()
        created_at = ctx.created_at
        if isinstance(created_at, datetime):
            created_at_value = created_at.isoformat()
        else:
            created_at_value = str(created_at)
        cur.execute(
            """
            INSERT INTO analysis_lineage (
                analysis_run_id,
                snapshot_id,
                ingestion_run_id,
                created_at
            )
            VALUES (?, ?, ?, ?);
            """,
            (
                ctx.analysis_run_id,
                ctx.snapshot_id,
                ctx.ingestion_run_id,
                created_at_value,
            ),
        )
        conn.commit()
        conn.close()

    def get_by_analysis_run_id(self, analysis_run_id: str) -> Optional[LineageRecord]:
        """Fetch a lineage record by analysis run ID.

        Args:
            analysis_run_id: Analysis run identifier.

        Returns:
            Lineage record if present, otherwise None.
        """
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                analysis_run_id,
                snapshot_id,
                ingestion_run_id,
                created_at
            FROM analysis_lineage
            WHERE analysis_run_id = ?
            LIMIT 1;
            """,
            (analysis_run_id,),
        )
        row = cur.fetchone()
        conn.close()
        if row is None:
            return None
        return LineageRecord(
            analysis_run_id=row["analysis_run_id"],
            snapshot_id=row["snapshot_id"],
            ingestion_run_id=row["ingestion_run_id"],
            created_at=row["created_at"],
        )

    def list_by_snapshot_id(self, snapshot_id: str) -> List[LineageRecord]:
        """List lineage records for a snapshot.

        Args:
            snapshot_id: Snapshot identifier to filter on.

        Returns:
            List of lineage records for the snapshot.
        """
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                analysis_run_id,
                snapshot_id,
                ingestion_run_id,
                created_at
            FROM analysis_lineage
            WHERE snapshot_id = ?
            ORDER BY created_at DESC, analysis_run_id DESC;
            """,
            (snapshot_id,),
        )
        rows = cur.fetchall()
        conn.close()
        return [
            LineageRecord(
                analysis_run_id=row["analysis_run_id"],
                snapshot_id=row["snapshot_id"],
                ingestion_run_id=row["ingestion_run_id"],
                created_at=row["created_at"],
            )
            for row in rows
        ]
