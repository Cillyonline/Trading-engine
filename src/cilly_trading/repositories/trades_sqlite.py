"""SQLite-Implementierung des TradeRepository."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import List, Optional

from cilly_trading.models import PersistedTradePayload
from cilly_trading.repositories import TradeRepository
from cilly_trading.repositories._base_sqlite import BaseSqliteRepository


class SqliteTradeRepository(BaseSqliteRepository, TradeRepository):
    """Speichert und lädt Trades aus einer SQLite-Datenbank."""

    def save_trade(self, trade: PersistedTradePayload) -> int:
        with self._connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO trades (
                    signal_id,
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
                    :signal_id,
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
                    "signal_id": trade.get("signal_id"),
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
        return int(trade_id)

    def get_trade(self, trade_id: int) -> Optional[PersistedTradePayload]:
        with self._connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT
                    id, signal_id, symbol, strategy, stage,
                    entry_price, entry_date, exit_price, exit_date,
                    reason_entry, reason_exit, notes,
                    timeframe, market_type, data_source
                FROM trades
                WHERE id = ?
                LIMIT 1;
                """,
                (trade_id,),
            )
            row = cur.fetchone()

        if row is None:
            return None
        return self._row_to_payload(row)

    def list_trades(
        self,
        limit: int = 100,
        *,
        symbol: Optional[str] = None,
        strategy: Optional[str] = None,
        signal_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[PersistedTradePayload]:
        conditions = []
        params: list = []

        if symbol is not None:
            conditions.append("symbol = ?")
            params.append(symbol)
        if strategy is not None:
            conditions.append("strategy = ?")
            params.append(strategy)
        if signal_id is not None:
            conditions.append("signal_id = ?")
            params.append(signal_id)
        if status == "open":
            conditions.append("exit_price IS NULL")
        elif status == "closed":
            conditions.append("exit_price IS NOT NULL")

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        with self._connection() as conn:
            cur = conn.cursor()
            cur.execute(
                f"""
                SELECT
                    id, signal_id, symbol, strategy, stage,
                    entry_price, entry_date, exit_price, exit_date,
                    reason_entry, reason_exit, notes,
                    timeframe, market_type, data_source
                FROM trades
                {where}
                ORDER BY id DESC
                LIMIT ?;
                """,
                (*params, limit),
            )
            rows = cur.fetchall()

        return [self._row_to_payload(row) for row in rows]

    def update_trade_exit(
        self, trade_id: int, exit_price: float, exit_date: str, reason_exit: str
    ) -> bool:
        with self._connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE trades
                SET exit_price = :exit_price,
                    exit_date = :exit_date,
                    reason_exit = :reason_exit
                WHERE id = :trade_id;
                """,
                {
                    "exit_price": exit_price,
                    "exit_date": exit_date,
                    "reason_exit": reason_exit,
                    "trade_id": trade_id,
                },
            )
            conn.commit()
            return cur.rowcount > 0

    @staticmethod
    def _row_to_payload(row: sqlite3.Row) -> PersistedTradePayload:
        trade: PersistedTradePayload = {
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
        if row["signal_id"] is not None:
            trade["signal_id"] = row["signal_id"]
        if row["reason_exit"] is not None:
            trade["reason_exit"] = row["reason_exit"]
        if row["notes"] is not None:
            trade["notes"] = row["notes"]
        return trade
