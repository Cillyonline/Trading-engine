# Phase 14: Runtime Observability Extension Points

## Goal
Define explicit extension points for runtime observability (`status`, `health`, `introspection`) with strict contracts and read-only guarantees.

## Explicit Extension Points

### 1) `status`
- Purpose: expose runtime status snapshots.
- Input: `ObservabilityContext` (immutable metadata only).
- Output: JSON-serializable DTO payload (`dict[str, JsonValue]`).
- Guarantees:
  - no lifecycle mutation,
  - no persistence mutation,
  - no mutable runtime handle access,
  - execution budget enforcement via registry.

### 2) `health`
- Purpose: expose runtime health checks and summary.
- Input: `ObservabilityContext`.
- Output: JSON-serializable DTO payload.
- Guarantees:
  - read-only execution,
  - deterministic behavior based on provided context,
  - exceptions are isolated and converted into contract errors.

### 3) `introspection`
- Purpose: expose safe runtime metadata and diagnostics.
- Input: `ObservabilityContext`.
- Output: JSON-serializable DTO payload.
- Guarantees:
  - no mutable internal references,
  - no side effects,
  - DTO-only surface.

## Contract: Input / Output / Guarantees / Forbidden

### Input Contract
- Extensions receive **only** `ObservabilityContext`.
- `ObservabilityContext` is a frozen dataclass, preventing mutation by design.
- Context fields are metadata snapshots (`runtime_id`, `mode`, timestamps, schema version).

### Output Contract
- Extensions must return DTO-only payloads (`dict[str, JsonValue]`).
- Payloads are validated through JSON serialization (`json.dumps`).
- Non-serializable outputs are rejected as extension failures.

### Runtime Guarantees
- Extension execution is isolated per extension.
- Extension exceptions do not crash the engine path; they are captured as `extension_failed:<ExceptionType>`.
- Budget enforcement marks slow extensions as `budget_exceeded:<seconds>`.

### Forbidden by Contract
- Runtime lifecycle control (`init/start/shutdown/pause/resume/restart`).
- Strategy or business logic mutation.
- Persistence writes.
- Dynamic plugin loading.
- UI/configuration interaction.
- Returning mutable engine objects or non-DTO payloads.

## Scope Boundaries
In scope:
- status / health / introspection extension points,
- strict contracts,
- read-only behavior by design,
- contract-level tests.

Out of scope:
- runtime lifecycle control,
- strategy implementations,
- persistence logic,
- dynamic plugin loading,
- configuration UIs.
