# Paper Inspection API

This document defines the read-only paper inspection surface for paper account state, paper trades, and derived paper positions.

## Read-Only Endpoints

All endpoints require `X-Cilly-Role: read_only` (or a higher role).

- `GET /paper/account`
- `GET /paper/trades`
- `GET /paper/positions`

No mutation endpoints are introduced by this surface.

## Authoritative State Ownership

Paper inspection state is authoritative only when derived from Trading Core entities:

- Orders: canonical `Order` entities (`core_orders`)
- Execution lifecycle facts: canonical `ExecutionEvent` entities (`core_execution_events`)
- Trades: canonical `Trade` entities (`core_trades`)
- Positions: derived canonical `Position` entities assembled from canonical trades/orders/execution events

No `/paper/*` runtime endpoint uses legacy `trades` table payloads as the source of truth.

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

`GET /paper/account` is derived from canonical Trading Core state:

- `realized_pnl`: sum of canonical `Trade.realized_pnl` (null treated as `0`)
- `unrealized_pnl`: sum of canonical `Trade.unrealized_pnl` (null treated as `0`)
- `open_trades` / `closed_trades`: canonical `Trade.status`
- `open_positions`: derived canonical `Position.status`
- `cash`: `starting_cash + realized_pnl`
- `equity`: `cash + unrealized_pnl`
- `total_pnl`: `realized_pnl + unrealized_pnl`
- `as_of`: max non-null timestamp across canonical trade open/close timestamps

## Trading Core Alignment

- `GET /paper/trades` returns canonical `Trade` entities from Trading Core persistence.
- `GET /paper/positions` returns canonical `Position` entities derived from canonical Trading Core entities.
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
