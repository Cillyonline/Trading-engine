# Local Development: Run & Analyze

## TL;DR Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=src uvicorn api.main:app --reload
```

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

## Step-by-step (fresh clone → signals stored)

1) **Create and activate a virtual environment**

```bash
python -m venv .venv
source .venv/bin/activate
```

2) **Install dependencies**

```bash
pip install -r requirements.txt
```

3) **Run the API**

No CLI entrypoint yet; use API endpoints.

```bash
PYTHONPATH=src uvicorn api.main:app --reload
```

The code uses a `src/` layout; `PYTHONPATH=src` makes `cilly_trading` importable.

4) **Verify the API is up**

```bash
curl http://127.0.0.1:8000/health
```

Expected output:

```json
{"status":"ok"}
```

5) **Trigger signal generation**

Supported strategies: `RSI2`, `TURTLE`.

```bash
curl -X POST "http://127.0.0.1:8000/strategy/analyze" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "symbol": "AAPL",
    "strategy": "RSI2",
    "market_type": "stock",
    "lookback_days": 200
  }'
```

Expected output (example):

```json
{
  "symbol": "AAPL",
  "strategy": "RSI2",
  "signals": []
}
```

6) **Verify signals were stored**

```bash
curl -X GET "http://127.0.0.1:8000/signals?strategy=RSI2&limit=10" \
  -H "Accept: application/json"
```

Expected output (example):

```json
{
  "items": [],
  "limit": 10,
  "offset": 0,
  "total": 0
}
```

## Run the API with Docker (alternative)

```bash
docker compose up --build
```

```bash
curl http://127.0.0.1:8000/health
```

Expected output:

```json
{"status":"ok"}
```

## Results: where data is stored and how to read it

- SQLite file: `cilly_trading.db` (project root)
- Key tables: `signals`, `analysis_runs`

Read results via API:

```bash
curl -X GET "http://127.0.0.1:8000/signals?strategy=RSI2&limit=10" \
  -H "Accept: application/json"
```

## Reset local state (SQLite)

**Docker:**

```bash
docker compose down -v
```

**Non-Docker (local venv run):**

1) Stop `uvicorn`
2) Delete the SQLite file in the project root:
   - `cilly_trading.db`
3) Restart `uvicorn` (DB re-initializes on startup)

Safety note: this deletes all local signals and analysis runs.

## Common setup errors & fixes

1) **No CLI entrypoint**
   - Symptom: Looking for a `run` or `engine` command.
   - Fix: Run the API with `uvicorn api.main:app --reload` and use the HTTP endpoints.

2) **Unknown strategy (400)**
   - Symptom: `{"detail":"Unknown strategy: <strategy>"}`
   - Fix: Use supported strategies: `RSI2` or `TURTLE`.

3) **Missing required field (422)**
   - Symptom: `422 Unprocessable Entity` with missing field details (e.g., missing `symbol`).
   - Fix: Provide all required fields for `/strategy/analyze` and `/analysis/run`.

4) **invalid_ingestion_run_id (422)**
   - Symptom: `{"detail":"invalid_ingestion_run_id"}`
   - Fix: When using `ingestion_run_id`, provide a valid UUIDv4 string.

5) **ingestion_run_not_found (422)**
   - Symptom: `{"detail":"ingestion_run_not_found"}`
   - Fix: Use an existing ingestion run ID or omit `ingestion_run_id` for endpoints where it is optional.

## Run tests (optional)

```bash
python -m pytest
```

See `docs/testing.md` for the canonical test setup and command.
