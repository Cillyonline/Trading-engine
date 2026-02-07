# Local Development: Run & Analyze

## TL;DR Quick Start (fresh local setup)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=src uvicorn api.main:app --reload
```

In a second terminal:

```bash
curl http://127.0.0.1:8000/health
```

Expected output:

```json
{"status":"ok"}
```

## Prerequisites

- Python 3.10+
- `pip`

## Canonical startup path

The canonical local startup path is:

```bash
PYTHONPATH=src uvicorn api.main:app --reload
```

Run it from the repository root after venv activation and dependency install.

## Secondary / utility entrypoints (not canonical)

- `PYTHONPATH=src python -m api.main` (starts same FastAPI app via module `__main__` block)
- `docker compose up --build` (containerized local run)
- `PYTHONPATH=src python -m cilly_trading.engine.deterministic_run --fixtures-dir fixtures/deterministic-analysis --output tests/output/deterministic-analysis.json` (deterministic offline utility run)

There is no installed top-level project CLI command (for example `cilly-trading ...`).

## Step-by-step (fresh clone → analysis request → persisted signals)

1) **Create and activate a virtual environment**

```bash
python -m venv .venv
source .venv/bin/activate
```

2) **Install dependencies**

```bash
pip install -r requirements.txt
```

3) **Start the API (terminal A)**

```bash
PYTHONPATH=src uvicorn api.main:app --reload
```

4) **Verify API health (terminal B)**

```bash
curl http://127.0.0.1:8000/health
```

Expected output:

```json
{"status":"ok"}
```

5) **Create a demo snapshot and capture `ingestion_run_id` (terminal B)**

```bash
SNAPSHOT_ID=$(python scripts/create_demo_snapshot.py | awk -F'= ' '/ingestion_run_id/{print $2}')
echo "$SNAPSHOT_ID"
```

Expected behavior:
- command prints a UUID value
- this value is required by snapshot-only analysis endpoints

6) **Trigger strategy analysis using the created snapshot (terminal B)**

```bash
curl -X POST "http://127.0.0.1:8000/strategy/analyze" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d "{
    \"ingestion_run_id\": \"$SNAPSHOT_ID\",
    \"symbol\": \"AAPL\",
    \"strategy\": \"RSI2\",
    \"market_type\": \"stock\",
    \"lookback_days\": 200
  }"
```

Expected output shape:

```json
{
  "symbol": "AAPL",
  "strategy": "RSI2",
  "signals": []
}
```

(`signals` may be empty or contain one/more signal objects depending on snapshot data.)

7) **Verify persisted signals (terminal B)**

```bash
curl -X GET "http://127.0.0.1:8000/signals?strategy=RSI2&ingestion_run_id=$SNAPSHOT_ID&limit=10" \
  -H "Accept: application/json"
```

Expected output shape:

```json
{
  "items": [],
  "limit": 10,
  "offset": 0,
  "total": 0
}
```

## Stop / Reset

### Stop API
In terminal A (where `uvicorn` runs), press `Ctrl+C` once.

Optional verification:

```bash
curl --fail http://127.0.0.1:8000/health
```

This returns non-zero after successful stop.

### Reset local DB (non-Docker)

```bash
rm -f cilly_trading.db
```

Then restart API with the canonical startup command.

### Reset local DB (Docker)

```bash
docker compose down -v
```

Safety note: reset deletes local signals, analysis runs, ingestion runs, and snapshot rows.

## Common setup errors & fixes

1) **Missing snapshot reference (422)**
- Symptom: `{"detail":"ingestion_run_not_found"}` or `{"detail":"ingestion_run_not_ready"}`
- Fix: run `python scripts/create_demo_snapshot.py`, capture `ingestion_run_id`, and reuse it in the request.

2) **Unknown strategy (400)**
- Symptom: `{"detail":"Unknown strategy: <strategy>"}`
- Fix: use supported strategies: `RSI2` or `TURTLE`.

3) **Missing required field (422)**
- Symptom: `422 Unprocessable Entity` with missing field details.
- Fix: provide required request fields, including `ingestion_run_id` for snapshot-only analysis endpoints.

4) **invalid_ingestion_run_id (422)**
- Symptom: `{"detail":"invalid_ingestion_run_id"}`
- Fix: provide a valid UUIDv4 string.

## Run tests (optional)

```bash
python -m pytest
```

See `docs/testing.md` for the canonical test setup and command.
