# API Usage Contract (MVP v1.1)

This document defines the stable usage contract for the MVP v1 API. It documents the currently implemented behavior without changing runtime logic.

## Base URL

- Local development: `http://localhost:8000`

## Canonical Operator Analysis Contract

This section is the single authoritative request/response contract for operator-triggered analysis.

- Authoritative endpoint: `POST /analysis/run`
- Governing workflow: the operator-facing manual analysis trigger currently represented by the owner dashboard workflow
- Not authoritative: `POST /strategy/analyze`, `POST /screener/basic`, or any future UI-specific adapter payloads

If multiple operator-facing UIs coexist, they are expected to implement this contract when they trigger the manual operator analysis flow.

### Canonical request body

Clients must send a JSON object with the following shape:

| Name | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `ingestion_run_id` | string (UUIDv4) | required | none | Snapshot reference for the analysis. |
| `symbol` | string | required | none | Instrument identifier such as `AAPL` or `BTC/USDT`. |
| `strategy` | string | required | none | Canonical strategy key. Use `RSI2` or `TURTLE`. |
| `market_type` | string | optional | `stock` | Must be `stock` or `crypto`. |
| `lookback_days` | integer | optional | `200` | Must be in the inclusive range `30..1000`. |
| `strategy_config` | object | optional | omitted | Strategy-specific parameter overrides. |

Canonical request example:

```json
{
  "ingestion_run_id": "b1b2c3d4-1111-2222-3333-444455556666",
  "symbol": "AAPL",
  "strategy": "RSI2",
  "market_type": "stock",
  "lookback_days": 200,
  "strategy_config": {
    "oversold_threshold": 10.0
  }
}
```

Request boundary notes:

- `analysis_run_id` is not part of the canonical request contract. The server is authoritative for run identity and computes `analysis_run_id` from the canonical request payload.
- A legacy client may still send `analysis_run_id`, and the current backend may ignore it, but frontend and backend follow-up work for this issue must treat that field as out of contract.
- Required versus optional fields are defined only by the table above. If an optional field is omitted, the documented default applies.

### Canonical success response body

The endpoint returns a JSON object with the following top-level shape on success:

| Name | Type | Required | Notes |
| --- | --- | --- | --- |
| `analysis_run_id` | string | required | Deterministic server-computed run identifier for this canonical request payload. |
| `ingestion_run_id` | string (UUIDv4) | required | Snapshot reference used for the run. |
| `symbol` | string | required | Instrument identifier used for the run. |
| `strategy` | string | required | Canonical strategy key returned in uppercase form. |
| `signals` | array of signal objects | required | Zero or more analysis signals. Empty array means the run succeeded but produced no signals. |

Signal object shape:

| Name | Type | Required | Notes |
| --- | --- | --- | --- |
| `symbol` | string | required | Signal symbol. |
| `strategy` | string | required | Signal strategy key. |
| `direction` | string | required | Signal direction such as `long` or `short`. |
| `score` | number | required | Numeric signal score. |
| `timestamp` | string (ISO-8601 datetime) | required | Signal timestamp. |
| `stage` | string | required | Signal stage such as `setup`. |
| `timeframe` | string | required | Timeframe emitted by the analysis engine. |
| `market_type` | string | required | `stock` or `crypto`. |
| `data_source` | string | required | Data source identifier used by the backend. |
| `entry_zone` | object | optional | Present when the signal has an entry range. |
| `confirmation_rule` | string | optional | Present when the signal includes an operator-readable confirmation rule. |

`entry_zone` object shape when present:

| Name | Type | Required | Notes |
| --- | --- | --- | --- |
| `from_` | number | required | Inclusive lower bound of the suggested entry zone. |
| `to` | number | required | Inclusive upper bound of the suggested entry zone. |

Canonical success response example:

