# API Usage Contract (MVP v1.1)

This document defines the stable usage contract for the MVP v1 API. It documents the currently implemented behavior without changing runtime logic.

## Base URL

- Local development: `http://localhost:8000`

## Common Conventions

### Snapshot-first analysis contract

All analysis entrypoints are **snapshot-only**:

- **No implicit live data.** Every analysis run requires an `ingestion_run_id` that points to a snapshot in the analysis repository.
- **Deterministic failure on missing/partial snapshots.** If the snapshot does not exist, is not ready for the requested symbols/timeframe, or contains invalid data, the request fails with a deterministic error (see Error semantics below).
- **Deterministic identities.** Manual analysis runs return a deterministic `analysis_run_id` derived from the canonical request payload, and signals carry deterministic identities based on their stable fields. The API does not re-derive or mutate these identities on read.

### Snapshot ingestion workflow (MVP v1.1, as implemented)

This repository **does not implement** snapshot ingestion. The only implemented behavior is how the API and engine read and validate snapshots already present in the SQLite database. Snapshot creation and population are therefore **out-of-band for MVP** (for example, a separate process must insert rows into the tables described below).

#### Tables and immutability

The database schema defines two snapshot-related tables:

- `ingestion_runs` contains metadata for a snapshot run (`ingestion_run_id`, `created_at`, `source`, `symbols_json`, `timeframe`, `fingerprint_hash`). The API treats this table as the existence check for a snapshot run.
- `ohlcv_snapshots` contains OHLCV rows keyed by `(ingestion_run_id, symbol, timeframe, ts)` and references `ingestion_runs(ingestion_run_id)` via a foreign key. Update and delete triggers abort with `snapshot_immutable`, making snapshot rows immutable once inserted.

No code path in this repository inserts into `ingestion_runs` or `ohlcv_snapshots`; they must already exist for the API to operate.

#### How `ingestion_runs` and `ohlcv_snapshots` are used

Snapshot-only API endpoints call `_require_ingestion_run` and `_require_snapshot_ready`, which delegate to `analysis_run_repo.ingestion_run_exists` and `analysis_run_repo.ingestion_run_is_ready`. Readiness is defined as:

- The `ingestion_runs` row exists for the requested `ingestion_run_id`, **and**
- For every required symbol in the request, **at least one row** exists in `ohlcv_snapshots` with the same `ingestion_run_id`, `symbol`, and `timeframe` (the default timeframe is `D1`).

No validation is performed on the number of rows, date coverage, or completeness beyond the presence of at least one row per symbol/timeframe. The engine then loads snapshot data via `load_ohlcv_snapshot`, which raises `SnapshotDataError` if no rows exist for a symbol/timeframe or if the OHLCV data fails validation; the API converts this to `422 snapshot_data_invalid`.

### Deterministic vs non-deterministic execution paths

**Deterministic (snapshot-only, API entrypoints):**

- **POST `/strategy/analyze`** (`api.main.analyze_strategy`) calls `_run_snapshot_analysis`, which invokes `cilly_trading.engine.core.run_watchlist_analysis(snapshot_only=True)` and loads data via `cilly_trading.engine.data.load_ohlcv_snapshot`. Determinism is limited to the contents of the referenced `ingestion_run_id` snapshot.
- **POST `/analysis/run`** (`api.main.manual_analysis`) follows the same snapshot-only path through `_run_snapshot_analysis` and `run_watchlist_analysis(snapshot_only=True)`.
- **POST `/screener/basic`** (`api.main.basic_screener`) follows the same snapshot-only path through `_run_snapshot_analysis` and `run_watchlist_analysis(snapshot_only=True)`.

**Non-deterministic (engine usage outside API snapshot-only guards):**

- Direct engine calls to `cilly_trading.engine.core.run_watchlist_analysis` with `snapshot_only=False` (default) and without `ingestion_run_id` load data via `cilly_trading.engine.data.load_ohlcv`, which depends on current time (`_utc_now`) and external data sources (`yfinance` for stocks, `ccxt`/Binance for crypto). Results can vary over time or with upstream data changes.
- If `snapshot_only=False` and snapshot data is missing or invalid, the engine may skip symbols instead of failing the request, which makes outcomes dependent on snapshot availability at runtime.

### Error semantics (analysis endpoints)

These errors are emitted by `/strategy/analyze`, `/analysis/run`, and `/screener/basic`:

#### 4xx vs 5xx responses (what they mean)

