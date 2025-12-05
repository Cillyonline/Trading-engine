"""
SQLite-Implementierung des TradeRepository.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import List, Optional

from cilly_trading.db import init_db, DEFAULT_DB_PATH  # type: ignore
from cilly_trading.models import Trade
from cilly_trading.repositories import TradeRepository


class SqliteTradeRepository(TradeRepository):
    """
    Speichert und lädt Trades aus einer SQLite-Datenbank.
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

    def save_trade(self, trade: Trade) -> int:
        conn = self._get_connection()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO trades (
                symbol,
                strategy,
                stage,
                entry_price,
                entry_date,
                exit_price,
                exit_date,
                reason_entry,
                reason_exit,
                notes,
                timeframe,
                market_type,
                data_source
            )
            VALUES (
                :symbol,
                :strategy,
                :stage,
                :entry_price,
                :entry_date,
                :exit_price,
                :exit_date,
                :reason_entry,
                :reason_exit,
                :notes,
                :timeframe,
                :market_type,
                :data_source
            );
            """,
            {
                "symbol": trade["symbol"],
                "strategy": trade["strategy"],
                "stage": trade["stage"],
                "entry_price": trade.get("entry_price"),
                "entry_date": trade.get("entry_date"),
                "exit_price": trade.get("exit_price"),
                "exit_date": trade.get("exit_date"),
                "reason_entry": trade["reason_entry"],
                "reason_exit": trade.get("reason_exit"),
                "notes": trade.get("notes"),
                "timeframe": trade["timeframe"],
                "market_type": trade["market_type"],
                "data_source": trade["data_source"],
            },
        )

        trade_id = cur.lastrowid
        conn.commit()
        conn.close()

        return int(trade_id)

    def list_trades(self, limit: int = 100) -> List[Trade]:
        conn = self._get_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT
                id,
                symbol,
                strategy,
                stage,
                entry_price,
                entry_date,
                exit_price,
                exit_date,
                reason_entry,
                reason_exit,
                notes,
                timeframe,
                market_type,
                data_source
            FROM trades
            ORDER BY id DESC
            LIMIT ?;
            """,
            (limit,),
        )

        rows = cur.fetchall()
        conn.close()

        result: List[Trade] = []
        for row in rows:
            trade: Trade = {
                "id": row["id"],
                "symbol": row["symbol"],
                "strategy": row["strategy"],
                "stage": row["stage"],
                "entry_price": row["entry_price"],
                "entry_date": row["entry_date"],
                "exit_price": row["exit_price"],
                "exit_date": row["exit_date"],
                "reason_entry": row["reason_entry"],
                "timeframe": row["timeframe"],
                "market_type": row["market_type"],
                "data_source": row["data_source"],
            }
            if row["reason_exit"] is not None:
                trade["reason_exit"] = row["reason_exit"]
            if row["notes"] is not None:
                trade["notes"] = row["notes"]

            result.append(trade)

        return result
