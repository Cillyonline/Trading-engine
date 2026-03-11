# Engine Runtime Lifecycle Contract

## Document Purpose
This document defines the runtime lifecycle state machine and the operator-facing API contract for explicit runtime start and stop controls.
It documents the existing lifecycle model and the response semantics that start/stop endpoints must follow when they are exposed.
It does not require or describe a concrete endpoint implementation.

## Scope and Non-Scope
### In Scope
- Explicit lifecycle state definitions.
- Allowed lifecycle transitions for a single runtime instance.
- Operator-facing `start` and `stop` API contract semantics.
- Invalid-transition behavior for operator-facing lifecycle controls.
- Boundaries between engine-owned lifecycle authority and API-exposed control endpoints.

### Out of Scope
- Implementing new endpoints.
- Changing lifecycle states or transition rules.
- Startup or shutdown internals beyond documented externally visible effects.
- Authentication or authorization behavior.
- UI behavior for lifecycle actions.

## Lifecycle State Model
The engine runtime lifecycle is defined by exactly six states:

1. **init**
   - The runtime controller exists.
   - The runtime has not yet been prepared for operation.

2. **ready**
   - The runtime has been initialized and is prepared for operation.
   - The runtime is not yet actively executing.

3. **running**
   - The runtime is actively executing its operational workload.

4. **paused**
   - The runtime has been operator-paused after reaching `running`.
   - Initialization and runtime ownership are preserved while execution is suspended.

5. **stopping**
   - The runtime is in terminal transition away from active execution.
   - This is a transitional state and not an operator target state.

6. **stopped**
   - The runtime is no longer operationally active.
   - This is the terminal state for the current runtime instance.

No additional lifecycle states are part of this contract.

## Allowed Lifecycle Transitions
The lifecycle contract permits only the following direct transitions:

- `init -> ready`
- `ready -> running`
- `running -> paused`
- `paused -> running`
- `running -> stopping`
- `paused -> stopped`
- `stopping -> stopped`

No other direct transitions are valid under this contract.

## Transition Rules
- `start` may compose `init -> ready -> running` when the runtime has not yet been initialized.
- `resume` is the only path from `paused` back to `running`.
- `stop` may compose `running -> stopping -> stopped`.
- `stopped` is terminal for the current runtime instance.
- A stopped runtime instance is not restarted by re-entering an earlier state.
- The API contract must not invent transitions that are not listed above.

## Control Operation Mapping
The existing engine-owned control operations map to the state machine as follows:

| Control operation | Existing engine behavior | Resulting state semantics |
| --- | --- | --- |
| `start_engine_runtime()` | If state is `init`, it performs `init -> ready`, then `ready -> running`. If state is `ready`, it performs `ready -> running`. If state is already `running`, it returns `running`. Otherwise it raises `LifecycleTransitionError`. | Start is valid from `init`, `ready`, and `running`. |
| `pause_engine_runtime()` | Pauses only from `running`; repeated pause on `paused` is idempotent; other states raise `LifecycleTransitionError`. | Pause is a control-plane suspension, not a terminal transition. |
| `resume_engine_runtime()` | Resumes only from `paused`; repeated resume on `running` is idempotent; other states raise `LifecycleTransitionError`. | Resume is distinct from start. |
| `shutdown_engine_runtime()` | Returns `init` or `ready` unchanged; transitions `running -> stopping -> stopped`; transitions `paused -> stopped`; transitions `stopping -> stopped`; returns `stopped` unchanged. | Stop is terminal when runtime has entered execution or shutdown phases and is a no-op before that point. |

## Operator-Facing Runtime Control API Contract
This section defines the operator-facing API contract that explicit start/stop endpoints must follow.
It is normative for request/response behavior and intentionally separate from route implementation work.

### Common Request and Response Shape
- Method: `POST`
- Path-specific endpoints: `POST /execution/start` and `POST /execution/stop`
- Request body: none
- Query parameters: none
- Response media type: `application/json`
- Success body shape:

```json
{
  "state": "running"
}
```

- The response body uses the same single-field control-plane shape already used by pause/resume: `{"state":"<runtime_state>"}`.
- Lifecycle transition conflicts use `409 Conflict` with the existing application error shape:

```json
{
  "detail": "controller-authored transition error message"
}
```

### `POST /execution/start`
Purpose: Request that the runtime be in `running` state using the existing start semantics.

#### Success behavior

| Current runtime state | Endpoint result | Notes |
| --- | --- | --- |
| `init` | `200 {"state":"running"}` | Internally composes `init -> ready -> running`. |
| `ready` | `200 {"state":"running"}` | Internally performs `ready -> running`. |
| `running` | `200 {"state":"running"}` | Idempotent success. |

#### Invalid lifecycle transition behavior