- **4xx (client error):** The request could not be processed because of the request itself (missing/invalid fields, or snapshot reference problems).  
  **What to do:** Fix the request payload or the snapshot reference, then retry.
- **5xx (server error):** The server failed to complete a valid request.  
  **What to do:** Retry later. If it continues, contact the API operator with the time of failure.

#### Snapshot readiness and validation errors

| Status | Error detail | What happened | What to do next |
| --- | --- | --- | --- |
| 422 | `invalid_ingestion_run_id` | The snapshot reference was not a valid UUIDv4. | Provide a valid UUIDv4 for `ingestion_run_id` and retry. |
| 422 | `ingestion_run_not_found` | The snapshot reference does not exist. | Verify the snapshot was created and use an existing `ingestion_run_id`. |
| 422 | `ingestion_run_not_ready` | The snapshot exists but is missing data for one or more requested symbols/timeframe. | Ensure the snapshot contains at least one row per requested symbol and timeframe, or request symbols/timeframe that exist in the snapshot. |
| 422 | `snapshot_data_invalid` | Snapshot rows exist but failed validation during analysis. | Fix or replace the snapshot data, then retry with a valid `ingestion_run_id`. |

### Supported strategies

- `RSI2`
- `TURTLE`

### Strategy configuration normalization (as implemented)

- Strategy configs are optional; omitted, `null`, or `{}` resolves to an empty config.
- Configs must be mappings; non-mapping values are logged and treated as empty configs.
- Only implemented parameters are accepted; unknown keys are ignored and logged.
- Supported aliases:
  - `RSI2`: `oversold` → `oversold_threshold`
  - `TURTLE`: `entry_lookback` → `breakout_lookback`, `proximity_threshold` → `proximity_threshold_pct`
- If both a canonical key and its alias are provided, the engine raises an error and skips the strategy.
- Invalid types or out-of-range values for known keys raise an error and skip the strategy (no signals for that strategy).

### Strategy config invalidation and skip semantics (as implemented)

Invalid `strategy_config` values do **not** fail the request. The API still returns `200 OK`, and the affected strategy is **skipped** with **no signals produced** for that strategy.

**Skip causes (exactly as implemented):**

- Invalid types for known strategy keys.
- Out-of-range values for known strategy keys.
- Alias and canonical key conflicts (both provided).

**Boundary clarification:**

- Snapshot/ingestion validation errors fail the request (see Error semantics).
- Strategy config errors only skip the affected strategy; the request remains successful.

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

### Empty results vs failures (how to interpret responses)

- **Empty result (success):** A `200 OK` response with an empty `signals` array means the request succeeded but no signals were generated for that snapshot.  
  **What to do:** Treat the response as a successful run; if you expected signals, verify snapshot coverage and strategy configuration.
- **Failure:** A non-2xx response with an error body indicates the request could not be processed.  
  **What to do:** Follow the guidance in the error detail above (fix the request or snapshot, then retry).

### Ingestion run validation

All analysis entrypoints require `ingestion_run_id`. The API enforces:

- Must be a valid UUIDv4 string, otherwise `422` with `{"detail":"invalid_ingestion_run_id"}`.
- Must exist in the analysis run repository, otherwise `422` with `{"detail":"ingestion_run_not_found"}`.
- Must be ready for the requested symbols/timeframe, otherwise `422` with `{"detail":"ingestion_run_not_ready"}`.

---

## GET /health

### Purpose

Purpose: Health check for API availability.

### Request

Request parameters:

| Name | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| N/A | N/A | N/A | N/A | No request parameters. |

### Success response

Success response:

- **Status:** `200 OK`
- **Body:**
  ```json
  {
    "status": "ok"
  }
  ```

**Empty/no-result behavior:** Not applicable.

**Validation rules:** None.

### Errors

| Status | Error body shape | Error detail | Trigger |
| --- | --- | --- | --- |
| None | None | None | No application-defined errors. |

### Example

Example request:

```bash
curl -s http://localhost:8000/health
```

Example response:

```json
{
  "status": "ok"
}
```

---

## GET /signals

### Purpose

Read stored signals with pagination and optional filtering.

### Request

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

**Validation rules:**

- `start` and `from` cannot both be present with different values.
- `end` and `to` cannot both be present with different values.
- Resolved `from` must be `<=` resolved `to`.
- `limit` must be within `1..500`.

### Success response

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

### Errors

