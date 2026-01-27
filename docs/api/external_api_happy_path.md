# External API Usage (Happy Path)

This guide shows **one complete snapshot-only analysis request** from local startup to a valid response. It is intentionally limited to a single request/response pair so a new external user can follow it without guessing.

## Snapshot-only behavior (must know)

All API analysis endpoints are **snapshot-only**. They **never** fetch live market data. The request below uses a concrete `ingestion_run_id` that already exists in the local SQLite database (`cilly_trading.db`) and contains snapshot rows for the symbol/timeframe used in the request.

## Prerequisites

- Python 3.10+
- A demo snapshot in `cilly_trading.db` seeded with `ingestion_run_id` `11111111-1111-4111-8111-111111111111` (this repo does **not** create snapshots)
- `sqlite3` CLI available (for verifying the snapshot ID)

## Step 1 — Start the API locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=src uvicorn api.main:app --reload
```

## Step 2 — Identify a valid snapshot ID

Use the concrete `ingestion_run_id` shown below from the seeded demo database. The queries confirm it exists and has snapshot rows for the symbol/timeframe (`D1`) used later in the request.

```bash
sqlite3 cilly_trading.db "SELECT ingestion_run_id, timeframe, created_at FROM ingestion_runs ORDER BY created_at DESC LIMIT 5;"
```

```bash
sqlite3 cilly_trading.db "SELECT symbol, timeframe, COUNT(*) FROM ohlcv_snapshots WHERE ingestion_run_id='11111111-1111-4111-8111-111111111111' GROUP BY symbol, timeframe;"
```

## Step 3 — Run exactly one snapshot-based analysis request

**Request:** `POST /strategy/analyze` (single symbol, single strategy)

```bash
curl -X POST "http://127.0.0.1:8000/strategy/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "ingestion_run_id": "11111111-1111-4111-8111-111111111111",
    "symbol": "AAPL",
    "strategy": "RSI2",
    "market_type": "stock",
    "lookback_days": 200
  }'
```

**Response (example shape):**

```json
{
  "symbol": "AAPL",
  "strategy": "RSI2",
  "signals": []
}
```

### How to interpret the response

- `signals` is an array of zero or more signal objects for the strategy run. An empty array means “no signal” for the snapshot you referenced.
