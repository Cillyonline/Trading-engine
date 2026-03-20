# Trading Core Execution Persistence Boundary

Issue `#720` aligns execution persistence with the canonical trading core model.

## Canonical Persistence Contract

Execution persistence is bounded to canonical entities:

- `Order` (authoritative intent and lifecycle state)
- `ExecutionEvent` (authoritative immutable execution fact)
- `Trade` (derived lifecycle summary)

The persistence interface is `CanonicalExecutionRepository` in:

- `src/cilly_trading/repositories/__init__.py`

SQLite implementation:

- `src/cilly_trading/repositories/execution_core_sqlite.py`

## Repository Access Pattern

Canonical writes are explicit by entity:

1. `save_order(order)`
2. `save_execution_events(events)`
3. `save_trade(trade)`

Canonical reads are explicit by entity:

1. `get_order(order_id)` / `list_orders(...)`
2. `list_execution_events(...)`
3. `get_trade(trade_id)` / `list_trades(...)`

This keeps replay and audit reads independent from paper-trading legacy payload storage.

## Deterministic Ordering

Deterministic read ordering is fixed by SQL order-by clauses:

- Orders: `created_at`, `sequence`, `order_id`
- Execution events: `occurred_at`, `sequence`, `event_id`
- Trades: `opened_at`, `trade_id`

All timestamps are normalized for lexical UTC ordering (`Z` treated as `+00:00`).

## Auditability and Replay

- `ExecutionEvent` rows are append-only by `event_id`.
- Re-inserting an existing `event_id` with a different payload raises `conflicting_execution_event_payload`.
- Canonical payloads are persisted as canonical JSON and validated on read, preserving deterministic round-trip behavior.

## No Conflicting Model Boundary

Legacy `TradeRepository` now explicitly uses `PersistedTradePayload` for paper-trading snapshots.
Canonical execution persistence uses `Order`/`ExecutionEvent`/`Trade` only through `CanonicalExecutionRepository`.
This removes type-level ambiguity between legacy and canonical persistence boundaries.
