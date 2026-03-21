# Trading Core Domain Model

Issue `#718` defines one canonical trading-core vocabulary for `Trade`, `Position`, `Order`, and `ExecutionEvent`.
Issue `#726` adds a bounded shared risk baseline vocabulary reused across trading-core entities.

## Canonical Entities

| Entity | Authority | Responsibility | Must not own |
| --- | --- | --- | --- |
| `Order` | Authoritative | The requested trading instruction and its bounded lifecycle state. | Position aggregation, trade lifecycle summaries |
| `ExecutionEvent` | Authoritative | Immutable execution-side facts for one order lifecycle transition. | Aggregated position state, aggregated trade state |
| `Position` | Derived | Deterministic aggregate exposure state built from execution events. | New execution facts, order intent |
| `Trade` | Derived | Deterministic lifecycle summary assembled from orders and execution events. | Order submission intent, immutable execution facts |

## Required vs Optional

- `Order` requires deterministic identity and lifecycle fields: `order_id`, `strategy_id`, `symbol`, `sequence`, `side`, `order_type`, `time_in_force`, `status`, `quantity`, and `created_at`.
- `Order` optional fields are present only when lifecycle state justifies them: `submitted_at`, `average_fill_price`, `last_execution_event_id`, `position_id`, and `trade_id`.
- `ExecutionEvent` requires `event_id`, `order_id`, `strategy_id`, `symbol`, `side`, `event_type`, `occurred_at`, and `sequence`.
- `ExecutionEvent` fill payload fields `execution_quantity`, `execution_price`, and `commission` are required only for fill events.
- `Position` requires deterministic aggregate state: `position_id`, `strategy_id`, `symbol`, `direction`, `status`, `opened_at`, `quantity_opened`, `quantity_closed`, `net_quantity`, and `average_entry_price`.
- `Position` optional fields are lifecycle-dependent: `closed_at`, `average_exit_price`, and `realized_pnl`.
- `Trade` requires lifecycle identity and aggregate state: `trade_id`, `position_id`, `strategy_id`, `symbol`, `direction`, `status`, `opened_at`, `quantity_opened`, `quantity_closed`, and `average_entry_price`.
- `Trade` optional fields are lifecycle-dependent: `closed_at`, `average_exit_price`, and `realized_pnl`.

## Risk Baseline Vocabulary

The trading core exposes one bounded risk vocabulary with explicit required vs derived ownership.

| Entity | Required risk fields | Derived risk fields | Invariants |
| --- | --- | --- | --- |
| `Order` | `entry_price`, `stop_price` (when order-level baseline risk is provided) | `planned_exposure`, `max_risk` | `entry_price` and `stop_price` must be provided together; `stop_price < entry_price` for long entries; `planned_exposure = quantity * entry_price`; `max_risk = quantity * (entry_price - stop_price)` |
| `ExecutionEvent` | none | `fill_exposure`, `realized_pnl_delta` | fill events may define risk deltas; if `fill_exposure` is set then `fill_exposure = execution_quantity * execution_price`; non-fill events must not define execution/risk payload fields |
| `Position` | none | `exposure_notional`, `realized_pnl`, `unrealized_pnl` | `exposure_notional = net_quantity * average_entry_price`; flat/closed positions must not carry non-zero `unrealized_pnl` |
| `Trade` | none | `exposure_notional`, `realized_pnl`, `unrealized_pnl` | `exposure_notional = (quantity_opened - quantity_closed) * average_entry_price`; closed trades must not carry non-zero `unrealized_pnl` |

Boundaries:

- `Order` owns baseline entry/stop intent.
- `ExecutionEvent` owns immutable fill facts and optional fill-level risk deltas.
- `Position` and `Trade` own derived realized/unrealized and exposure state.
- Portfolio-level policy and allocation are out of scope.

## Relationships

- `ExecutionEvent.order_id -> Order.order_id`
- `Order.position_id -> Position.position_id` when the order affects a position
- `Trade.position_id -> Position.position_id`
- `Trade.execution_event_ids -> ExecutionEvent.event_id`
- `Position.execution_event_ids -> ExecutionEvent.event_id`
- `Trade` and `Position` may both reference the same `Order` and `ExecutionEvent` identifiers, but only `Order` and `ExecutionEvent` are authoritative sources
- `Order` baseline entry/stop fields provide the anchor for risk semantics reused by later `Trade` and `Position` derivatives

## Determinism Rules

- Canonical serialization uses compact JSON with lexicographically sorted keys.
- Decimal-valued trading-core fields serialize as strings to avoid float drift.
- Identifier lists are normalized into deterministic lexicographic order.
- Relationship validation rejects unknown references and mismatched entity links.

## Lifecycle Interpretation

1. `Order` captures intent.
2. `ExecutionEvent` records immutable lifecycle facts for that order.
3. `Position` derives current or closed aggregate exposure from those facts.
4. `Trade` derives the lifecycle summary tied to the position and linked execution events.

## Lifecycle State Machine

Deterministic lifecycle states, transition rules, transition-order checks, and transition invariants for `Order`, `Trade`, and `Position` are defined once in:

- `docs/architecture/trading_lifecycle_state_machine.md`
- `src/cilly_trading/trading_lifecycle.py`
