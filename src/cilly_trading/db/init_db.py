"""
Init-Skript für die SQLite-Datenbank der Cilly Trading Engine.

- Legt die Datei `cilly_trading.db` im Projektverzeichnis an (falls nicht vorhanden).
- Erzeugt die Tabellen `signals` und `trades` entsprechend der MVP-Spezifikation.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

# Standard-Pfad für die Datenbankdatei (kann später per ENV konfiguriert werden)
DEFAULT_DB_PATH = Path("cilly_trading.db")


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """
    Erzeugt eine SQLite-Connection.

    :param db_path: Optionaler Pfad zur DB-Datei. Wenn None, wird DEFAULT_DB_PATH verwendet.
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    # ensure parent dir exists (falls später in Unterordnern gespeichert wird)
    if db_path.parent and not db_path.parent.exists():
        db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    # bessere Row-Funktionalität: Zugriff per Spaltenname möglich
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[Path] = None) -> None:
    """
    Initialisiert die SQLite-Datenbank:
    - erzeugt Datei (falls nicht vorhanden)
    - legt Tabellen `signals` und `trades` an (wenn sie noch nicht existieren)
    """
    conn = get_connection(db_path)
    cur = conn.cursor()

    # Tabelle: signals
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            data_source TEXT NOT NULL         -- "yahoo" | "binance"
        );
        """
    )
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

    # Tabelle: trades
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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

    conn.commit()
    conn.close()


if __name__ == "__main__":
    # Für lokalen Aufruf:
    # python -m src.cilly_trading.db.init_db
    init_db()
    print(f"SQLite-Datenbank initialisiert unter: {DEFAULT_DB_PATH.resolve()}")
