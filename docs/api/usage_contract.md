# API Usage Contract (MVP v1.1)

This document defines the stable usage contract for the MVP v1 API. It documents the currently implemented behavior without changing runtime logic.

## Base URL

- Local development: `http://localhost:8000`

## Common Conventions

### Supported strategies

- `RSI2`
- `TURTLE`

### Market types

- `stock`
- `crypto`

### Error formats

The API returns two error shapes depending on the failure mode:

1. **Validation errors (FastAPI/Pydantic)**

   - **Status:** `422 Unprocessable Entity`
   - **Body:**
     ```json
     {
       "detail": [
         {
           "loc": ["body", "field_name"],
           "msg": "field required",
           "type": "value_error.missing"
         }
       ]
     }
     ```

2. **Application errors (explicit `HTTPException`)**

   - **Body:**
     ```json
     {
       "detail": "error_code_or_message"
     }
     ```

Exact status codes are documented per endpoint in the Errors section.

### Ingestion run validation

Some endpoints accept `ingestion_run_id`. When provided, the API enforces:

- Must be a valid UUIDv4 string, otherwise `422` with `{"detail":"invalid_ingestion_run_id"}`.
- Must exist in the analysis run repository, otherwise `422` with `{"detail":"ingestion_run_not_found"}`.

---

## GET `/health`

**Purpose:** Health check for API availability.

**Request parameters:**

| Name | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| N/A | N/A | N/A | N/A | No request parameters. |

**Success response:**

- **Status:** `200 OK`
- **Body:**
  ```json
  {
    "status": "ok"
  }
  ```

**Empty/no-result behavior:** Not applicable.

**Validation rules:** None.

**Errors:**

| Status | Error body shape | Error detail | Trigger |
| --- | --- | --- | --- |
| None | None | None | No application-defined errors. |

**Example request:**

```bash
curl -s http://localhost:8000/health
```

**Example response:**

```json
{
  "status": "ok"
}
```

---

## GET `/signals`

**Purpose:** Read stored signals with pagination and optional filtering.

**Query parameters:**

| Name | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `symbol` | string | optional | none | Symbol filter (e.g., `AAPL`, `BTC/USDT`). |
| `strategy` | string | optional | none | Strategy filter (e.g., `RSI2`, `TURTLE`). |
| `preset` | string | optional | none | Preset filter (e.g., `D1`). |
| `from` | string (ISO-8601 datetime) | optional | none | Start time (inclusive) for `created_at`. |
| `to` | string (ISO-8601 datetime) | optional | none | End time (inclusive) for `created_at`. |
| `start` | string (ISO-8601 datetime) | optional | none | Alias for `from` (must not conflict). |
| `end` | string (ISO-8601 datetime) | optional | none | Alias for `to` (must not conflict). |
| `sort` | string | optional | `created_at_desc` | One of `created_at_asc`, `created_at_desc`. |
| `limit` | integer | optional | `50` | Range `1..500`. |
| `offset` | integer | optional | `0` | Must be `>= 0`. |

**Success response:**

- **Status:** `200 OK`
- **Body:**
  ```json
  {
    "items": [
      {
        "symbol": "AAPL",
        "strategy": "RSI2",
        "direction": "long",
        "score": 42.5,
        "created_at": "2024-01-15T09:30:00Z",
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
    ],
    "limit": 50,
    "offset": 0,
    "total": 128
  }
  ```

**Empty/no-result behavior:** Returns an empty `items` array with `total: 0` and the provided `limit/offset`.

**Validation rules:**

- `start` and `from` cannot both be present with different values.
- `end` and `to` cannot both be present with different values.
- Resolved `from` must be `<=` resolved `to`.
- `limit` must be within `1..500`.

**Errors:**

| Status | Error body shape | Error detail | Trigger |
| --- | --- | --- | --- |
| 422 | `{"detail":"start conflicts with from"}` | `start conflicts with from` | `start` and `from` provided with different values. |
| 422 | `{"detail":"end conflicts with to"}` | `end conflicts with to` | `end` and `to` provided with different values. |
| 422 | `{"detail":"from must be less than or equal to to"}` | `from must be less than or equal to to` | Resolved `from` is later than resolved `to`. |
| 422 | Pydantic validation list | varies | Invalid query parameter types or constraints (e.g., `limit` outside `1..500`). |

**Example request:**

```bash
curl -s "http://localhost:8000/signals?strategy=RSI2&limit=2&offset=0"
```

**Example response:**

```json
{
  "items": [],
  "limit": 2,
  "offset": 0,
  "total": 0
}
```

---

## GET `/screener/v2/results`

**Purpose:** Read screener results filtered by strategy and timeframe.

**Query parameters:**

| Name | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `strategy` | string | required | none | Strategy name. |
| `timeframe` | string | required | none | Timeframe filter (e.g., `D1`). |
| `min_score` | number | optional | none | Minimum score filter (`>= 0`). |

**Success response:**