```json
{
  "analysis_run_id": "e1f2d3c4-1111-2222-3333-444455556666",
  "ingestion_run_id": "b1b2c3d4-1111-2222-3333-444455556666",
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

### Canonical failure semantics

- Validation and snapshot failures use the API-wide error formats documented below.
- For this operator contract, valid payload decisions come from the canonical request table above and the error table in the `POST /analysis/run` section below.
- A successful response with `signals: []` is still a valid completed run.

## Phase 37 Watchlist Workflow

The repository now includes a bounded Phase 37 watchlist workflow on top of the existing snapshot-only analysis surface.

- Persistence and CRUD are exposed through `/watchlists` routes.
- Execution and ranking are exposed through `POST /watchlists/{watchlist_id}/execute`.
- The workflow is bounded to saved watchlists, snapshot-only execution, deterministic ranking, and isolated symbol failures.
- This API contract does not imply later-phase charting, alerts, trading-desk, or broader market-data-product claims.

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
- **POST `/watchlists/{watchlist_id}/execute`** (`api.main.execute_watchlist`) follows the same snapshot-only path through `_run_snapshot_analysis` and `run_watchlist_analysis(snapshot_only=True)`, but isolates symbol-level snapshot failures into the response payload instead of failing the entire request.
- **POST `/screener/basic`** (`api.main.basic_screener`) follows the same snapshot-only path through `_run_snapshot_analysis` and `run_watchlist_analysis(snapshot_only=True)`.

**Non-deterministic (engine usage outside API snapshot-only guards):**

- Direct engine calls to `cilly_trading.engine.core.run_watchlist_analysis` with `snapshot_only=False` (default) and without `ingestion_run_id` load data via `cilly_trading.engine.data.load_ohlcv`, which depends on current time (`_utc_now`) and external data sources (`yfinance` for stocks, `ccxt`/Binance for crypto). Results can vary over time or with upstream data changes.
- If `snapshot_only=False` and snapshot data is missing or invalid, the engine may skip symbols instead of failing the request, which makes outcomes dependent on snapshot availability at runtime.

### Direct provider adapter status vs runtime-safe usage claims

The repository contains direct provider adapter code in `cilly_trading.engine.data` (`_load_stock_yahoo`, `_load_crypto_binance`, and `load_ohlcv`).

This presence does **not** by itself establish a runtime-safe deterministic API integration claim.

A repository-safe market-data claim must distinguish:

- **Adapter presence:** direct provider code exists.
- **Deterministic usage boundary:** runtime API entrypoints enforce snapshot-only paths (`load_ohlcv_snapshot`) with `ingestion_run_id`.
- **Operational/runtime evidence:** tests verify snapshot-only endpoints do not call direct provider loaders in the deterministic API path.

The snapshot-only API contract remains the authoritative deterministic runtime boundary.

### Error semantics (analysis endpoints)

These errors are emitted by `/strategy/analyze`, `/analysis/run`, `/watchlists/{watchlist_id}/execute`, and `/screener/basic` unless the endpoint-specific section below narrows the behavior:

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
| `timeframe` | string | optional | none | Persisted signal timeframe filter (e.g., `D1`). |
| `from` | string (ISO-8601 datetime) | optional | none | Start time (inclusive) for `created_at`. |
| `to` | string (ISO-8601 datetime) | optional | none | End time (inclusive) for `created_at`. |
| `sort` | string | optional | `created_at_desc` | One of `created_at_asc`, `created_at_desc`. |
| `limit` | integer | optional | `50` | Range `1..500`. |
| `offset` | integer | optional | `0` | Must be `>= 0`. |

**Validation rules:**

- `preset`, `start`, and `end` are not accepted on this endpoint.
- `from` must be `<=` `to` when both are provided.
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
| 422 | `{"detail":"preset query parameter is not supported; use timeframe"}` | `preset query parameter is not supported; use timeframe` | Legacy `preset` query parameter is provided. |
| 422 | `{"detail":"start query parameter is not supported; use from"}` | `start query parameter is not supported; use from` | Legacy `start` query parameter is provided. |
| 422 | `{"detail":"end query parameter is not supported; use to"}` | `end query parameter is not supported; use to` | Legacy `end` query parameter is provided. |
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
| `limit` | integer | optional | `50` | Range `1..500`. |
| `offset` | integer | optional | `0` | Must be `>= 0`. |

**Validation rules:**

- `strategy` and `timeframe` are required.
- `min_score` must be `>= 0` when provided.
- `limit` must be within `1..500`.

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
    "limit": 50,
    "offset": 0,
    "total": 1
  }
  ```

