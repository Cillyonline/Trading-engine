"""SQLite repository for deterministic watchlist persistence."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import List, Optional

from cilly_trading.repositories import Watchlist, WatchlistRepository
from cilly_trading.repositories._base_sqlite import BaseSqliteRepository


class SqliteWatchlistRepository(BaseSqliteRepository, WatchlistRepository):
    """Persist named watchlists and ordered symbol membership in SQLite."""

    def _validate_payload(self, *, watchlist_id: str, name: str, symbols: List[str]) -> List[str]:
        normalized_symbols = [symbol.strip() for symbol in symbols]
        if not watchlist_id.strip():
            raise ValueError("watchlist_id must not be empty")
        if not name.strip():
            raise ValueError("name must not be empty")
        if not normalized_symbols:
            raise ValueError("watchlist symbols must not be empty")
        if any(not symbol for symbol in normalized_symbols):
            raise ValueError("watchlist symbols must not contain empty values")
        return normalized_symbols

    def _build_watchlist(self, row: sqlite3.Row, *, symbols: tuple[str, ...]) -> Watchlist:
        return Watchlist(
            watchlist_id=row["watchlist_id"],
            name=row["name"],
            symbols=symbols,
        )

    def _get_symbols(self, conn: sqlite3.Connection, watchlist_id: str) -> tuple[str, ...]:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT symbol
            FROM watchlist_symbols
            WHERE watchlist_id = ?
            ORDER BY position ASC, symbol ASC;
            """,
            (watchlist_id,),
        )
        return tuple(row["symbol"] for row in cur.fetchall())

    def create_watchlist(self, *, watchlist_id: str, name: str, symbols: List[str]) -> Watchlist:
        normalized_symbols = self._validate_payload(
            watchlist_id=watchlist_id,
            name=name,
            symbols=symbols,
        )
        with self._connection() as conn:
            try:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO watchlists (watchlist_id, name)
                    VALUES (?, ?);
                    """,
                    (watchlist_id, name),
                )
                cur.executemany(
                    """
                    INSERT INTO watchlist_symbols (watchlist_id, position, symbol)
                    VALUES (?, ?, ?);
                    """,
                    [
                        (watchlist_id, position, symbol)
                        for position, symbol in enumerate(normalized_symbols)
                    ],
                )
                conn.commit()
            except sqlite3.IntegrityError as exc:
                conn.rollback()
                raise ValueError("watchlist_id, name, and symbols must be unique within a watchlist") from exc
            except Exception:
                conn.rollback()
                raise

        result = self.get_watchlist(watchlist_id)
        if result is None:
            raise RuntimeError("created watchlist could not be reloaded")
        return result

    def get_watchlist(self, watchlist_id: str) -> Optional[Watchlist]:
        with self._connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT watchlist_id, name
                FROM watchlists
                WHERE watchlist_id = ?
                LIMIT 1;
                """,
                (watchlist_id,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return self._build_watchlist(row, symbols=self._get_symbols(conn, watchlist_id))

    def list_watchlists(self) -> List[Watchlist]:
        with self._connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT watchlist_id, name
                FROM watchlists
                ORDER BY name ASC, watchlist_id ASC;
                """
            )
            rows = cur.fetchall()
            return [
                self._build_watchlist(row, symbols=self._get_symbols(conn, row["watchlist_id"]))
                for row in rows
            ]

    def update_watchlist(self, *, watchlist_id: str, name: str, symbols: List[str]) -> Watchlist:
        normalized_symbols = self._validate_payload(
            watchlist_id=watchlist_id,
            name=name,
            symbols=symbols,
        )
        with self._connection() as conn:
            try:
                cur = conn.cursor()
                cur.execute(
                    """
                    UPDATE watchlists
                    SET name = ?
                    WHERE watchlist_id = ?;
                    """,
                    (name, watchlist_id),
                )
                if cur.rowcount == 0:
                    conn.rollback()
                    raise KeyError(f"watchlist not found: {watchlist_id}")
                cur.execute(
                    """
                    DELETE FROM watchlist_symbols
                    WHERE watchlist_id = ?;
                    """,
                    (watchlist_id,),
                )
                cur.executemany(
                    """
                    INSERT INTO watchlist_symbols (watchlist_id, position, symbol)
                    VALUES (?, ?, ?);
                    """,
                    [
                        (watchlist_id, position, symbol)
                        for position, symbol in enumerate(normalized_symbols)
                    ],
                )
                conn.commit()
            except sqlite3.IntegrityError as exc:
                conn.rollback()
                raise ValueError("watchlist name and symbols must remain unique") from exc
            except Exception:
                conn.rollback()
                raise

        result = self.get_watchlist(watchlist_id)
        if result is None:
            raise RuntimeError("updated watchlist could not be reloaded")
        return result

    def delete_watchlist(self, watchlist_id: str) -> bool:
        with self._connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                DELETE FROM watchlists
                WHERE watchlist_id = ?;
                """,
                (watchlist_id,),
            )
            conn.commit()
            return cur.rowcount > 0
