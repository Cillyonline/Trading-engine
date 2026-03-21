# Trading Core Inspection API

This document defines the read-only trading core inspection surface aligned with the canonical model (`Order`, `ExecutionEvent`, `Trade`, `Position`).

## Read-Only Endpoints

All endpoints require `X-Cilly-Role: read_only` (or higher role).

- `GET /trading-core/orders`
- `GET /trading-core/execution-events`
- `GET /trading-core/trades`
- `GET /trading-core/positions`

No mutation endpoints are introduced by this surface.

## Canonical Alignment

- Response payload entities map directly to canonical models in `src/cilly_trading/models.py`.
- Decimal-valued canonical fields are serialized as strings.
- Deterministic ordering is guaranteed by canonical repository ordering and stable in-memory ordering for derived positions.

## Query Parameters

### `GET /trading-core/orders`

- Optional filters: `strategy_id`, `symbol`, `order_id`
- Pagination: `limit` (`1..500`), `offset` (`>=0`)

### `GET /trading-core/execution-events`

- Optional filters: `strategy_id`, `symbol`, `order_id`, `trade_id`
- Pagination: `limit` (`1..500`), `offset` (`>=0`)

### `GET /trading-core/trades`

- Optional filters: `strategy_id`, `symbol`, `position_id`, `trade_id`
- Pagination: `limit` (`1..500`), `offset` (`>=0`)

### `GET /trading-core/positions`

- Optional filters: `strategy_id`, `symbol`, `position_id`
- Pagination: `limit` (`1..500`), `offset` (`>=0`)

## Response Shape

Each endpoint returns a paginated payload in this structure:

```json
{
  "items": [],
  "limit": 50,
  "offset": 0,
  "total": 0
}
```

The `items` array contains canonical entity payloads for the requested endpoint.