**Empty/no-result behavior:** Returns `items: []`, the provided `limit/offset`, and `total: 0`.

### Errors

| Status | Error body shape | Error detail | Trigger |
| --- | --- | --- | --- |
| 422 | Pydantic validation list | varies | Missing or invalid query parameters (e.g., missing `strategy`). |

### Example

**Request:**

```bash
curl -s "http://localhost:8000/screener/v2/results?strategy=TURTLE&timeframe=D1&limit=25&offset=0"
```

**Response:**

```json
{
  "items": [],
  "limit": 25,
  "offset": 0,
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

Manually trigger the canonical operator analysis flow. This is the authoritative route for operator-triggered analysis requests and responses. The API computes a deterministic run ID from the canonical request payload and returns it.

### Request

**Request body:**

| Name | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `ingestion_run_id` | string (UUIDv4) | required | none | Snapshot reference ID. |
| `symbol` | string | required | none | Symbol (e.g., `AAPL`, `BTC/USDT`). |
| `strategy` | string | required | none | Canonical strategy key. Use `RSI2` or `TURTLE`. |
| `market_type` | string | optional | `stock` | Must match `stock` or `crypto`. |
| `lookback_days` | integer | optional | `200` | Range `30..1000`. |
| `strategy_config` | object | optional | none | Strategy config overrides. |

**Validation rules:**

- This endpoint is the authoritative contract for operator-triggered analysis. Client payloads should follow the canonical contract in the `Canonical Operator Analysis Contract` section above.
- `strategy` must match a known strategy (`RSI2`, `TURTLE`), otherwise `400`.
- `market_type` must be `stock` or `crypto`.
- `lookback_days` must be within `30..1000`.
- `analysis_run_id` is not part of the canonical request contract. If a legacy client still sends it, the current backend ignores it.

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
  "analysis_run_id": "e1f2d3c4-1111-2222-3333-444455556666",
  "ingestion_run_id": "b1b2c3d4-1111-2222-3333-444455556666",
  "symbol": "AAPL",
  "strategy": "RSI2",
  "signals": []
}
```

---

## POST /watchlists

### Purpose

Create a persisted watchlist with a stable identifier, display name, and ordered symbol membership.

### Request

**Request body:**

| Name | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `watchlist_id` | string | required | none | Stable saved-watchlist identifier. |
| `name` | string | required | none | Human-readable watchlist name. |
| `symbols` | array of strings | required | none | Ordered symbol list. Must not be empty. |

**Validation rules:**

- Mutation requires an operator-capable role.
- `symbols` must not be empty and must not contain empty values.
- Duplicate names or identifiers are rejected.

### Success response

- **Status:** `200 OK`
- **Body:**
  ```json
  {
    "watchlist_id": "tech-growth",
    "name": "Tech Growth",
    "symbols": ["MSFT", "AAPL", "NVDA"]
  }
  ```

### Errors

| Status | Error body shape | Error detail | Trigger |
| --- | --- | --- | --- |
| 401 | `{"detail":"unauthorized"}` | `unauthorized` | `X-Cilly-Role` header is missing or invalid. |
| 403 | `{"detail":"forbidden"}` | `forbidden` | Caller role cannot mutate watchlists. |
| 422 | `{"detail":"watchlist symbols must not contain empty values"}` | `watchlist symbols must not contain empty values` | Symbol list contains empty members. |
| 422 | `{"detail":"watchlist name and symbols must remain unique"}` | `watchlist name and symbols must remain unique` | Duplicate identifier or name. |
| 422 | Pydantic validation list | varies | Invalid request body such as missing fields. |

---

## GET /watchlists

### Purpose

Read the saved watchlist inventory in deterministic order.

