# Runtime Chart Data Contract

## Purpose
This document defines the deterministic chart-data contract for Phase 39 runtime visual analysis on the backend-served `/ui` surface.

It is intentionally bounded to existing runtime API responses and snapshot-governed analysis behavior. No new chart-specific route is introduced in Phase 39.

## Contract Status
- Runtime surface: `/ui`
- Scope: read-only visual analysis
- Contract schema: `phase39.chart-data.v1`
- Reference validator and projection module: `src/api/chart_contract.py`

## Route Reuse Evaluation
Phase 39 reuses the existing runtime API routes before considering any chart-specific route shape.

| Existing route | Reuse status | Chart role | Snapshot binding | Contract status |
| --- | --- | --- | --- | --- |
| `POST /analysis/run` | Reused as-is | Primary single-symbol visual-analysis source | Explicit `ingestion_run_id` in request and response | Authoritative |
| `POST /watchlists/{watchlist_id}/execute` | Reused as-is | Primary ranked multi-symbol visual-analysis source | Explicit `ingestion_run_id` in request and response | Authoritative |
| `GET /signals` | Reused with boundary | Historical signal evidence when no session-local analysis payload is active | Not available in the response shape | Fallback-only |

### Reuse Decision
- Phase 39 does not need a new backend route to define chart data.
- Chart consumers must project existing runtime payloads into the bounded contract described below.
- If a later issue introduces a dedicated chart endpoint, it must serialize this same schema and preserve the same snapshot-first constraints.

## Snapshot Artifact Evaluation
The chart contract is tied to the repository's existing snapshot-governed analysis path.

| Existing artifact or store | Role in chart contract | Boundary |
| --- | --- | --- |
| `ingestion_runs` | Snapshot identity and readiness anchor | Must exist before authoritative chart state is created |
| `ohlcv_snapshots` | Immutable input data for analysis | Source of analysis determinism, not a direct chart payload in Phase 39 |
| persisted `analysis_runs` results | Deterministic cached analysis identity | May be reused when request payloads match |
| persisted `signals` rows | Historical signal evidence | Read-only fallback, not a market-data feed |

This means the Phase 39 chart contract stays attached to deterministic analysis artifacts rather than raw live-market delivery.

## Top-Level Contract
Every Phase 39 chart payload projected for `/ui` must validate to this shape:

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `schema_version` | string | yes | Must be `phase39.chart-data.v1` |
| `contract_scope` | string | yes | Must be `runtime_visual_analysis` |
| `constraints` | object | yes | Explicit snapshot-first and non-productization guardrails |
| `source` | object | yes | Declares which existing route the payload came from |
| `context` | object | yes | Binds the payload to `/ui` plus the known runtime identifiers |
| `points` | array | yes | Ordered chart-consumer items derived from the reused route |
| `failures` | array | yes | Symbol-level failures when the source route exposes them |

### `constraints`

| Field | Type | Required | Value |
| --- | --- | --- | --- |
| `snapshot_first` | boolean | yes | `true` |
| `live_data_allowed` | boolean | yes | `false` |
| `market_data_product` | boolean | yes | `false` |
| `chart_route_added` | boolean | yes | `false` |

These fields make the Phase 39 boundary machine-checkable: the contract is snapshot-first, does not allow live data, does not create a market-data product surface, and does not imply a new chart route.

### `source`

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `source_type` | string enum | yes | `analysis_run`, `watchlist_execution`, or `signal_log` |
| `endpoint` | string enum | yes | `/analysis/run`, `/watchlists/{watchlist_id}/execute`, or `/signals` |
| `reuse` | string | yes | Must be `existing_runtime_api` |
| `authority` | string enum | yes | `authoritative` or `fallback_only` |
| `snapshot_binding` | string enum | yes | `explicit_ingestion_run_id` or `not_available_in_source` |
| `order_basis` | string enum | yes | `response_order` or `rank_ascending` |

### `context`

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `runtime_surface` | string | yes | Must be `/ui` |
| `analysis_run_id` | string or null | yes | Present for analysis-run and watchlist-execution projections |
| `ingestion_run_id` | string or null | yes | Present only when the reused source exposes snapshot binding |
| `watchlist_id` | string or null | yes | Present for watchlist execution |
| `watchlist_name` | string or null | yes | Present for watchlist execution |
| `symbol` | string or null | yes | Present for single-symbol analysis |
| `strategy` | string or null | yes | Present for single-symbol analysis and signal-log points |
| `market_type` | string or null | yes | Present when the reused source exposes it |

### `points`
`points` is the ordered list chart consumers render. The order is deterministic because it is inherited from the reused route contract:

