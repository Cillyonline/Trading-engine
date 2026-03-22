# Paper Inspection API

This document defines the read-only paper inspection surface for paper account state, paper trades, and derived paper positions.

## Read-Only Endpoints

All endpoints require `X-Cilly-Role: read_only` (or a higher role).

- `GET /paper/account`
- `GET /paper/trades`
- `GET /paper/positions`

No mutation endpoints are introduced by this surface.

## Paper Account State

`GET /paper/account` returns one explicit bounded state payload (all monetary fields use 4-decimal precision):

- `starting_cash`
- `cash`
- `equity`
- `realized_pnl`
- `unrealized_pnl`
- `total_pnl`
- `open_positions`
- `open_trades`
- `closed_trades`
- `as_of`

Starting cash defaults to `100000` and can be overridden via `CILLY_PAPER_ACCOUNT_STARTING_CASH` (must be numeric and non-negative).

## Trading Core Alignment

- `GET /paper/trades` returns canonical `Trade` entities.
- `GET /paper/positions` returns canonical `Position` entities derived from paper trades.
- Position/trade lifecycle state semantics follow the same canonical model constraints as Trading Core.

## Deterministic Ordering

- Paper trades are ordered by `opened_at`, then `trade_id`.
- Paper positions are ordered by `opened_at`, then `position_id`.
- Filtering and pagination preserve stable deterministic ordering.

## Query Parameters

### `GET /paper/trades`

- Optional filters: `strategy_id`, `symbol`, `position_id`, `trade_id`
- Pagination: `limit` (`1..500`), `offset` (`>=0`)

### `GET /paper/positions`

- Optional filters: `strategy_id`, `symbol`, `position_id`
- Pagination: `limit` (`1..500`), `offset` (`>=0`)

## Response Shape

`GET /paper/trades` and `GET /paper/positions` use:

```json
{
  "items": [],
  "limit": 50,
  "offset": 0,
  "total": 0
}
```

The JSON example block above is intentionally closed to keep the document valid for markdown renderers.