### Request

No request body.

**Validation rules:**

- Read access requires a valid authenticated role header and a role permitted to inspect watchlists.

### Success response

- **Status:** `200 OK`
- **Body:**
  ```json
  {
    "items": [
      {
        "watchlist_id": "alpha-list",
        "name": "Alpha",
        "symbols": ["AAPL"]
      }
    ],
    "total": 1
  }
  ```

**Empty/no-result behavior:** Returns `items: []` and `total: 0` when no watchlists are stored.

### Errors

| Status | Error body shape | Error detail | Trigger |
| --- | --- | --- | --- |
| 401 | `{"detail":"unauthorized"}` | `unauthorized` | `X-Cilly-Role` header is missing or invalid. |
| 403 | `{"detail":"forbidden"}` | `forbidden` | Caller has a valid role but lacks read access. |

---

## GET /watchlists/{watchlist_id}

### Purpose

Read one persisted watchlist by identifier.

### Request

**Path parameters:**

| Name | Type | Required | Notes |
| --- | --- | --- | --- |
| `watchlist_id` | string | required | Saved watchlist identifier. |

### Success response

- **Status:** `200 OK`
- **Body:**
  ```json
  {
    "watchlist_id": "tech-growth",
    "name": "Tech Growth",
    "symbols": ["MSFT", "AAPL", "NVDA"]
  }
  ```

### Errors

| Status | Error body shape | Error detail | Trigger |
| --- | --- | --- | --- |
| 401 | `{"detail":"unauthorized"}` | `unauthorized` | `X-Cilly-Role` header is missing or invalid. |
| 403 | `{"detail":"forbidden"}` | `forbidden` | Caller has a valid role but lacks read access. |
| 404 | `{"detail":"watchlist_not_found"}` | `watchlist_not_found` | `watchlist_id` does not exist. |

---

## PUT /watchlists/{watchlist_id}

### Purpose

Replace the saved watchlist name and symbol membership for an existing watchlist.

### Request

**Path parameters:**

| Name | Type | Required | Notes |
| --- | --- | --- | --- |
| `watchlist_id` | string | required | Saved watchlist identifier. |

**Request body:**

| Name | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `name` | string | required | none | Replacement display name. |
| `symbols` | array of strings | required | none | Replacement ordered symbol list. Must not be empty. |

**Validation rules:**

- Mutation requires an operator-capable role.
- Missing watchlists return `404`.
- Invalid updates do not partially persist.

### Success response

- **Status:** `200 OK`
- **Body:**
  ```json
  {
    "watchlist_id": "tech-growth",
    "name": "Phase 37 Ranked Tech",
    "symbols": ["NVDA", "MSFT"]
  }
  ```

### Errors

| Status | Error body shape | Error detail | Trigger |
| --- | --- | --- | --- |
| 401 | `{"detail":"unauthorized"}` | `unauthorized` | `X-Cilly-Role` header is missing or invalid. |
| 403 | `{"detail":"forbidden"}` | `forbidden` | Caller role cannot mutate watchlists. |
| 404 | `{"detail":"watchlist_not_found"}` | `watchlist_not_found` | `watchlist_id` does not exist. |
| 422 | `{"detail":"watchlist symbols must not contain empty values"}` | `watchlist symbols must not contain empty values` | Symbol list contains empty members. |
| 422 | `{"detail":"watchlist name and symbols must remain unique"}` | `watchlist name and symbols must remain unique` | New state conflicts with another watchlist. |
| 422 | Pydantic validation list | varies | Invalid request body. |

---

## DELETE /watchlists/{watchlist_id}

### Purpose

Delete a persisted watchlist.

### Request

**Path parameters:**

| Name | Type | Required | Notes |
| --- | --- | --- | --- |
| `watchlist_id` | string | required | Saved watchlist identifier. |

### Success response

- **Status:** `200 OK`
- **Body:**
  ```json
  {
    "watchlist_id": "tech-growth",
    "deleted": true
  }
  ```

### Errors