| Status | Error body shape | Error detail | Trigger |
| --- | --- | --- | --- |
| 422 | `{"detail":"start conflicts with from"}` | `start conflicts with from` | `start` and `from` provided with different values. |
| 422 | `{"detail":"end conflicts with to"}` | `end conflicts with to` | `end` and `to` provided with different values. |
| 422 | `{"detail":"from must be less than or equal to to"}` | `from must be less than or equal to to` | Resolved `from` is later than resolved `to`. |
| 422 | Pydantic validation list | varies | Invalid query parameter types or constraints (e.g., `limit` outside `1..500`). |

### Example

**Request:**

```bash
curl -s "http://localhost:8000/signals?strategy=RSI2&limit=2&offset=0"
```

**Response:**

```json
{
  "items": [],
  "limit": 2,
  "offset": 0,
  "total": 0
}
```

---

## GET /screener/v2/results

### Purpose

Read screener results filtered by strategy and timeframe.

### Request

**Query parameters:**

| Name | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `strategy` | string | required | none | Strategy name. |
| `timeframe` | string | required | none | Timeframe filter (e.g., `D1`). |
| `min_score` | number | optional | none | Minimum score filter (`>= 0`). |

**Validation rules:**

- `strategy` and `timeframe` are required.
- `min_score` must be `>= 0` when provided.

### Success response

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

### Errors

| Status | Error body shape | Error detail | Trigger |
| --- | --- | --- | --- |
| 422 | Pydantic validation list | varies | Missing or invalid query parameters (e.g., missing `strategy`). |

### Example

**Request:**

```bash
curl -s "http://localhost:8000/screener/v2/results?strategy=TURTLE&timeframe=D1"
```

**Response:**

```json
{
  "items": [],
  "total": 0
}
```

---

## POST /strategy/analyze

### Purpose

Run a strategy analysis for a single symbol. Returns raw signal output for the requested symbol and strategy. When presets are provided, results are grouped by preset ID.

### Request

**Request body:**

| Name | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `ingestion_run_id` | string (UUIDv4) | required | none | Snapshot reference ID (snapshot-only). |
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

**Validation rules:**

- `strategy` must match a known strategy (`RSI2`, `TURTLE`), otherwise `400`.
- `market_type` must be `stock` or `crypto`.
- `lookback_days` must be within `30..1000`.
- `presets` list (if provided) must have unique `id` values.

### Success response

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

### Errors

| Status | Error body shape | Error detail | Trigger |
| --- | --- | --- | --- |
| 400 | `{"detail":"Unknown strategy: <strategy>"}` | `Unknown strategy: <strategy>` | `strategy` does not match a supported strategy. |
| 422 | `{"detail":"invalid_ingestion_run_id"}` | `invalid_ingestion_run_id` | `ingestion_run_id` is provided but not a valid UUIDv4. |
| 422 | `{"detail":"ingestion_run_not_found"}` | `ingestion_run_not_found` | `ingestion_run_id` is provided but not found in the repository. |
| 422 | `{"detail":"ingestion_run_not_ready"}` | `ingestion_run_not_ready` | Snapshot exists but is not ready for the requested symbol/timeframe. |
| 422 | `{"detail":"snapshot_data_invalid"}` | `snapshot_data_invalid` | Snapshot data failed validation during analysis. |
| 422 | Pydantic validation list | varies | Invalid request body (e.g., `presets` with duplicate `id`, `lookback_days` outside `30..1000`). |

### Example

**Request:**

```bash
curl -s -X POST http://localhost:8000/strategy/analyze \
  -H 'Content-Type: application/json' \
  -d '{
    "ingestion_run_id": "b1b2c3d4-1111-2222-3333-444455556666",
    "symbol": "AAPL",
    "strategy": "RSI2",
    "market_type": "stock",
    "lookback_days": 200
  }'
```

**Response:**

```json
{
  "symbol": "AAPL",
  "strategy": "RSI2",
  "signals": []
}
```

---

## POST /analysis/run

### Purpose

Manually trigger an analysis run. The API computes a deterministic run ID from the canonical request payload and returns it (idempotent). The `analysis_run_id` field in the request is optional and ignored; the server computes the deterministic ID.

### Request

**Request body:**

