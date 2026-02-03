# API Usage Examples

Examples-first guide for using the API locally. This document consolidates the cookbook scenarios and the external happy-path walkthrough. It documents current behavior only.

## Quick Start
- Base URL: `http://localhost:8000`
- Authentication: none
- Common headers:
  - `Content-Type: application/json`
  - `Accept: application/json`

## Snapshot-only behavior (must know)

All API analysis endpoints are **snapshot-only**. They **never** fetch live market data. Every analysis request must reference a valid `ingestion_run_id` that already exists in the local SQLite database (`cilly_trading.db`) and contains snapshot rows for the symbol/timeframe used in the request.

## Prerequisites

- Python 3.10+
- A demo snapshot in `cilly_trading.db` seeded with an example ingestion run ID (this repo does **not** create snapshots)
- `sqlite3` CLI available (for verifying the snapshot ID)

## Step 1 — Start the API locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=src uvicorn api.main:app --reload
```

## Step 2 — Identify a valid snapshot ID

Use the queries below to locate an existing ingestion run ID and confirm it has snapshot rows for the symbol/timeframe (`D1`) used later in the request.

```bash
sqlite3 cilly_trading.db "SELECT ingestion_run_id, timeframe, created_at FROM ingestion_runs ORDER BY created_at DESC LIMIT 5;"
```

```bash
sqlite3 cilly_trading.db "SELECT symbol, timeframe, COUNT(*) FROM ohlcv_snapshots WHERE ingestion_run_id='<EXAMPLE_INGESTION_RUN_ID>' GROUP BY symbol, timeframe;"
```

## Step 3 — Run exactly one snapshot-based analysis request

**Request:** `POST /strategy/analyze` (single symbol, single strategy)

```bash
curl -X POST "http://127.0.0.1:8000/strategy/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "ingestion_run_id": "<EXAMPLE_INGESTION_RUN_ID>",
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

---

## Common Usage Scenarios

### Scenario 1: Run a strategy analysis for one symbol
**curl**
```bash
curl -X POST "http://localhost:8000/strategy/analyze" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "ingestion_run_id": "<EXAMPLE_INGESTION_RUN_ID>",
    "symbol": "AAPL",
    "strategy": "RSI2",
    "market_type": "stock",
    "lookback_days": 200
  }'
```

**httpie**
```bash
http POST http://localhost:8000/strategy/analyze \
  Content-Type:application/json \
  Accept:application/json \
  ingestion_run_id="<EXAMPLE_INGESTION_RUN_ID>" \
  symbol="AAPL" \
  strategy="RSI2" \
  market_type="stock" \
  lookback_days:=200
```

**Postman (raw)**
```
POST http://localhost:8000/strategy/analyze
Content-Type: application/json
Accept: application/json

{
  "ingestion_run_id": "<EXAMPLE_INGESTION_RUN_ID>",
  "symbol": "AAPL",
  "strategy": "RSI2",
  "market_type": "stock",
  "lookback_days": 200
}
```

**Expected status:** `200 OK`

**Sample response**
```json
{ "detail": "Response schema depends on API models. See /docs for exact structure." }
```

### Scenario 2: Run the basic screener with default watchlist
**curl**
```bash
curl -X POST "http://localhost:8000/screener/basic" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "ingestion_run_id": "<EXAMPLE_INGESTION_RUN_ID>",
    "market_type": "stock",
    "lookback_days": 200,
    "min_score": 30
  }'
```

**httpie**
```bash
http POST http://localhost:8000/screener/basic \
  Content-Type:application/json \
  Accept:application/json \
  ingestion_run_id="<EXAMPLE_INGESTION_RUN_ID>" \
  market_type="stock" \
  lookback_days:=200 \
  min_score:=30
```

**Postman (raw)**
```
POST http://localhost:8000/screener/basic
Content-Type: application/json
Accept: application/json

{
  "ingestion_run_id": "<EXAMPLE_INGESTION_RUN_ID>",
  "market_type": "stock",
  "lookback_days": 200,
  "min_score": 30
}
```

**Expected status:** `200 OK`

**Sample response**
```json
{ "detail": "Response schema depends on API models. See /docs for exact structure." }
```

### Scenario 3: Read recent signals with filters
**curl**
```bash
curl -X GET "http://localhost:8000/signals?symbol=AAPL&strategy=RSI2&limit=10" \
  -H "Accept: application/json"
```

**httpie**
```bash
http GET http://localhost:8000/signals \
  symbol=="AAPL" \
  strategy=="RSI2" \
  limit==10 \
  Accept:application/json
```

**Postman (raw)**
```
GET http://localhost:8000/signals?symbol=AAPL&strategy=RSI2&limit=10
Accept: application/json
```

**Expected status:** `200 OK`

**Sample response**
```json
{ "detail": "Response schema depends on API models. See /docs for exact structure." }
```

## Error Examples

### Error 1: 400 Invalid strategy
**curl**
```bash
curl -X POST "http://localhost:8000/strategy/analyze" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "ingestion_run_id": "<EXAMPLE_INGESTION_RUN_ID>",
    "symbol": "AAPL",
    "strategy": "UNKNOWN",
    "market_type": "stock",
    "lookback_days": 200
  }'
```

**httpie**
```bash
http POST http://localhost:8000/strategy/analyze \
  Content-Type:application/json \
  Accept:application/json \
  ingestion_run_id="<EXAMPLE_INGESTION_RUN_ID>" \
  symbol="AAPL" \
  strategy="UNKNOWN" \
  market_type="stock" \
  lookback_days:=200
```

**Postman (raw)**
```
POST http://localhost:8000/strategy/analyze
Content-Type: application/json
Accept: application/json

{
  "ingestion_run_id": "<EXAMPLE_INGESTION_RUN_ID>",
  "symbol": "AAPL",
  "strategy": "UNKNOWN",
  "market_type": "stock",
  "lookback_days": 200
}
```

**Expected status:** `400 Bad Request`

**Sample response**
```json
{ "detail": "Response schema depends on API models. See /docs for exact structure." }
```

### Error 2: 404 Not found (unknown route)
**curl**
```bash
curl -X GET "http://localhost:8000/unknown/resource" \
  -H "Accept: application/json"
```

**httpie**
```bash
http GET http://localhost:8000/unknown/resource \
  Accept:application/json
```

**Postman (raw)**
```
GET http://localhost:8000/unknown/resource
Accept: application/json
```

**Expected status:** `404 Not Found`

**Sample response**
```json
{
  "detail": "Not Found"
}
```

### Error 3: 422 Missing required field
**curl**
```bash
curl -X POST "http://localhost:8000/strategy/analyze" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "ingestion_run_id": "<EXAMPLE_INGESTION_RUN_ID>",
    "strategy": "RSI2",
    "market_type": "stock",
    "lookback_days": 200
  }'
```

**httpie**
```bash
http POST http://localhost:8000/strategy/analyze \
  Content-Type:application/json \
  Accept:application/json \
  ingestion_run_id="<EXAMPLE_INGESTION_RUN_ID>" \
  strategy="RSI2" \
  market_type="stock" \
  lookback_days:=200
```

**Postman (raw)**
```
POST http://localhost:8000/strategy/analyze
Content-Type: application/json
Accept: application/json

{
  "ingestion_run_id": "<EXAMPLE_INGESTION_RUN_ID>",
  "strategy": "RSI2",
  "market_type": "stock",
  "lookback_days": 200
}
```

**Expected status:** `422 Unprocessable Entity`

**Sample response**
```json
{
  "detail": [
    {
      "loc": ["body", "symbol"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```