- **Status:** `200 OK`
- **Body:**
  ```json
  {
    "items": [
      {
        "symbol": "NVDA",
        "score": 68.2,
        "strategy": "TURTLE",
        "timeframe": "D1",
        "market_type": "stock",
        "created_at": "2024-01-15T09:30:00Z"
      }
    ],
    "total": 1
  }
  ```

**Empty/no-result behavior:** Returns `items: []` and `total: 0`.

**Validation rules:**

- `strategy` and `timeframe` are required.
- `min_score` must be `>= 0` when provided.

**Errors:**

| Status | Error body shape | Error detail | Trigger |
| --- | --- | --- | --- |
| 422 | Pydantic validation list | varies | Missing or invalid query parameters (e.g., missing `strategy`). |

**Example request:**

```bash
curl -s "http://localhost:8000/screener/v2/results?strategy=TURTLE&timeframe=D1"
```

**Example response:**

```json
{
  "items": [],
  "total": 0
}
```

---

## POST `/strategy/analyze`

**Purpose:** Run a strategy analysis for a single symbol. Returns raw signal output for the requested symbol and strategy. When presets are provided, results are grouped by preset ID.

**Request body:**

| Name | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `ingestion_run_id` | string (UUIDv4) | optional | none | Snapshot reference ID. Validated if present. |
| `symbol` | string | required | none | Symbol (e.g., `AAPL`, `BTC/USDT`). |
| `strategy` | string | required | none | Strategy name (case-insensitive). |
| `market_type` | string | optional | `stock` | Must match `stock` or `crypto`. |
| `lookback_days` | integer | optional | `200` | Range `30..1000`. |
| `strategy_config` | object | optional | none | Strategy config overrides (ignored if `presets` supplied). |
| `presets` | array | optional | none | List of preset objects (must be unique by `id`). |

Preset object:

| Name | Type | Required | Notes |
| --- | --- | --- | --- |
| `id` | string | required | Stable preset identifier. |
| `params` | object | optional | Strategy config overrides for this preset. |

**Success response (no presets):**

- **Status:** `200 OK`
- **Body:**
  ```json
  {
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
        "entry_zone": {"from_": 178.5, "to": 182.0},
        "confirmation_rule": "RSI below 10",
        "timeframe": "D1",
        "market_type": "stock",
        "data_source": "yahoo"
      }
    ]
  }
  ```

**Success response (with presets):**

- **Status:** `200 OK`
- **Body:**
  ```json
  {
    "symbol": "AAPL",
    "strategy": "RSI2",
    "results_by_preset": {
      "default": [
        {
          "symbol": "AAPL",
          "strategy": "RSI2",
          "direction": "long",
          "score": 42.5,
          "timestamp": "2024-01-15T09:30:00Z",
          "stage": "setup",
          "entry_zone": {"from_": 178.5, "to": 182.0},
          "confirmation_rule": "RSI below 10",
          "timeframe": "D1",
          "market_type": "stock",
          "data_source": "yahoo"
        }
      ]
    }
  }
  ```

**Empty/no-result behavior:** Returns empty `signals` or empty arrays per preset when no signals match.

**Validation rules:**

- `strategy` must match a known strategy (`RSI2`, `TURTLE`), otherwise `400`.
- `market_type` must be `stock` or `crypto`.
- `lookback_days` must be within `30..1000`.
- `presets` list (if provided) must have unique `id` values.

**Errors:**

| Status | Error body shape | Error detail | Trigger |
| --- | --- | --- | --- |
| 400 | `{"detail":"Unknown strategy: <strategy>"}` | `Unknown strategy: <strategy>` | `strategy` does not match a supported strategy. |
| 422 | `{"detail":"invalid_ingestion_run_id"}` | `invalid_ingestion_run_id` | `ingestion_run_id` is provided but not a valid UUIDv4. |
| 422 | `{"detail":"ingestion_run_not_found"}` | `ingestion_run_not_found` | `ingestion_run_id` is provided but not found in the repository. |
| 422 | Pydantic validation list | varies | Invalid request body (e.g., `presets` with duplicate `id`, `lookback_days` outside `30..1000`). |

**Example request:**

```bash
curl -s -X POST http://localhost:8000/strategy/analyze \
  -H 'Content-Type: application/json' \
  -d '{
    "symbol": "AAPL",
    "strategy": "RSI2",
    "market_type": "stock",
    "lookback_days": 200
  }'
```

**Example response:**

```json
{
  "symbol": "AAPL",
  "strategy": "RSI2",
  "signals": []
}
```

---

## POST `/analysis/run`

**Purpose:** Manually trigger an analysis run with a client-provided idempotent run ID.

**Request body:**

