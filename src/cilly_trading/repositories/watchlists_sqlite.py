"""SQLite repository for deterministic watchlist persistence."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import List, Optional

from cilly_trading.db import DEFAULT_DB_PATH, init_db
from cilly_trading.repositories import Watchlist, WatchlistRepository


class SqliteWatchlistRepository(WatchlistRepository):
    """Persist named watchlists and ordered symbol membership in SQLite."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        if db_path is None:
            db_path = DEFAULT_DB_PATH

        self._db_path = Path(db_path)
        init_db(self._db_path)

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

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
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("BEGIN;")
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
        finally:
            conn.close()

        result = self.get_watchlist(watchlist_id)
        if result is None:
            raise RuntimeError("created watchlist could not be reloaded")
        return result

    def get_watchlist(self, watchlist_id: str) -> Optional[Watchlist]:
        conn = self._get_connection()
        try:
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
        finally:
            conn.close()

    def list_watchlists(self) -> List[Watchlist]:
        conn = self._get_connection()
        try:
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
        finally:
            conn.close()

    def update_watchlist(self, *, watchlist_id: str, name: str, symbols: List[str]) -> Watchlist:
        normalized_symbols = self._validate_payload(
            watchlist_id=watchlist_id,
            name=name,
            symbols=symbols,
        )
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("BEGIN;")
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
        finally:
            conn.close()

        result = self.get_watchlist(watchlist_id)
        if result is None:
            raise RuntimeError("updated watchlist could not be reloaded")
        return result

    def delete_watchlist(self, watchlist_id: str) -> bool:
        conn = self._get_connection()
        try:
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
        finally:
            conn.close()
