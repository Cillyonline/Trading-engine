# Strategy Lifecycle Model

## States

- **DRAFT**: Initial design and development state. The strategy is not yet approved for production use.
- **EVALUATION**: Controlled validation state for deterministic review and promotion checks.
- **PRODUCTION**: Approved operational state for strategies that passed evaluation.
- **DEPRECATED**: Terminal retirement state. A deprecated strategy cannot be reactivated.

## Transition Graph

Only the following directed transitions are allowed:

- `DRAFT -> EVALUATION`
- `DRAFT -> DEPRECATED`
- `EVALUATION -> PRODUCTION`
- `EVALUATION -> DEPRECATED`
- `PRODUCTION -> DEPRECATED`

All other transitions are illegal.

```text
DRAFT ------> EVALUATION ------> PRODUCTION ------> DEPRECATED
  \              \                                   ^
   \              +---------------> DEPRECATED       |
    +-----------------------------> DEPRECATED -------+
```

## Promotion Invariants

- Only `EVALUATION` can promote to `PRODUCTION`.
- `PRODUCTION` cannot revert to any prior state.
- `DEPRECATED` is terminal and has no outbound transitions.
- Every transition must be explicit in the transition matrix and validated before state change.

## Deterministic Validation

Validation is deterministic and implemented with an explicit transition matrix.

- Valid transitions are accepted.
- Illegal transitions raise a deterministic error message.
- Self-transitions are illegal.
- Transitions from `DEPRECATED` are always rejected as terminal-state violations.

## Execution Eligibility (Design Only)

Execution eligibility is defined by lifecycle state semantics only:

- `PRODUCTION` is the lifecycle state intended for execution eligibility.
- `DRAFT`, `EVALUATION`, and `DEPRECATED` are not execution-eligible by definition.

This document defines eligibility semantics only and does not enforce execution gating.
