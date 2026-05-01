"""
Init-Skript fuer die SQLite-Datenbank der Cilly Trading Engine.

- Legt die Datei `cilly_trading.db` im Projektverzeichnis an (falls nicht vorhanden).
- Erzeugt die Tabellen `signals`, `trades`, `analysis_runs` und `watchlists`
  entsprechend der MVP-Spezifikation.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Optional

DEFAULT_DB_PATH_ENV_VAR = "CILLY_DB_PATH"


def resolve_default_db_path() -> Path:
    """Resolve the canonical runtime DB path from the bounded process environment."""

    configured_path = os.getenv(DEFAULT_DB_PATH_ENV_VAR)
    if configured_path:
        return Path(configured_path).expanduser()
    return Path("cilly_trading.db")


# Standard-Pfad fuer die Datenbankdatei (kann spaeter per ENV konfiguriert werden)
DEFAULT_DB_PATH = resolve_default_db_path()


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """
    Erzeugt eine SQLite-Connection.

    :param db_path: Optionaler Pfad zur DB-Datei. Wenn None, wird DEFAULT_DB_PATH verwendet.
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    # ensure parent dir exists (falls spaeter in Unterordnern gespeichert wird)
    if db_path.parent and not db_path.parent.exists():
        db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    # bessere Row-Funktionalitaet: Zugriff per Spaltenname moeglich
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[Path] = None) -> None:
    """
    Initialisiert die SQLite-Datenbank:
    - erzeugt Datei (falls nicht vorhanden)
    - legt Tabellen an (wenn sie noch nicht existieren)
    """
    conn = get_connection(db_path)
    cur = conn.cursor()

    # Tabelle: signals
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT,
            analysis_run_id TEXT,
            ingestion_run_id TEXT,
            symbol TEXT NOT NULL,
            strategy TEXT NOT NULL,
            direction TEXT NOT NULL,
            score REAL NOT NULL,
            timestamp TEXT NOT NULL,
            stage TEXT NOT NULL,              -- "setup" oder "entry_confirmed"
            entry_zone_from REAL,
            entry_zone_to REAL,
            confirmation_rule TEXT,
            timeframe TEXT NOT NULL,          -- z. B. "D1"
            market_type TEXT NOT NULL,        -- "stock" | "crypto"
            data_source TEXT NOT NULL,        -- "yahoo" | "binance"
            reasons_json TEXT
        );
        """
    )
    cur.execute("PRAGMA table_info(signals);")
    signal_columns = {row["name"] for row in cur.fetchall()}
    if "signal_id" not in signal_columns:
        cur.execute("ALTER TABLE signals ADD COLUMN signal_id TEXT;")
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_signals_timestamp
          ON signals(timestamp);
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_signals_symbol_timestamp
          ON signals(symbol, timestamp);
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_signals_strategy_timestamp
          ON signals(strategy, timestamp);
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_signals_symbol_strategy_timestamp
          ON signals(symbol, strategy, timestamp);
        """
    )
    cur.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_signals_analysis_run_signal_id_unique
          ON signals(analysis_run_id, signal_id)
          WHERE analysis_run_id IS NOT NULL AND signal_id IS NOT NULL;
        """
    )
    # Tabelle: trades
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT,
            symbol TEXT NOT NULL,
            strategy TEXT NOT NULL,
            stage TEXT NOT NULL,              -- "setup" oder "entry_confirmed"
            entry_price REAL,
            entry_date TEXT,
            exit_price REAL,
            exit_date TEXT,
            reason_entry TEXT NOT NULL,
            reason_exit TEXT,
            notes TEXT,
            timeframe TEXT NOT NULL,
            market_type TEXT NOT NULL,
            data_source TEXT NOT NULL
        );
        """
    )
    cur.execute("PRAGMA table_info(trades);")
    trade_columns = {row["name"] for row in cur.fetchall()}
    if "signal_id" not in trade_columns:
        cur.execute("ALTER TABLE trades ADD COLUMN signal_id TEXT;")
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_trades_signal_id
          ON trades(signal_id)
          WHERE signal_id IS NOT NULL;
        """
    )

    # Tabelle: analysis_runs
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS analysis_runs (
            analysis_run_id TEXT PRIMARY KEY,
            ingestion_run_id TEXT NOT NULL,
            request_payload TEXT NOT NULL,
            result_payload TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_analysis_runs_ingestion
          ON analysis_runs(ingestion_run_id);
        """
    )

    # Tabelle: ingestion_runs
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ingestion_runs (
            ingestion_run_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            source TEXT NOT NULL,
            symbols_json TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            fingerprint_hash TEXT NULL
        );
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_ingestion_runs_created_at
          ON ingestion_runs(created_at);
        """
    )

    # Tabelle: ohlcv_snapshots
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ohlcv_snapshots (
            ingestion_run_id TEXT NOT NULL,
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            ts INTEGER NOT NULL,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            volume REAL NOT NULL,
            PRIMARY KEY (ingestion_run_id, symbol, timeframe, ts),
            FOREIGN KEY (ingestion_run_id) REFERENCES ingestion_runs(ingestion_run_id)
        );
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_ohlcv_snapshots_lookup
          ON ohlcv_snapshots(ingestion_run_id, symbol, timeframe, ts);
        """
    )
    cur.execute(
        """
        CREATE TRIGGER IF NOT EXISTS trg_ohlcv_snapshots_no_update
        BEFORE UPDATE ON ohlcv_snapshots
        BEGIN
            SELECT RAISE(ABORT, 'snapshot_immutable');
        END;
        """
    )
    cur.execute(
        """
        CREATE TRIGGER IF NOT EXISTS trg_ohlcv_snapshots_no_delete
        BEFORE DELETE ON ohlcv_snapshots
        BEGIN
            SELECT RAISE(ABORT, 'snapshot_immutable');
        END;
        """
    )

    # Tabelle: watchlists
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS watchlists (
            watchlist_id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        );
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_watchlists_name
          ON watchlists(name, watchlist_id);
        """
    )

    # Tabelle: watchlist_symbols
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS watchlist_symbols (
            watchlist_id TEXT NOT NULL,
            position INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            PRIMARY KEY (watchlist_id, position),
            FOREIGN KEY (watchlist_id) REFERENCES watchlists(watchlist_id) ON DELETE CASCADE
        );
        """
    )
    cur.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_watchlist_symbols_unique_membership
          ON watchlist_symbols(watchlist_id, symbol);
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_watchlist_symbols_lookup
          ON watchlist_symbols(watchlist_id, position, symbol);
        """
    )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    # Fuer lokalen Aufruf:
    # python -m src.cilly_trading.db.init_db
    init_db()
    print(f"SQLite-Datenbank initialisiert unter: {DEFAULT_DB_PATH.resolve()}")
