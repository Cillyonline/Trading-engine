"""
Create a deterministic demo snapshot in the local SQLite DB (cilly_trading.db).

This is meant for MVP exploration:
- Creates one ingestion_run in `ingestion_runs`
- Inserts OHLCV rows into `ohlcv_snapshots` for a small watchlist
- Data is deterministic (same inputs -> same generated series shape),
  but each symbol gets a small stable variation.

Run (PowerShell / VS Code terminal):
  python scripts/create_demo_snapshot.py
"""

import json
import math
import sqlite3
from datetime import datetime, timedelta, timezone
from uuid import uuid4


# === CONFIG ===
DB = "cilly_trading.db"
SYMBOLS = ["AAPL", "MSFT", "NVDA", "META", "TSLA"]
TIMEFRAME = "D1"
SOURCE = "demo_seed"
BARS = 260  # enough for MVP lookbacks


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def main() -> None:
    conn = _connect(DB)
    cur = conn.cursor()

    ingestion_run_id = str(uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    # Create ingestion run row
    cur.execute(
        """
        INSERT INTO ingestion_runs (
            ingestion_run_id,
            created_at,
            source,
            symbols_json,
            timeframe,
            fingerprint_hash
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            ingestion_run_id,
            created_at,
            SOURCE,
            json.dumps(SYMBOLS),
            TIMEFRAME,
            None,
        ),
    )

    # Create deterministic OHLCV rows
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    rows = []

    for symbol in SYMBOLS:
        # stable-ish variation per symbol (only used for demo seeding)
        base = 100.0 + (hash(symbol) % 20)

        for i in range(BARS):
            dt = start + timedelta(days=i)
            ts_ms = int(dt.timestamp() * 1000)

            close = base + 2.5 * math.sin(i / 8.0) + (i * 0.03)
            open_ = close + 0.2 * math.sin(i / 3.0)
            high = max(open_, close) + 0.6
            low = min(open_, close) - 0.6
            volume = 1_000_000 + (i * 1000)

            rows.append(
                (
                    ingestion_run_id,
                    symbol,
                    TIMEFRAME,
                    ts_ms,
                    float(open_),
                    float(high),
                    float(low),
                    float(close),
                    float(volume),
                )
            )

    cur.executemany(
        """
        INSERT INTO ohlcv_snapshots (
            ingestion_run_id,
            symbol,
            timeframe,
            ts,
            open,
            high,
            low,
            close,
            volume
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )

    conn.commit()

    print("✅ Demo Snapshot created")
    print("ingestion_run_id =", ingestion_run_id)
    print("symbols =", SYMBOLS)
    print("ohlcv_snapshots rows =", len(rows))

    conn.close()


if __name__ == "__main__":
    main()
