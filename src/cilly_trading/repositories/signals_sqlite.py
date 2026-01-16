"""
SQLite-Implementierung des SignalRepository.
"""

from __future__ import annotations

import json
import sqlite3
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
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_signal_columns(self) -> None:
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(signals);")
        columns = {row["name"] for row in cur.fetchall()}
        missing_columns = []
        if "analysis_run_id" not in columns:
            missing_columns.append(("analysis_run_id", "TEXT"))
        if "ingestion_run_id" not in columns:
            missing_columns.append(("ingestion_run_id", "TEXT"))
        if "reasons_json" not in columns:
            missing_columns.append(("reasons_json", "TEXT"))

        for column_name, column_type in missing_columns:
            cur.execute(f"ALTER TABLE signals ADD COLUMN {column_name} {column_type};")
        if missing_columns:
            conn.commit()
        conn.close()

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

        conn = self._get_connection()
        cur = conn.cursor()

        cur.executemany(
            """
            INSERT INTO signals (
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
                confirmation_rule,
                timeframe,
                market_type,
                data_source,
                reasons_json
            )
            VALUES (
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
                :confirmation_rule,
                :timeframe,
                :market_type,
                :data_source,
                :reasons_json
            );
            """,
            [
                {
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
        conn.close()

    def list_signals(self, limit: int = 100) -> List[Signal]:
        conn = self._get_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT
                id,
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
        conn.close()

        result: List[Signal] = []
        for row in rows:
            signal: Signal = {
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

            result.append(signal)

        return result

    def read_signals(
        self,
        *,
        symbol: Optional[str] = None,
        strategy: Optional[str] = None,
        preset: Optional[str] = None,
        from_: Optional[datetime] = None,
        to: Optional[datetime] = None,
        sort: str = "created_at_desc",
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Signal], int]:
        where_clauses = []
        params: List[object] = []

        if symbol is not None:
            where_clauses.append("symbol = ?")
            params.append(symbol)
        if strategy is not None:
            where_clauses.append("strategy = ?")
            params.append(strategy)
        if preset is not None:
            where_clauses.append("timeframe = ?")
            params.append(preset)
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

        conn = self._get_connection()
        cur = conn.cursor()

        count_query = f"SELECT COUNT(*) FROM signals {where_sql};"
        cur.execute(count_query, params)
        total = int(cur.fetchone()[0])

        data_query = f"""
            SELECT
                id,
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
        conn.close()

        result: List[Signal] = []
        for row in rows:
            signal: Signal = {
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

            result.append(signal)

        return result, total

    def read_screener_results(
        self,
        *,
        strategy: str,
        timeframe: str,
        min_score: Optional[float] = None,
    ) -> List[dict]:
        where_clauses = ["strategy = ?", "timeframe = ?", "stage = ?"]
        params: List[object] = [strategy, timeframe, "setup"]

        if min_score is not None:
            where_clauses.append("score >= ?")
            params.append(min_score)

        where_sql = "WHERE " + " AND ".join(where_clauses)
        order_sql = "ORDER BY score DESC, symbol ASC"

        conn = self._get_connection()
        cur = conn.cursor()
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
            {order_sql};
        """
        cur.execute(query, params)
        rows = cur.fetchall()
        conn.close()

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

        return result


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