| Name | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `analysis_run_id` | string | required | none | Client-provided run ID (idempotent key). |
| `ingestion_run_id` | string (UUIDv4) | required | none | Snapshot reference ID. |
| `symbol` | string | required | none | Symbol (e.g., `AAPL`, `BTC/USDT`). |
| `strategy` | string | required | none | Strategy name (case-insensitive). |
| `market_type` | string | optional | `stock` | Must match `stock` or `crypto`. |
| `lookback_days` | integer | optional | `200` | Range `30..1000`. |
| `strategy_config` | object | optional | none | Strategy config overrides. |

**Success response:**

- **Status:** `200 OK`
- **Body:**
  ```json
  {
    "analysis_run_id": "e1f2d3c4-1111-2222-3333-444455556666",
    "ingestion_run_id": "b1b2c3d4-1111-2222-3333-444455556666",
    "symbol": "AAPL",
    "strategy": "RSI2",
    "signals": []
  }
  ```

**Empty/no-result behavior:** Returns `signals: []` when no signals match.

**Validation rules:**

- `strategy` must match a known strategy (`RSI2`, `TURTLE`), otherwise `400`.
- `market_type` must be `stock` or `crypto`.
- `lookback_days` must be within `30..1000`.

**Errors:**

| Status | Error body shape | Error detail | Trigger |
| --- | --- | --- | --- |
| 400 | `{"detail":"Unknown strategy: <strategy>"}` | `Unknown strategy: <strategy>` | `strategy` does not match a supported strategy. |
| 422 | `{"detail":"invalid_ingestion_run_id"}` | `invalid_ingestion_run_id` | `ingestion_run_id` is not a valid UUIDv4 string. |
| 422 | `{"detail":"ingestion_run_not_found"}` | `ingestion_run_not_found` | `ingestion_run_id` does not exist in the repository. |
| 422 | Pydantic validation list | varies | Invalid request body (e.g., missing required fields). |

**Example request:**

```bash
curl -s -X POST http://localhost:8000/analysis/run \
  -H 'Content-Type: application/json' \
  -d '{
    "analysis_run_id": "e1f2d3c4-1111-2222-3333-444455556666",
    "ingestion_run_id": "b1b2c3d4-1111-2222-3333-444455556666",
    "symbol": "AAPL",
    "strategy": "RSI2"
  }'
```

**Example response:**

```json
{
  "analysis_run_id": "e1f2d3c4-1111-2222-3333-444455556666",
  "ingestion_run_id": "b1b2c3d4-1111-2222-3333-444455556666",
  "symbol": "AAPL",
  "strategy": "RSI2",
  "signals": []
}
```

---

## POST `/screener/basic`

**Purpose:** Run a basic screener across a set of symbols and return aggregated setup signals.

**Request body:**

| Name | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `ingestion_run_id` | string (UUIDv4) | optional | none | Snapshot reference ID. Validated if present. |
| `symbols` | array of strings | optional | none | If omitted or empty, a default watchlist is used. |
| `market_type` | string | optional | `stock` | Must match `stock` or `crypto`. |
| `lookback_days` | integer | optional | `200` | Range `30..1000`. |
| `min_score` | number | optional | `30.0` | Range `0..100`. |

Default watchlists:

- `stock`: `AAPL`, `MSFT`, `NVDA`, `META`, `TSLA`
- `crypto`: `BTC/USDT`, `ETH/USDT`, `SOL/USDT`, `BNB/USDT`, `XRP/USDT`

**Success response:**

- **Status:** `200 OK`
- **Body:**
  ```json
  {
    "market_type": "stock",
    "symbols": [
      {
        "symbol": "AAPL",
        "score": 55.2,
        "signal_strength": 0.8,
        "setups": [
          {
            "strategy": "RSI2",
            "score": 55.2,
            "signal_strength": 0.8,
            "stage": "setup",
            "confirmation_rule": "RSI below 10",
            "entry_zone": {"from_": 178.5, "to": 182.0},
            "timeframe": "D1",
            "market_type": "stock"
          }
        ]
      }
    ]
  }
  ```

**Empty/no-result behavior:** Returns `symbols: []` when no setup signals meet `min_score`.

**Validation rules:**

- `market_type` must be `stock` or `crypto`.
- `lookback_days` must be within `30..1000`.
- `min_score` must be within `0..100`.

**Errors:**

| Status | Error body shape | Error detail | Trigger |
| --- | --- | --- | --- |
| 422 | `{"detail":"invalid_ingestion_run_id"}` | `invalid_ingestion_run_id` | `ingestion_run_id` is provided but not a valid UUIDv4. |
| 422 | `{"detail":"ingestion_run_not_found"}` | `ingestion_run_not_found` | `ingestion_run_id` is provided but not found in the repository. |
| 422 | Pydantic validation list | varies | Invalid request body (e.g., `min_score` outside `0..100`). |

**Example request:**

```bash
curl -s -X POST http://localhost:8000/screener/basic \
  -H 'Content-Type: application/json' \
  -d '{
    "market_type": "stock",
    "min_score": 40
  }'
```

**Example response:**

```json
{
  "market_type": "stock",
  "symbols": []
}
```
