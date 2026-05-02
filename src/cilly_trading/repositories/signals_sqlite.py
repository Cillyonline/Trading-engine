"""
SQLite-Implementierung des SignalRepository.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Tuple

from cilly_trading.db import init_db, DEFAULT_DB_PATH  # type: ignore
from cilly_trading.models import Signal, SignalReason, compute_signal_id, compute_signal_reason_id
from cilly_trading.repositories import SignalRepository


class SignalReconstructionError(ValueError):
    """Raised when persisted signal data cannot be reconstructed deterministically."""


class SqliteSignalRepository(SignalRepository):
    """
    Speichert und lädt Signals aus einer SQLite-Datenbank.
    """

    def __init__(self, db_path: Optional[Path] = None) -> None:
        if db_path is None:
            db_path = DEFAULT_DB_PATH

        self._db_path = Path(db_path)
        # sicherstellen, dass DB und Tabellen existieren
        init_db(self._db_path)
        self._ensure_signal_columns()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        return conn

    def _connection(self):
        return closing(self._get_connection())

    def _ensure_signal_columns(self) -> None:
        with self._connection() as conn:
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(signals);")
            columns = {row["name"] for row in cur.fetchall()}
            missing_columns = []
            if "signal_id" not in columns:
                missing_columns.append(("signal_id", "TEXT"))
            if "analysis_run_id" not in columns:
                missing_columns.append(("analysis_run_id", "TEXT"))
            if "ingestion_run_id" not in columns:
                missing_columns.append(("ingestion_run_id", "TEXT"))
            if "reasons_json" not in columns:
                missing_columns.append(("reasons_json", "TEXT"))
            if "stop_loss" not in columns:
                missing_columns.append(("stop_loss", "REAL"))

            for column_name, column_type in missing_columns:
                cur.execute(f"ALTER TABLE signals ADD COLUMN {column_name} {column_type};")
            cur.execute(
                """
                DELETE FROM signals
                WHERE id IN (
                    SELECT older.id
                    FROM signals AS older
                    JOIN signals AS newer
                      ON older.ingestion_run_id = newer.ingestion_run_id
                     AND older.signal_id = newer.signal_id
                     AND older.id < newer.id
                    WHERE older.ingestion_run_id IS NOT NULL AND older.signal_id IS NOT NULL
                );
                """
            )
            cur.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_signals_ingestion_run_signal_id_unique
                  ON signals(ingestion_run_id, signal_id)
                  WHERE ingestion_run_id IS NOT NULL AND signal_id IS NOT NULL;
                """
            )
            cur.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_signals_analysis_run_signal_id_unique
                  ON signals(analysis_run_id, signal_id)
                  WHERE analysis_run_id IS NOT NULL AND signal_id IS NOT NULL;
                """
            )
            conn.commit()

    def _serialize_reasons(self, reasons: Optional[List[SignalReason]]) -> Optional[str]:
        if reasons is None:
            return None
        return json.dumps(reasons, separators=(",", ":"), ensure_ascii=False, sort_keys=True)

    def _deserialize_reasons(self, payload: Optional[str]) -> Optional[List[SignalReason]]:
        if payload is None:
            return None
        try:
            reasons = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ValueError("Persisted reasons payload is not valid JSON.") from exc
        if not isinstance(reasons, list):
            raise ValueError("Persisted reasons payload must be a list.")
        return reasons

    def save_signals(self, signals: List[Signal]) -> None:
        if not signals:
            return
        for signal in signals:
            if not signal.get("ingestion_run_id"):
                raise ValueError("ingestion_run_id is required for signal persistence")

        with self._connection() as conn:
            cur = conn.cursor()
            cur.executemany(
                """
                INSERT OR IGNORE INTO signals (
                    signal_id,
                    analysis_run_id,
                    ingestion_run_id,
                    symbol,
                    strategy,
                    direction,
                    score,
                    timestamp,
                    stage,
                    entry_zone_from,
                    entry_zone_to,
                    stop_loss,
                    confirmation_rule,
                    timeframe,
                    market_type,
                    data_source,
                    reasons_json
                )
                VALUES (
                    :signal_id,
                    :analysis_run_id,
                    :ingestion_run_id,
                    :symbol,
                    :strategy,
                    :direction,
                    :score,
                    :timestamp,
                    :stage,
                    :entry_zone_from,
                    :entry_zone_to,
                    :stop_loss,
                    :confirmation_rule,
                    :timeframe,
                    :market_type,
                    :data_source,
                    :reasons_json
                );
                """,
                [
                    {
                        "signal_id": (
                            s.get("signal_id")
                            or (compute_signal_id(s) if s.get("timestamp") else None)
                        ),
                        "analysis_run_id": s.get("analysis_run_id"),
                        "ingestion_run_id": s.get("ingestion_run_id"),
                        "symbol": s["symbol"],
                        "strategy": s["strategy"],
                        "direction": s["direction"],
                        "score": s["score"],
                        "timestamp": s["timestamp"],
                        "stage": s["stage"],
                        "entry_zone_from": (
                            s["entry_zone"]["from_"] if "entry_zone" in s and s["entry_zone"] else None
                        ),
                        "entry_zone_to": (
                            s["entry_zone"]["to"] if "entry_zone" in s and s["entry_zone"] else None
                        ),
                        "stop_loss": s.get("stop_loss"),
                        "confirmation_rule": s.get("confirmation_rule"),
                        "timeframe": s["timeframe"],
                        "market_type": s["market_type"],
                        "data_source": s["data_source"],
                        "reasons_json": self._serialize_reasons(s.get("reasons")),
                    }
                    for s in signals
                ],
            )
            conn.commit()

    def list_signals(self, limit: int = 100) -> List[Signal]:
        with self._connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT
                    id,
                    signal_id,
                    analysis_run_id,
                    ingestion_run_id,
                    symbol,
                    strategy,
                    direction,
                    score,
                    timestamp,
                    stage,
                    entry_zone_from,
                    entry_zone_to,
                    stop_loss,
                    confirmation_rule,
                    timeframe,
                    market_type,
                    data_source,
                    reasons_json
                FROM signals
                ORDER BY id DESC
                LIMIT ?;
                """,
                (limit,),
            )
            rows = cur.fetchall()

        result: List[Signal] = []
        for row in rows:
            signal: Signal = {
                "signal_id": row["signal_id"],
                "analysis_run_id": row["analysis_run_id"],
                "ingestion_run_id": row["ingestion_run_id"],
                "symbol": row["symbol"],
                "strategy": row["strategy"],
                "direction": row["direction"],
                "score": row["score"],
                "timestamp": row["timestamp"],
                "stage": row["stage"],
                "timeframe": row["timeframe"],
                "market_type": row["market_type"],
                "data_source": row["data_source"],
            }
            if signal["analysis_run_id"] is None:
                signal.pop("analysis_run_id")
            if signal["ingestion_run_id"] is None:
                signal.pop("ingestion_run_id")
            if signal["signal_id"] is None:
                signal.pop("signal_id")
            reasons = self._deserialize_reasons(row["reasons_json"])
            if reasons is not None:
                signal["reasons"] = reasons
            if row["confirmation_rule"] is not None:
                signal["confirmation_rule"] = row["confirmation_rule"]

            if row["entry_zone_from"] is not None and row["entry_zone_to"] is not None:
                signal["entry_zone"] = {
                    "from_": row["entry_zone_from"],
                    "to": row["entry_zone_to"],
                }
            if row["stop_loss"] is not None:
                signal["stop_loss"] = row["stop_loss"]

            result.append(signal)

        return result

    def read_signals(
        self,
        *,
        symbol: Optional[str] = None,
        strategy: Optional[str] = None,
        timeframe: Optional[str] = None,
        ingestion_run_id: Optional[str] = None,
        from_: Optional[datetime] = None,
        to: Optional[datetime] = None,
        sort: str = "created_at_desc",
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Signal], int]:
        return self._read_signals(
            symbol=symbol,
            strategy=strategy,
            timeframe=timeframe,
            ingestion_run_id=ingestion_run_id,
            from_=from_,
            to=to,
            sort=sort,
            limit=limit,
            offset=offset,
            dedupe_unfiltered_reads=ingestion_run_id is None,
        )

    def read_signals_raw(
        self,
        *,
        symbol: Optional[str] = None,
        strategy: Optional[str] = None,
        timeframe: Optional[str] = None,
        ingestion_run_id: Optional[str] = None,
        from_: Optional[datetime] = None,
        to: Optional[datetime] = None,
        sort: str = "created_at_desc",
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Signal], int]:
        return self._read_signals(
            symbol=symbol,
            strategy=strategy,
            timeframe=timeframe,
            ingestion_run_id=ingestion_run_id,
            from_=from_,
            to=to,
            sort=sort,
            limit=limit,
            offset=offset,
            dedupe_unfiltered_reads=False,
        )

    def _read_signals(
        self,
        *,
        symbol: Optional[str],
        strategy: Optional[str],
        timeframe: Optional[str],
        ingestion_run_id: Optional[str],
        from_: Optional[datetime],
        to: Optional[datetime],
        sort: str,
        limit: int,
        offset: int,
        dedupe_unfiltered_reads: bool,
    ) -> Tuple[List[Signal], int]:
        where_clauses = []
        params: List[object] = []

        if symbol is not None:
            where_clauses.append("symbol = ?")
            params.append(symbol)
        if strategy is not None:
            where_clauses.append("strategy = ?")
            params.append(strategy)
        if timeframe is not None:
            where_clauses.append("timeframe = ?")
            params.append(timeframe)
        if ingestion_run_id is not None:
            where_clauses.append("ingestion_run_id = ?")
            params.append(ingestion_run_id)
        normalized_timestamp = "REPLACE(timestamp, 'Z', '+00:00')"
        if from_ is not None:
            where_clauses.append(f"{normalized_timestamp} >= ?")
            params.append(from_.isoformat())
        if to is not None:
            where_clauses.append(f"{normalized_timestamp} <= ?")
            params.append(to.isoformat())

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        if sort == "created_at_asc":
            order_sql = "ORDER BY timestamp ASC, id ASC"
        else:
            order_sql = "ORDER BY timestamp DESC, id DESC"

        with self._connection() as conn:
            cur = conn.cursor()

            if dedupe_unfiltered_reads:
                # Keep one row per deterministic signal identity when reads are unscoped
                # and dedupe is enabled. This prevents repeated entries caused by
                # reruns that persisted the same signal under a new ingestion_run_id.
                dedupe_identity_sql = (
                    "CASE "
                    "WHEN signal_id IS NOT NULL THEN signal_id "
                    "ELSE symbol || '|' || strategy || '|' || direction || '|' || "
                    "CAST(score AS TEXT) || '|' || timestamp || '|' || stage || '|' || "
                    "timeframe || '|' || market_type || '|' || data_source "
                    "END"
                )
                ranked_signals_cte = f"""
                    WITH ranked_signals AS (
                        SELECT
                            id,
                            signal_id,
                            analysis_run_id,
                            ingestion_run_id,
                            symbol,
                            strategy,
                            direction,
                            score,
                            timestamp,
                            stage,
                            entry_zone_from,
                            entry_zone_to,
                            stop_loss,
                            confirmation_rule,
                            timeframe,
                            market_type,
                            data_source,
                            reasons_json,
                            ROW_NUMBER() OVER (
                                PARTITION BY {dedupe_identity_sql}
                                ORDER BY {normalized_timestamp} DESC, id DESC
                            ) AS dedupe_rank
                        FROM signals
                        {where_sql}
                    )
                """
                count_query = f"""
                    {ranked_signals_cte}
                    SELECT COUNT(*)
                    FROM ranked_signals
                    WHERE dedupe_rank = 1;
                """
                cur.execute(count_query, params)
                total = int(cur.fetchone()[0])

                data_query = f"""
                    {ranked_signals_cte}
                    SELECT
                        id,
                        signal_id,
                        analysis_run_id,
                        ingestion_run_id,
                        symbol,
                        strategy,
                        direction,
                        score,
                        timestamp,
                        stage,
                        entry_zone_from,
                        entry_zone_to,
                        stop_loss,
                        confirmation_rule,
                        timeframe,
                        market_type,
                        data_source,
                        reasons_json
                    FROM ranked_signals
                    WHERE dedupe_rank = 1
                    {order_sql}
                    LIMIT ?
                    OFFSET ?;
                """
                cur.execute(data_query, [*params, limit, offset])
                rows = cur.fetchall()
            else:
                count_query = f"SELECT COUNT(*) FROM signals {where_sql};"
                cur.execute(count_query, params)
                total = int(cur.fetchone()[0])

                data_query = f"""
                    SELECT
                        id,
                        signal_id,
                        analysis_run_id,
                        ingestion_run_id,
                        symbol,
                        strategy,
                        direction,
                        score,
                        timestamp,
                        stage,
                        entry_zone_from,
                        entry_zone_to,
                        stop_loss,
                        confirmation_rule,
                        timeframe,
                        market_type,
                        data_source,
                        reasons_json
                    FROM signals
                    {where_sql}
                    {order_sql}
                    LIMIT ?
                    OFFSET ?;
                """
                cur.execute(data_query, [*params, limit, offset])
                rows = cur.fetchall()

        result: List[Signal] = []
        for row in rows:
            signal: Signal = {
                "signal_id": row["signal_id"],
                "analysis_run_id": row["analysis_run_id"],
                "ingestion_run_id": row["ingestion_run_id"],
                "symbol": row["symbol"],
                "strategy": row["strategy"],
                "direction": row["direction"],
                "score": row["score"],
                "timestamp": row["timestamp"],
                "stage": row["stage"],
                "timeframe": row["timeframe"],
                "market_type": row["market_type"],
                "data_source": row["data_source"],
            }
            if signal["analysis_run_id"] is None:
                signal.pop("analysis_run_id")
            if signal["ingestion_run_id"] is None:
                signal.pop("ingestion_run_id")
            if signal["signal_id"] is None:
                signal.pop("signal_id")
            reasons = self._deserialize_reasons(row["reasons_json"])
            if reasons is not None:
                signal["reasons"] = reasons
            if row["confirmation_rule"] is not None:
                signal["confirmation_rule"] = row["confirmation_rule"]

            if row["entry_zone_from"] is not None and row["entry_zone_to"] is not None:
                signal["entry_zone"] = {
                    "from_": row["entry_zone_from"],
                    "to": row["entry_zone_to"],
                }
            if row["stop_loss"] is not None:
                signal["stop_loss"] = row["stop_loss"]

            result.append(signal)

        return result, total

    def read_screener_results(
        self,
        *,
        strategy: str,
        timeframe: str,
        min_score: Optional[float] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[dict], int]:
        where_clauses = ["strategy = ?", "timeframe = ?", "stage = ?"]
        params: List[object] = [strategy, timeframe, "setup"]

        if min_score is not None:
            where_clauses.append("score >= ?")
            params.append(min_score)

        where_sql = "WHERE " + " AND ".join(where_clauses)
        order_sql = "ORDER BY score DESC, symbol ASC"

        with self._connection() as conn:
            cur = conn.cursor()
            cur.execute(f"SELECT COUNT(*) FROM signals {where_sql};", params)
            total = int(cur.fetchone()[0])

            query = f"""
                SELECT
                    symbol,
                    score,
                    strategy,
                    timeframe,
                    market_type,
                    timestamp
                FROM signals
                {where_sql}
                {order_sql}
                LIMIT ?
                OFFSET ?;
            """
            cur.execute(query, [*params, limit, offset])
            rows = cur.fetchall()

        result: List[dict] = []
        for row in rows:
            result.append(
                {
                    "symbol": row["symbol"],
                    "score": row["score"],
                    "strategy": row["strategy"],
                    "timeframe": row["timeframe"],
                    "market_type": row["market_type"],
                    "created_at": row["timestamp"],
                }
            )

        return result, total


