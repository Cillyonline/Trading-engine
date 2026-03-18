# API Usage Examples

Examples-first guide for using the API locally. This document shows how to call the current endpoints and points to the authoritative contract when operator-triggered analysis is involved.

## Quick Start

- Base URL: `http://localhost:8000`
- Authentication: none
- Common headers:
  - `Content-Type: application/json`
  - `Accept: application/json`
- Authoritative operator analysis contract: `docs/operations/api/usage_contract.md` section `Canonical Operator Analysis Contract`

## Snapshot-only behavior

All analysis endpoints are snapshot-only. They never fetch live market data. Every analysis request must reference a valid `ingestion_run_id` that already exists in the local SQLite database (`cilly_trading.db`) and contains snapshot rows for the requested symbol and timeframe.

## Prerequisites

- Python 3.12+
- A demo snapshot in `cilly_trading.db` seeded with an example ingestion run ID
- `sqlite3` CLI available to inspect snapshot data

## Step 1 - Start the API locally

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .[test]
$env:PYTHONPATH = "src"
uvicorn api.main:app --reload
```

## Step 2 - Identify a valid snapshot ID

Use the queries below to find an existing ingestion run ID and confirm it has snapshot rows for the symbol and timeframe (`D1`) used later in the request.

```bash
sqlite3 cilly_trading.db "SELECT ingestion_run_id, timeframe, created_at FROM ingestion_runs ORDER BY created_at DESC LIMIT 5;"
```

```bash
sqlite3 cilly_trading.db "SELECT symbol, timeframe, COUNT(*) FROM ohlcv_snapshots WHERE ingestion_run_id='<EXAMPLE_INGESTION_RUN_ID>' GROUP BY symbol, timeframe;"
```

## Step 3 - Run the canonical operator-triggered analysis request

Authoritative route: `POST /analysis/run`

```bash
curl -X POST "http://127.0.0.1:8000/analysis/run" \
  -H "Content-Type: application/json" \
  -d '{
    "ingestion_run_id": "<EXAMPLE_INGESTION_RUN_ID>",
    "symbol": "AAPL",
    "strategy": "RSI2",
    "market_type": "stock",
    "lookback_days": 200
  }'
```

Response example:

```json
{
  "analysis_run_id": "e1f2d3c4-1111-2222-3333-444455556666",
  "ingestion_run_id": "<EXAMPLE_INGESTION_RUN_ID>",
  "symbol": "AAPL",
  "strategy": "RSI2",
  "signals": []
}
```

How to interpret the response:

- `analysis_run_id` is the server-computed deterministic run identifier.
- `signals` is an array of zero or more signal objects.
- `signals: []` means the request succeeded but no signal was produced for that snapshot.

## Common Usage Scenarios

### Scenario 1: Operator-triggered analysis for one symbol

This is the workflow governed by issue `#600`. The payload shape shown here is the same shape documented in `docs/operations/api/usage_contract.md`.

**curl**

```bash
curl -X POST "http://localhost:8000/analysis/run" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "ingestion_run_id": "<EXAMPLE_INGESTION_RUN_ID>",
    "symbol": "AAPL",
    "strategy": "RSI2",
    "market_type": "stock",
    "lookback_days": 200,
    "strategy_config": {
      "oversold_threshold": 10.0
    }
  }'
```

**httpie**

```bash
http POST http://localhost:8000/analysis/run \
  Content-Type:application/json \
  Accept:application/json \
  ingestion_run_id="<EXAMPLE_INGESTION_RUN_ID>" \
  symbol="AAPL" \
  strategy="RSI2" \
  market_type="stock" \
  lookback_days:=200 \
  strategy_config:='{"oversold_threshold":10.0}'
```

**Postman (raw)**

```http
POST http://localhost:8000/analysis/run
Content-Type: application/json
Accept: application/json

{
  "ingestion_run_id": "<EXAMPLE_INGESTION_RUN_ID>",
  "symbol": "AAPL",
  "strategy": "RSI2",
  "market_type": "stock",
  "lookback_days": 200,
  "strategy_config": {
    "oversold_threshold": 10.0
  }
}
```

**Expected status:** `200 OK`

**Sample response**

```json
{
  "analysis_run_id": "e1f2d3c4-1111-2222-3333-444455556666",
  "ingestion_run_id": "<EXAMPLE_INGESTION_RUN_ID>",
  "symbol": "AAPL",
  "strategy": "RSI2",
  "signals": [
    {
      "symbol": "AAPL",
      "strategy": "RSI2",
      "direction": "long",
      "score": 42.5,
      "timestamp": "2024-01-15T09:30:00Z",
      "stage": "setup",
      "entry_zone": {
        "from_": 178.5,
        "to": 182.0
      },
      "confirmation_rule": "RSI below 10",
      "timeframe": "D1",
      "market_type": "stock",
      "data_source": "yahoo"
    }
  ]
}
```

### Scenario 2: Run a strategy analysis for one symbol

`POST /strategy/analyze` remains available, but it is not the authoritative operator contract.

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

### Scenario 3: Run the basic screener with the default watchlist

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

### Scenario 4: Read recent signals with filters

```bash
curl -X GET "http://localhost:8000/signals?symbol=AAPL&strategy=RSI2&limit=10" \
  -H "Accept: application/json"
```

## Error Examples

### Error 1: 400 Unknown strategy

```bash
curl -X POST "http://localhost:8000/analysis/run" \
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

Expected status: `400 Bad Request`

Sample response:

```json
{
  "detail": "Unknown strategy: UNKNOWN"
}
```

### Error 2: 404 Unknown route

```bash
curl -X GET "http://localhost:8000/unknown/resource" \
  -H "Accept: application/json"
```

Expected status: `404 Not Found`

Sample response:

```json
{
  "detail": "Not Found"
}
```

### Error 3: 422 Missing required field

```bash
curl -X POST "http://localhost:8000/analysis/run" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "ingestion_run_id": "<EXAMPLE_INGESTION_RUN_ID>",
    "strategy": "RSI2",
    "market_type": "stock",
    "lookback_days": 200
  }'
```

Expected status: `422 Unprocessable Entity`

Sample response:

```json
{
  "detail": [
    {
      "loc": ["body", "symbol"],
      "msg": "Field required",
      "type": "missing"
    }
  ]
}
```