| Name | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `analysis_run_id` | string | optional | none | Optional client-provided run ID (ignored). |
| `ingestion_run_id` | string (UUIDv4) | required | none | Snapshot reference ID. |
| `symbol` | string | required | none | Symbol (e.g., `AAPL`, `BTC/USDT`). |
| `strategy` | string | required | none | Strategy name (case-insensitive). |
| `market_type` | string | optional | `stock` | Must match `stock` or `crypto`. |
| `lookback_days` | integer | optional | `200` | Range `30..1000`. |
| `strategy_config` | object | optional | none | Strategy config overrides. |

**Validation rules:**

- `strategy` must match a known strategy (`RSI2`, `TURTLE`), otherwise `400`.
- `market_type` must be `stock` or `crypto`.
- `lookback_days` must be within `30..1000`.

### Success response

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

### Errors

| Status | Error body shape | Error detail | Trigger |
| --- | --- | --- | --- |
| 400 | `{"detail":"Unknown strategy: <strategy>"}` | `Unknown strategy: <strategy>` | `strategy` does not match a supported strategy. |
| 422 | `{"detail":"invalid_ingestion_run_id"}` | `invalid_ingestion_run_id` | `ingestion_run_id` is not a valid UUIDv4 string. |
| 422 | `{"detail":"ingestion_run_not_found"}` | `ingestion_run_not_found` | `ingestion_run_id` does not exist in the repository. |
| 422 | `{"detail":"ingestion_run_not_ready"}` | `ingestion_run_not_ready` | Snapshot exists but is not ready for the requested symbol/timeframe. |
| 422 | `{"detail":"snapshot_data_invalid"}` | `snapshot_data_invalid` | Snapshot data failed validation during analysis. |
| 422 | Pydantic validation list | varies | Invalid request body (e.g., missing required fields). |

### Example

**Request:**

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

**Response:**

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

## POST /screener/basic

### Purpose

Run a basic screener across a set of symbols and return aggregated setup signals.

### Request

**Request body:**

| Name | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `ingestion_run_id` | string (UUIDv4) | required | none | Snapshot reference ID (snapshot-only). |
| `symbols` | array of strings | optional | none | If omitted or empty, a default watchlist is used. |
| `market_type` | string | optional | `stock` | Must match `stock` or `crypto`. |
| `lookback_days` | integer | optional | `200` | Range `30..1000`. |
| `min_score` | number | optional | `30.0` | Range `0..100`. |

Default watchlists:

- `stock`: `AAPL`, `MSFT`, `NVDA`, `META`, `TSLA`
- `crypto`: `BTC/USDT`, `ETH/USDT`, `SOL/USDT`, `BNB/USDT`, `XRP/USDT`

**Validation rules:**

- `market_type` must be `stock` or `crypto`.
- `lookback_days` must be within `30..1000`.
- `min_score` must be within `0..100`.

### Success response

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

### Errors

| Status | Error body shape | Error detail | Trigger |
| --- | --- | --- | --- |
| 422 | `{"detail":"invalid_ingestion_run_id"}` | `invalid_ingestion_run_id` | `ingestion_run_id` is provided but not a valid UUIDv4. |
| 422 | `{"detail":"ingestion_run_not_found"}` | `ingestion_run_not_found` | `ingestion_run_id` is provided but not found in the repository. |
| 422 | `{"detail":"ingestion_run_not_ready"}` | `ingestion_run_not_ready` | Snapshot exists but is not ready for the requested symbols/timeframe. |
| 422 | `{"detail":"snapshot_data_invalid"}` | `snapshot_data_invalid` | Snapshot data failed validation during analysis. |
| 422 | Pydantic validation list | varies | Invalid request body (e.g., `min_score` outside `0..100`). |

### Example

**Request:**

```bash
curl -s -X POST http://localhost:8000/screener/basic \
  -H 'Content-Type: application/json' \
  -d '{
    "ingestion_run_id": "b1b2c3d4-1111-2222-3333-444455556666",
    "market_type": "stock",
    "min_score": 40
  }'
```

**Response:**

```json
{
  "market_type": "stock",
  "symbols": []
}
```

---

## Audit trail / reproducibility checklist

### Inputs to capture

- `ingestion_run_id` (snapshot reference ID)
- Request payload (symbol(s), strategy, market_type, lookback_days, strategy_config/presets)
- Strategy configuration used (normalized config after alias resolution; unknown keys removed)
- Timeframe (`D1` in MVP)

### Outputs to store/log

- `analysis_run_id` (computed deterministic run identity for `/analysis/run`)
- `ingestion_run_id`
- Canonical request payload reference (exact payload used to compute the run ID)
- Timestamps used by the snapshot (as provided by the snapshot data)