- `POST /analysis/run`: preserve response order from `signals`
- `POST /watchlists/{watchlist_id}/execute`: preserve ranked order from `ranked_results`
- `GET /signals`: preserve response order from `items`

Each point exposes only derived analysis fields that already exist in the reused runtime payloads:

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `sequence` | integer | yes | 1-based deterministic position inside the payload |
| `symbol` | string | yes | Instrument identifier |
| `strategy` | string or null | yes | Present when source data exposes a strategy |
| `stage` | string or null | yes | Present when source data exposes a stage |
| `score` | number or null | yes | Derived analysis score, not raw market price history |
| `signal_strength` | number or null | yes | Present for ranked watchlist results when available |
| `rank` | integer or null | yes | Present for ranked watchlist results |
| `recorded_at` | string or null | yes | Timestamp field copied from the reused source when available |
| `timeframe` | string or null | yes | Present when source data exposes a timeframe |
| `market_type` | string or null | yes | Present when source data exposes a market type |
| `data_source` | string or null | yes | Present when source data exposes a provider label |
| `confirmation_rule` | string or null | yes | Present when source data exposes an operator-readable confirmation |
| `entry_zone` | object or null | yes | Present when source data exposes an entry range |
| `setups` | array | yes | Ranked-result setup summaries carried forward from watchlist execution |

### `failures`
`failures` is empty for analysis-run and signal-log projections. For watchlist execution it carries the existing symbol-level failure items returned by `POST /watchlists/{watchlist_id}/execute`.

## Source-Specific Boundary Rules

### `POST /analysis/run`
- This is the authoritative chart source for single-symbol Phase 39 visual analysis.
- Consumers may assume snapshot binding because `ingestion_run_id` is part of the response.
- Consumers must not infer candlestick or OHLCV payload guarantees from this contract. The chart data is derived analysis only.

### `POST /watchlists/{watchlist_id}/execute`
- This is the authoritative chart source for ranked multi-symbol visual analysis.
- `ranked_results` and `failures` are projected without inventing new ranking semantics.
- Consumers must treat the ranking as analysis evidence, not as a trade blotter, alert queue, or market scanner product.

### `GET /signals`
- This source is fallback-only.
- The current `GET /signals` response does not expose `ingestion_run_id`, so it cannot serve as the authoritative snapshot anchor for the active Phase 39 session.
- Consumers may use it for historical score visibility only and must label or treat it as read-only evidence rather than current snapshot state.

## Example Projection
Example analysis-run chart payload:

```json
{
  "schema_version": "phase39.chart-data.v1",
  "contract_scope": "runtime_visual_analysis",
  "constraints": {
    "snapshot_first": true,
    "live_data_allowed": false,
    "market_data_product": false,
    "chart_route_added": false
  },
  "source": {
    "source_type": "analysis_run",
    "endpoint": "/analysis/run",
    "reuse": "existing_runtime_api",
    "authority": "authoritative",
    "snapshot_binding": "explicit_ingestion_run_id",
    "order_basis": "response_order"
  },
  "context": {
    "runtime_surface": "/ui",
    "analysis_run_id": "run-001",
    "ingestion_run_id": "11111111-1111-4111-8111-111111111111",
    "watchlist_id": null,
    "watchlist_name": null,
    "symbol": "AAPL",
    "strategy": "RSI2",
    "market_type": null
  },
  "points": [
    {
      "sequence": 1,
      "symbol": "AAPL",
      "strategy": "RSI2",
      "stage": "setup",
      "score": 42.5,
      "signal_strength": null,
      "rank": null,
      "recorded_at": "2025-01-02T00:00:00+00:00",
      "timeframe": "D1",
      "market_type": "stock",
      "data_source": "yahoo",
      "confirmation_rule": "RSI below 10",
      "entry_zone": {
        "from_": 178.5,
        "to": 182.0
      },
      "setups": []
    }
  ],
  "failures": []
}
```

The example above is illustrative only. The following sections remain normative contract guidance.

## Consumer Expectations
- Consumers must validate the chart payload before rendering it.
- Consumers must prefer `authoritative` sources over `fallback_only` sources for active session state.
- Consumers must not request or expect live ticks, OHLCV bars, provider metadata expansion, broker actions, alerts, or Strategy Lab semantics from this contract.
- Consumers must not treat this contract as a new market-data product layer.

## Explicit Non-Goals
This contract does not introduce:
- broker or live-market integrations
- a new market-data product layer
- alerts or notification payloads
- Strategy Lab APIs
- paper-trading workflow APIs
- Phase 40 dashboard aggregation APIs

That non-expansion is part of the contract itself, not just an implementation note.
