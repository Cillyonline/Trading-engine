"""
SQLite-Repository für Analyse-Runs.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from cilly_trading.db import DEFAULT_DB_PATH, init_db
from cilly_trading.engine.core import AnalysisRun


class SqliteAnalysisRunRepository:
    """
    Repository für Analyse-Run-Metadaten und Ergebnisse.
    """

    def __init__(self, db_path: Optional[Path] = None) -> None:
        if db_path is None:
            db_path = DEFAULT_DB_PATH

        self._db_path = Path(db_path)
        init_db(self._db_path)

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def ingestion_run_exists(self, ingestion_run_id: str) -> bool:
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT 1
            FROM ingestion_runs
            WHERE ingestion_run_id = ?
            LIMIT 1;
            """,
            (ingestion_run_id,),
        )
        row = cur.fetchone()
        conn.close()
        return row is not None

    def ingestion_run_is_ready(
        self,
        ingestion_run_id: str,
        *,
        symbols: list[str],
        timeframe: str,
    ) -> bool:
        try:
            conn = self._get_connection()
        except sqlite3.Error:
            return False

        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT 1
                FROM ingestion_runs
                WHERE ingestion_run_id = ?
                LIMIT 1;
                """,
                (ingestion_run_id,),
            )
            if cur.fetchone() is None:
                return False

            for symbol in symbols:
                cur.execute(
                    """
                    SELECT 1
                    FROM ohlcv_snapshots
                    WHERE ingestion_run_id = ?
                      AND symbol = ?
                      AND timeframe = ?
                    LIMIT 1;
                    """,
                    (ingestion_run_id, symbol, timeframe),
                )
                if cur.fetchone() is None:
                    return False
            return True
        except sqlite3.Error:
            return False
        finally:
            conn.close()

    def get_run(self, analysis_run_id: str) -> Optional[Dict[str, Any]]:
        """
        Lädt einen Analyse-Run anhand der Run-ID.

        Args:
            analysis_run_id: Eindeutige ID für den Analyse-Run.

        Returns:
            Optionaler Dict mit gespeicherten Run-Daten.
        """
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                analysis_run_id,
                ingestion_run_id,
                request_payload,
                result_payload,
                created_at
            FROM analysis_runs
            WHERE analysis_run_id = ?;
            """,
            (analysis_run_id,),
        )
        row = cur.fetchone()
        conn.close()

        if row is None:
            return None

        return {
            "analysis_run_id": row["analysis_run_id"],
            "ingestion_run_id": row["ingestion_run_id"],
            "request": json.loads(row["request_payload"]),
            "result": json.loads(row["result_payload"]),
            "created_at": row["created_at"],
        }

    def save_run(
        self,
        *,
        analysis_run_id: str,
        ingestion_run_id: str,
        request_payload: Dict[str, Any],
        result_payload: Dict[str, Any],
    ) -> None:
        """
        Speichert einen Analyse-Run mit Request- und Result-Payload.

        Args:
            analysis_run_id: Eindeutige ID für den Analyse-Run.
            ingestion_run_id: Referenz auf den Snapshot/Run der Ingestion.
            request_payload: Request-Daten als JSON-serialisierbares Dict.
            result_payload: Ergebnis-Daten als JSON-serialisierbares Dict.
        """
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO analysis_runs (
                analysis_run_id,
                ingestion_run_id,
                request_payload,
                result_payload,
                created_at
            )
            VALUES (?, ?, ?, ?, ?);
            """,
            (
                analysis_run_id,
                ingestion_run_id,
                json.dumps(request_payload, sort_keys=True),
                json.dumps(result_payload, sort_keys=True),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
        conn.close()

    def save_analysis_run(
        self,
        analysis_run: AnalysisRun,
        *,
        result_payload: Dict[str, Any],
    ) -> None:
        """Persist an analysis run using the existing schema.

        Args:
            analysis_run: AnalysisRun entity containing IDs and request payload.
            result_payload: Result payload to persist.
        """
        self.save_run(
            analysis_run_id=analysis_run.analysis_run_id,
            ingestion_run_id=analysis_run.ingestion_run_id,
            request_payload=analysis_run.request_payload,
            result_payload=result_payload,
        )
