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
  - deterministic behavior relative to the provided `ObservabilityContext`,
  - exceptions are isolated and converted into structured contract errors.

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
- `ObservabilityContext` is immutable (`@dataclass(frozen=True)`), read-only by design.
- Context fields are metadata snapshots (`runtime_id`, `mode`, timestamps, schema version).
- Extensions must be deterministic relative to the provided `ObservabilityContext`.

### Output Contract
- Extensions must return DTO-only payloads (`dict[str, JsonValue]`).
- Payloads are validated through JSON serialization (`json.dumps`).
- Non-serializable or non-DTO outputs are rejected and surfaced as a structured extension failure.

### Error Contract (Structured)
- `error_code`: `"extension_failed" | "budget_exceeded" | None`
- `error_detail`:
  - when `error_code == "extension_failed"`: exception type name (for example `TypeError`, `RuntimeError`),
  - when `error_code == "budget_exceeded"`: `"elapsed_seconds=<float>"`,
  - otherwise `None`.

### Runtime Guarantees
- Extension execution is isolated per extension.
- Extension exceptions do not crash the engine path.
- Budget enforcement includes extension execution time **and** JSON serialization validation time.
- Slow extensions are marked with:
  - `error_code="budget_exceeded"`
  - `error_detail="elapsed_seconds=<float>"`

### Registration Guarantees
- Extension names must be unique per extension point.
- Registering a duplicate extension name for the same extension point raises `ValueError`.

### Deterministic Context Construction
- `build_observability_context` supports deterministic usage with `now: datetime | None = None`.
- If `now` is provided, it is used for both `updated_at` and `now` fields.
- If `now` is `None`, current UTC time is used.

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
