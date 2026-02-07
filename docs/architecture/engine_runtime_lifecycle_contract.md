# Engine Runtime Lifecycle Contract

## Document Purpose
This document defines the conceptual lifecycle contract for the engine runtime.
It specifies lifecycle states, allowed state transitions, ownership boundaries, and invariants.
It does not define implementation mechanics.

## Scope and Non-Scope
### In Scope
- Explicit lifecycle state definitions.
- Conceptual transition constraints between states.
- Contract boundaries between engine and API regarding lifecycle.
- Lifecycle ownership and authority rules.
- Conceptual invariants and guarantees.

### Out of Scope
- Startup or shutdown mechanics.
- Internal control flow, sequencing logic, or algorithms.
- Threading, asynchronous execution, or process-model decisions.
- API endpoint design changes.
- Testing strategy.

## Lifecycle State Model
The engine runtime lifecycle is defined by exactly five states:

1. **init**
   - The runtime lifecycle has been created as a lifecycle subject.
   - The runtime is not yet declared usable for operational execution.

2. **ready**
   - The runtime is declared operationally prepared.
   - The runtime is not yet actively executing its operational workload.

3. **running**
   - The runtime is declared to be in active operational execution.

4. **stopping**
   - The runtime is declared to be in terminal transition away from running.
   - This is a transitional state and not an operational target state.

5. **stopped**
   - The runtime is declared no longer operationally active.
   - This is a terminal lifecycle state for the current runtime instance.

No additional lifecycle states are part of this contract.

## Allowed Conceptual Transitions
The lifecycle contract permits only the following direct state transitions:

- `init -> ready`
- `ready -> running`
- `running -> stopping`
- `stopping -> stopped`

No other direct transitions are valid under this contract.

## Transition Rules
- Lifecycle progression is forward-only for a runtime instance.
- A state change is valid only if it matches one of the allowed transitions.
- `running` is reachable only through `ready`.
- `stopped` is reachable only through `stopping`.
- Re-entry into earlier states is not permitted for the same runtime instance.

## Engine vs API Lifecycle Contract

### Engine Lifecycle Guarantees
The engine lifecycle contract guarantees that:
- Lifecycle state exists and is one of the five defined states.
- Published lifecycle state reflects the current conceptual lifecycle phase.
- State progression respects the allowed conceptual transitions.
- Lifecycle authority is exercised only by lifecycle owner roles defined in this document.

### API Reliance Contract
The API may rely on the following:
- Lifecycle state names and meanings as defined here.
- The allowed transition topology defined in this contract.
- Lifecycle invariants listed in this document.

### API Lifecycle Prohibitions
The API must not:
- Create new lifecycle states.
- Redefine state meanings.
- Trigger or force lifecycle transitions.
- Assume lifecycle paths that are not explicitly allowed by this contract.
- Claim lifecycle ownership authority.

## Runtime Ownership Rules

### Lifecycle Authority
- Lifecycle authority is owned by the engine runtime domain.
- Authority includes deciding and publishing lifecycle transitions.
- Lifecycle authority is singular for a runtime instance.

### Observer vs Controller Roles
- Observer roles may read lifecycle state.
- Controller roles may exercise lifecycle authority.
- The API is an observer of lifecycle state, not a lifecycle controller.

### Lifecycle-Agnostic API (Conceptual Definition)
A lifecycle-agnostic API means:
- API behavior is defined independently of lifecycle orchestration control.
- API may consume lifecycle state as contract context.
- API does not embed lifecycle control responsibility.
- API contract remains valid without requiring API ownership of runtime lifecycle decisions.

## Invariants and Guarantees
The following invariants are normative:

1. **State Validity Invariant**
   - The runtime lifecycle state is always one of: `init`, `ready`, `running`, `stopping`, `stopped`.

2. **Ordering Invariant**
   - For a runtime instance, lifecycle order is monotonic: `init`, `ready`, `running`, `stopping`, `stopped`.

3. **Running Preconditions Invariant**
   - `running` implies that `init` and `ready` have already occurred for the same runtime instance.

4. **Stopped Preconditions Invariant**
   - `stopped` implies that `stopping` has already occurred for the same runtime instance.

5. **No Backward Transition Invariant**
   - No lifecycle transition may move to an earlier state in the lifecycle order.

6. **Single-Authority Invariant**
   - Exactly one lifecycle authority domain governs transitions for a runtime instance.

7. **API Non-Control Invariant**
   - The API never owns or executes lifecycle control authority.

These invariants are conceptual guarantees and do not prescribe implementation techniques.