| Status | Error body shape | Error detail | Trigger |
| --- | --- | --- | --- |
| 401 | `{"detail":"unauthorized"}` | `unauthorized` | `X-Cilly-Role` header is missing or invalid. |
| 403 | `{"detail":"forbidden"}` | `forbidden` | Caller role cannot mutate watchlists. |
| 404 | `{"detail":"watchlist_not_found"}` | `watchlist_not_found` | `watchlist_id` does not exist. |

---

## POST /watchlists/{watchlist_id}/execute

### Purpose

Run the persisted watchlist workflow against a saved watchlist and return deterministic ranked results for later UI consumption.

### Request

**Path parameters:**

| Name | Type | Required | Notes |
| --- | --- | --- | --- |
| `watchlist_id` | string | required | Saved watchlist identifier. Must already exist. |

**Request body:**

| Name | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `ingestion_run_id` | string (UUIDv4) | required | none | Snapshot reference ID. |
| `market_type` | string | optional | `stock` | Must match `stock` or `crypto`. |
| `lookback_days` | integer | optional | `200` | Range `30..1000`. |
| `min_score` | number | optional | `30.0` | Range `0..100`. Only setup signals at or above this score are ranked. |

**Validation rules:**

- `watchlist_id` must identify an existing saved watchlist, otherwise `404`.
- `ingestion_run_id` must be a valid UUIDv4 and must exist.
- Mutation-level watchlist CRUD happens through the `/watchlists` routes above; this endpoint only executes an already-saved watchlist.
- Unlike `/screener/basic`, this endpoint does not require every watchlist symbol to be snapshot-ready up front. Snapshot failures for individual symbols are isolated into the response `failures` array.

### Success response

- **Status:** `200 OK`
- **Body:**
  ```json
  {
    "analysis_run_id": "d6d596a6f792d1f04b6cb13df7dd1f4707f258d8d0678d163fc8cb5ea1c9f2ad",
    "ingestion_run_id": "b1b2c3d4-1111-2222-3333-444455556666",
    "watchlist_id": "tech-growth",
    "watchlist_name": "Tech Growth",
    "market_type": "stock",
    "ranked_results": [
      {
        "rank": 1,
        "symbol": "NVDA",
        "score": 68.2,
        "signal_strength": 0.91,
        "setups": [
          {
            "strategy": "TURTLE",
            "score": 68.2,
            "signal_strength": 0.91,
            "stage": "setup",
            "confirmation_rule": "Breakout confirmed",
            "entry_zone": {"from_": 178.5, "to": 182.0},
            "timeframe": "D1",
            "market_type": "stock"
          }
        ]
      }
    ],
    "failures": [
      {
        "symbol": "MSFT",
        "code": "snapshot_data_invalid",
        "detail": "snapshot data unavailable or invalid for symbol"
      }
    ]
  }
  ```

**Ranking rules:**

- Only `setup` signals with `score >= min_score` participate in ranking.
- Ranked items are sorted deterministically by `score DESC`, then `signal_strength DESC`, then `symbol ASC`.
- `rank` is the 1-based position after deterministic sorting.
- The response is designed for the bounded Phase 37 `/ui` workflow and does not, by itself, imply later trading-desk or charting capability.

**Empty/no-result behavior:** Returns `ranked_results: []` when no qualifying setup signals are produced. Symbol-level failures may still be present in `failures`.

### Errors

| Status | Error body shape | Error detail | Trigger |
| --- | --- | --- | --- |
| 401 | `{"detail":"unauthorized"}` | `unauthorized` | `X-Cilly-Role` header is missing or invalid. |
| 403 | `{"detail":"forbidden"}` | `forbidden` | Caller has a valid role but lacks execution privileges. |
| 404 | `{"detail":"watchlist_not_found"}` | `watchlist_not_found` | `watchlist_id` does not exist. |
| 422 | `{"detail":"invalid_ingestion_run_id"}` | `invalid_ingestion_run_id` | `ingestion_run_id` is not a valid UUIDv4 string. |
| 422 | `{"detail":"ingestion_run_not_found"}` | `ingestion_run_not_found` | `ingestion_run_id` does not exist in the repository. |
| 422 | Pydantic validation list | varies | Invalid request body (for example `min_score` outside `0..100`). |

