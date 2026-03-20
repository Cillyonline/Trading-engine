# Trading Lifecycle State Machine

Issue `#719` defines one deterministic lifecycle model for `Order`, `Trade`, and `Position`.

## Scope

- This state machine governs lifecycle state transitions only.
- Broker-specific behavior, strategy logic, UI workflow, and notifications are out of scope.
- Lifecycle validation is centralized in `src/cilly_trading/trading_lifecycle.py`.

## Canonical States

### Order

- `created`
- `submitted`
- `partially_filled`
- `filled` (terminal)
- `cancelled` (terminal)
- `rejected` (terminal)

### Trade

- `open`
- `closed` (terminal)

### Position

- `flat`
- `open`
- `closed` (terminal)

## Allowed Transitions

### Order

- `created -> submitted`
- `created -> cancelled`
- `created -> rejected`
- `submitted -> partially_filled`
- `submitted -> filled`
- `submitted -> cancelled`
- `submitted -> rejected`
- `partially_filled -> filled`

All other `Order` transitions are forbidden.

### Trade

- `open -> closed`

All other `Trade` transitions are forbidden.

### Position

- `flat -> open`
- `open -> closed`

All other `Position` transitions are forbidden.

## Transition Invariants

### Order Invariants

- `filled_quantity` is never negative and never greater than `quantity`.
- Non-fill states (`created`, `submitted`, `cancelled`, `rejected`) require `filled_quantity == 0`.
- `partially_filled` requires `0 < filled_quantity < quantity`.
- `filled` requires `filled_quantity == quantity`.
- Across transitions:
  - `quantity` is immutable.
  - `filled_quantity` is monotonic non-decreasing.

### Trade Invariants

- `quantity_closed` never exceeds `quantity_opened`.
- `open` requires `quantity_closed < quantity_opened`.
- `closed` requires `quantity_closed == quantity_opened`.
- Across transitions:
  - `quantity_opened` is immutable.
  - `quantity_closed` is monotonic non-decreasing.

### Position Invariants

- `net_quantity == quantity_opened - quantity_closed`.
- `quantity_closed` never exceeds `quantity_opened`.
- `flat` requires all quantities to be zero.
- `open` requires `net_quantity > 0`.
- `closed` requires `net_quantity == 0` and `quantity_opened == quantity_closed`.
- Across transitions:
  - `quantity_opened` is immutable.
  - `quantity_closed` is monotonic non-decreasing.

## Validation Guards

Reusable guards are exposed from `src/cilly_trading/trading_lifecycle.py`:

- Transition guards:
  - `validate_order_transition`
  - `validate_trade_transition`
  - `validate_position_transition`
- Transition-order guards:
  - `validate_order_transition_sequence`
  - `validate_trade_transition_sequence`
  - `validate_position_transition_sequence`
- State invariant guards:
  - `validate_order_state_invariants`
  - `validate_trade_state_invariants`
  - `validate_position_state_invariants`
- Transition invariant guards:
  - `validate_order_transition_invariants`
  - `validate_trade_transition_invariants`
  - `validate_position_transition_invariants`

This is the canonical lifecycle model and must be reused instead of creating parallel transition logic.
