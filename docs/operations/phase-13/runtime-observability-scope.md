# Phase 13 – Runtime Status, Health & Introspection Scope

## Purpose
Phase 13 introduces runtime observability interfaces only. This phase exposes current runtime information for operators and diagnostics and does not change runtime behavior, decision logic, or lifecycle behavior.

## Non-Goals (Out of Scope)
- New runtime states or lifecycle transitions.
- Control operations (start, stop, pause, resume, restart, or equivalent).
- Any write operation against runtime state, configuration, queues, or storage.
- Live trading workflows or broker integrations.
- Backtesting workflows.
- AI-driven or strategy decision logic.

## Read-Only Contract (No Side Effects)
- All Phase 13 status, health, and introspection endpoints **MUST** be read-only.
- These endpoints **MUST NOT** trigger runtime state transitions.
- These endpoints **MUST NOT** mutate memory, configuration, queues, persistence, or external systems.
- These endpoints **MUST NOT** execute expensive side-effecting operations (for example: forced refreshes, cache rebuilds, or external reconfiguration).
- The API contract **WILL NOT** expose operator command surfaces.
- Exposed fields are intentionally minimal and stable.

## Phase-13 Endpoint Invariants (Issue #284 Guardrails)

### Endpoints in Scope
- `GET /health`
- `GET /runtime/introspection`

### Forbidden Side Effects
The endpoints above are read-only and must not produce side effects. The following are explicitly forbidden:
- Runtime lifecycle/state mutation (start/stop/pause/resume/restart/transition calls).
- Event emission or command dispatch into runtime/event buses.
- Persistence writes (for example signal/analysis save operations).
- External write I/O (filesystem/network/db writes initiated by endpoint handling).
- In-memory mutation of runtime controller state as part of the request.

### Enforcement
- Endpoint-layer guard markers (`_assert_phase_13_read_only_endpoint`) make the Phase-13 read-only intent explicit.
- Test-level `Phase13SideEffectDetector` snapshots endpoint-adjacent state before and after each call and asserts:
  - before/after snapshots are equal,
  - no lifecycle transition calls,
  - no persistence writes,
  - no event emissions.
- A deterministic detector-failure test proves violations are caught.

## Runtime Status
Runtime status reports current engine identity, lifecycle snapshot, and timing metadata without defining or changing lifecycle transitions.

### Status Fields
- `engine_id` (string): Stable identifier of the running engine instance.
- `runtime_state` (string): Current lifecycle state snapshot (generic values only, e.g. `starting`, `running`, `stopping`, `stopped`, `error`).
- `since` (RFC3339 timestamp): Time when the current `runtime_state` began.
- `uptime_seconds` (number): Elapsed runtime duration in seconds.
- `version` (object): Runtime version metadata.
  - `build` (string)
  - `commit` (string)
  - `api` (string)
- `clock` (object): Server time metadata.
  - `now` (RFC3339 timestamp)
- `last_event` (object, optional): Minimal recent event context.
  - `at` (RFC3339 timestamp)
  - `kind` (string)
  - `message` (string)

### Example Status Payload
```json
{
  "engine_id": "engine-main",
  "runtime_state": "running",
  "since": "2026-02-08T10:00:00Z",
  "uptime_seconds": 8640,
  "version": {
    "build": "2026.02.08.1",
    "commit": "abc123def",
    "api": "v1"
  },
  "clock": {
    "now": "2026-02-08T12:24:00Z"
  },
  "last_event": {
    "at": "2026-02-08T12:23:58Z",
    "kind": "heartbeat",
    "message": "Runtime loop active"
  }
}
```

### Field Stability
Status fields in this scope are stable. Any future additive changes must be versioned and documented.

## Health Semantics
Health expresses operational readiness at a high level and remains implementation-agnostic.

### Health Levels
- `healthy`: Core runtime services are available, checks are passing, and no known condition currently blocks normal operation.
- `degraded`: Runtime is available but one or more non-fatal checks indicate reduced reliability or elevated risk.
- `unavailable`: Runtime is not operationally available for normal use, or critical checks are failing.

### Health Payload Shape
- `level` (string): `healthy` | `degraded` | `unavailable`
- `summary` (string): Human-readable one-line health summary.
- `checks` (array): Small set of operational checks.
  - `name` (string)
  - `status` (string)
  - `detail` (string, optional)
  - `last_ok_at` (RFC3339 timestamp, optional)

### Example Health Payload
```json
{
  "level": "degraded",
  "summary": "Runtime available with one degraded dependency check",
  "checks": [
    {
      "name": "runtime_loop",
      "status": "ok",
      "last_ok_at": "2026-02-08T12:23:59Z"
    },
    {
      "name": "outbound_queue",
      "status": "warn",
      "detail": "Queue depth near configured threshold",
      "last_ok_at": "2026-02-08T12:23:10Z"
    }
  ]
}
```

## Introspection (Operator/Debug)
Introspection exposes safe runtime metadata to support operator diagnostics without exposing sensitive data.

### Included Metadata
- `configuration_snapshot`: Redacted and safe effective configuration view (no secrets).
- `feature_flags`: Read-only feature flag states, if present.
- `runtime_limits`: Safe runtime limits (for example: queue capacity thresholds) when non-sensitive.
- `dependencies`: Optional dependency status summary suitable for diagnostics.

### Explicit Exclusions
- Secrets, credentials, private keys, tokens, or raw secret material.
- Personal data.
- Large data dumps by default.
- Raw logs by default.

## Derived Follow-Up Issues (P13-A1, P13-A2, P13-A3, P13-D1)
- **P13-A1**: Implement runtime status endpoint(s) that conform to the status contract and field stability requirements in this document.
- **P13-A2**: Implement health endpoint(s) that return the defined health levels and checks payload shape.
- **P13-A3**: Implement introspection endpoint(s) exposing only the included safe metadata and enforcing explicit exclusions.
- **P13-D1**: Publish API reference documentation and example payloads for status, health, and introspection, aligned with this scope contract.