### Example

**Request:**

```bash
curl -s -X POST http://localhost:8000/watchlists/tech-growth/execute \
  -H 'Content-Type: application/json' \
  -H 'X-Cilly-Role: operator' \
  -d '{
    "ingestion_run_id": "b1b2c3d4-1111-2222-3333-444455556666",
    "market_type": "stock",
    "lookback_days": 200,
    "min_score": 30.0
  }'
```

**Response:**

```json
{
  "analysis_run_id": "d6d596a6f792d1f04b6cb13df7dd1f4707f258d8d0678d163fc8cb5ea1c9f2ad",
  "ingestion_run_id": "b1b2c3d4-1111-2222-3333-444455556666",
  "watchlist_id": "tech-growth",
  "watchlist_name": "Tech Growth",
  "market_type": "stock",
  "ranked_results": [],
  "failures": []
}
```

---

## GET /decision-cards

### Purpose

Inspect decision-card outputs through a bounded read-only surface for operator and research review workflows.

### Request

**Query parameters:**

| Name | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `run_id` | string | optional | none | Filter by artifact run directory. |
| `symbol` | string | optional | none | Filter by decision-card symbol. |
| `strategy_id` | string | optional | none | Filter by decision-card strategy ID. |
| `decision_card_id` | string | optional | none | Filter by exact decision-card ID. |
| `qualification_state` | string | optional | none | One of `reject`, `watch`, `paper_candidate`, `paper_approved`. |
| `review_state` | string | optional | none | One of `ranked`, `blocked`, `approved` (`blocked` maps to `reject`, `approved` maps to `paper_approved`, `ranked` maps to non-reject states). |
| `sort` | string | optional | `generated_at_desc` | One of `generated_at_desc`, `generated_at_asc`. |
| `limit` | integer | optional | `50` | Range `1..500`. |
| `offset` | integer | optional | `0` | Must be `>= 0`. |

### Success response

- **Status:** `200 OK`
- **Body:**
  ```json
  {
    "items": [
      {
        "run_id": "run-a",
        "artifact_name": "decision_card.json",
        "decision_card_id": "dc-001",
        "generated_at_utc": "2026-03-24T08:00:00Z",
        "symbol": "AAPL",
        "strategy_id": "RSI2",
        "qualification_state": "paper_approved",
        "qualification_color": "green",
        "qualification_summary": "Opportunity is approved for bounded paper-trading only.",
        "aggregate_score": 84.15,
        "confidence_tier": "high",
        "hard_gate_policy_version": "hard-gates.v1",
        "hard_gate_blocking_failure": false,
        "hard_gates": [],
        "component_scores": [],
        "rationale_summary": "Qualification is resolved from explicit hard gates, bounded scores, and confidence rules.",
        "gate_explanations": [],
        "score_explanations": [],
        "final_explanation": "Action state is deterministic and does not imply live-trading approval.",
        "metadata": {}
      }
    ],
    "limit": 50,
    "offset": 0,
    "total": 1
  }
  ```

**Deterministic ordering:**

- Primary: `generated_at_utc` (`DESC` by default, `ASC` when `sort=generated_at_asc`)
- Tie-breakers: `decision_card_id ASC`, `run_id ASC`, `artifact_name ASC`

**Empty/no-result behavior:** Returns `items: []` and `total: 0` when no matching decision cards are available.

### Errors

| Status | Error body shape | Error detail | Trigger |
| --- | --- | --- | --- |
| 401 | `{"detail":"unauthorized"}` | `unauthorized` | `X-Cilly-Role` header is missing or invalid. |
| 403 | `{"detail":"forbidden"}` | `forbidden` | Caller has a valid role but lacks read access. |
| 422 | Pydantic validation list | varies | Invalid query constraints or enum values (for example `limit=0` or unsupported `review_state`). |

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
