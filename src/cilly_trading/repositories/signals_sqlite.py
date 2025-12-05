"""
SQLite-Implementierung des SignalRepository.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import List, Optional

from cilly_trading.db import init_db, DEFAULT_DB_PATH  # type: ignore
from cilly_trading.models import Signal
from cilly_trading.repositories import SignalRepository


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

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def save_signals(self, signals: List[Signal]) -> None:
        if not signals:
            return

        conn = self._get_connection()
        cur = conn.cursor()

        cur.executemany(
    """
    INSERT INTO signals (
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
        data_source
    )
    VALUES (
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
        :data_source
    );
    """,
    [
        {
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
                data_source
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
            if row["confirmation_rule"] is not None:
                signal["confirmation_rule"] = row["confirmation_rule"]

            if row["entry_zone_from"] is not None and row["entry_zone_to"] is not None:
                signal["entry_zone"] = {
                    "from_": row["entry_zone_from"],
                    "to": row["entry_zone_to"],
                }

            result.append(signal)

        return result