| Current runtime state | Endpoint result | Why |
| --- | --- | --- |
| `paused` | `409 {"detail":"Cannot ensure running runtime from state 'paused'."}` | Start is not resume. A paused runtime must use the existing resume control. |
| `stopping` | `409 {"detail":"Cannot ensure running runtime from state 'stopping'."}` | Terminal shutdown has already begun. |
| `stopped` | `409 {"detail":"Cannot ensure running runtime from state 'stopped'."}` | `stopped` is terminal for the runtime instance. |

The `detail` value is the propagated `LifecycleTransitionError` text produced by the existing engine lifecycle helper.

### `POST /execution/stop`
Purpose: Request that the runtime perform the existing shutdown behavior for the current runtime instance.

#### Success behavior

| Current runtime state | Endpoint result | Notes |
| --- | --- | --- |
| `init` | `200 {"state":"init"}` | Accepted no-op. The runtime has not yet entered an active or shutdown-capable phase. |
| `ready` | `200 {"state":"ready"}` | Accepted no-op. The runtime is prepared but not executing. |
| `running` | `200 {"state":"stopped"}` | Internally composes `running -> stopping -> stopped`. |
| `paused` | `200 {"state":"stopped"}` | Stop terminalizes a paused runtime directly. |
| `stopping` | `200 {"state":"stopped"}` | Completes an in-progress shutdown. |
| `stopped` | `200 {"state":"stopped"}` | Idempotent success. |

#### Invalid lifecycle transition behavior
- No lifecycle-transition `409 Conflict` is defined for `POST /execution/stop` under the current runtime controller behavior.
- Requests received in `init` or `ready` are accepted as no-op successes and return the unchanged state.
- Requests received in `stopping` or `stopped` are accepted as idempotent shutdown completions.

## Endpoint Binding to Existing Lifecycle Helpers
The documented operator-facing contract is intentionally derived from the existing engine-owned lifecycle helpers.
An implementation that exposes these endpoints should not make new lifecycle decisions; it should translate helper behavior to HTTP as follows:

| Endpoint | Engine helper | HTTP translation rule |
| --- | --- | --- |
| `POST /execution/start` | `start_engine_runtime()` | Return `200 {"state":"running"}` on success. If the helper raises `LifecycleTransitionError`, return `409 {"detail":"<helper message>"}`. |
| `POST /execution/stop` | `shutdown_engine_runtime()` | Return `200 {"state":"<returned_state>"}` for all lifecycle-controlled outcomes under the current model. |

The following decision table is normative for lifecycle-controlled responses:

| Current runtime state | `POST /execution/start` | `POST /execution/stop` |
| --- | --- | --- |
| `init` | `200 {"state":"running"}` | `200 {"state":"init"}` |
| `ready` | `200 {"state":"running"}` | `200 {"state":"ready"}` |
| `running` | `200 {"state":"running"}` | `200 {"state":"stopped"}` |
| `paused` | `409 {"detail":"Cannot ensure running runtime from state 'paused'."}` | `200 {"state":"stopped"}` |
| `stopping` | `409 {"detail":"Cannot ensure running runtime from state 'stopping'."}` | `200 {"state":"stopped"}` |
| `stopped` | `409 {"detail":"Cannot ensure running runtime from state 'stopped'."}` | `200 {"state":"stopped"}` |

No other lifecycle-specific status code or response body is part of this contract.

## Relation to Existing Pause/Resume Controls
- `POST /execution/start` is not a synonym for `POST /execution/resume`.
- `paused -> running` remains owned by the existing resume behavior.
- `POST /execution/stop` may be called while paused and results in `stopped`, not `running`.
- A stopped runtime instance is not resumed or restarted by either pause/resume controls or the documented start contract.

## Engine vs API Lifecycle Contract

### Lifecycle Authority
- Lifecycle authority is owned by the engine runtime domain.
- The API may expose lifecycle control endpoints, but those endpoints delegate to engine-owned lifecycle operations.
- The API must not redefine lifecycle states, redefine transition rules, or bypass engine transition checks.

### Observer and Control Boundaries
- Read-only endpoints such as runtime introspection and system state observe lifecycle state.
- Control-plane endpoints may request transitions through engine-owned lifecycle helpers.
- API exposure of start/stop/pause/resume does not transfer lifecycle ownership from the engine to the API.

## Invariants and Guarantees
The following invariants are normative:

1. **State Validity Invariant**
   - The runtime lifecycle state is always one of: `init`, `ready`, `running`, `paused`, `stopping`, `stopped`.

2. **Transition Topology Invariant**
   - The runtime may move only along the allowed transitions listed in this document.

3. **Resume Path Invariant**
   - `paused` returns to `running` only through resume semantics, not through start semantics.

4. **Terminal State Invariant**
   - `stopped` is terminal for the current runtime instance.

5. **Stop Composition Invariant**
   - A stop request from `running` completes through `stopping` before publishing `stopped`.

6. **Single-Authority Invariant**
   - Exactly one lifecycle authority domain governs transitions for a runtime instance: the engine runtime domain.

7. **API Delegation Invariant**
   - Operator-facing API controls delegate lifecycle requests to engine-owned lifecycle behavior and must preserve the documented response semantics.