def reconstruct_signal_explanation(signal: Signal) -> dict:
    """Reconstruct a signal explanation from persisted signal data.

    Args:
        signal: Persisted signal payload including deterministic reasons.

    Returns:
        Structured explanation payload derived from persisted data only.

    Raises:
        SignalReconstructionError: If required fields or reason integrity checks fail.
    """
    required_fields = (
        "analysis_run_id",
        "ingestion_run_id",
        "symbol",
        "strategy",
        "direction",
        "score",
        "timestamp",
        "stage",
        "timeframe",
        "market_type",
        "data_source",
    )
    missing_fields = [
        field for field in required_fields if field not in signal or signal[field] is None
    ]
    if missing_fields:
        raise SignalReconstructionError(
            f"Signal is missing required fields for reconstruction: {', '.join(missing_fields)}"
        )

    reasons = signal.get("reasons")
    if reasons is None:
        raise SignalReconstructionError("Signal reasons are missing; cannot reconstruct explanation.")
    if not isinstance(reasons, list):
        raise SignalReconstructionError("Signal reasons payload must be a list.")
    if not reasons:
        raise SignalReconstructionError("Signal reasons are empty; cannot reconstruct explanation.")

    expected_signal_id = compute_signal_id(signal)
    if signal.get("signal_id") and signal["signal_id"] != expected_signal_id:
        raise SignalReconstructionError("Signal ID does not match deterministic reconstruction.")

    for reason in reasons:
        for reason_field in ("reason_id", "reason_type", "signal_id", "rule_ref", "data_refs", "ordering_key"):
            if reason_field not in reason:
                raise SignalReconstructionError(
                    f"Signal reason is missing required field: {reason_field}"
                )

    ordered_reasons = sorted(reasons, key=lambda reason: (reason["ordering_key"], reason["reason_id"]))
    if reasons != ordered_reasons:
        raise SignalReconstructionError("Signal reasons are not in canonical order.")

    for reason in reasons:
        rule_ref = reason["rule_ref"]
        if not isinstance(rule_ref, dict):
            raise SignalReconstructionError("Signal reason rule_ref must be a dict.")
        if "rule_id" not in rule_ref or "rule_version" not in rule_ref:
            raise SignalReconstructionError("Signal reason rule_ref is incomplete.")
        data_refs = reason["data_refs"]
        if not isinstance(data_refs, list):
            raise SignalReconstructionError("Signal reason data_refs must be a list.")
        if not data_refs:
            raise SignalReconstructionError("Signal reason data_refs are empty.")
        for data_ref in data_refs:
            for data_field in ("data_type", "data_id", "value", "timestamp"):
                if data_field not in data_ref:
                    raise SignalReconstructionError(
                        f"Signal reason data_ref is missing required field: {data_field}"
                    )
        if reason["signal_id"] != expected_signal_id:
            raise SignalReconstructionError("Signal reason signal_id does not match reconstructed signal.")
        expected_reason_id = compute_signal_reason_id(
            signal_id=expected_signal_id,
            reason_type=reason["reason_type"],
            rule_ref=reason["rule_ref"],
            data_refs=reason["data_refs"],
        )
        if reason["reason_id"] != expected_reason_id:
            raise SignalReconstructionError("Signal reason ID does not match deterministic reconstruction.")

    explanation = {
        "signal_id": expected_signal_id,
        "analysis_run_id": signal["analysis_run_id"],
        "ingestion_run_id": signal["ingestion_run_id"],
        "symbol": signal["symbol"],
        "strategy": signal["strategy"],
        "direction": signal["direction"],
        "score": signal["score"],
        "timestamp": signal["timestamp"],
        "stage": signal["stage"],
        "timeframe": signal["timeframe"],
        "market_type": signal["market_type"],
        "data_source": signal["data_source"],
        "reasons": reasons,
    }
    if "entry_zone" in signal:
        explanation["entry_zone"] = signal["entry_zone"]
    if "confirmation_rule" in signal:
        explanation["confirmation_rule"] = signal["confirmation_rule"]

    return explanation
