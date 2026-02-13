# External Error Semantics (CLI and API)

## Purpose and Scope

This document defines **stable, external-facing error semantics** for users of the CLI and API.
It is intentionally high level and is **documentation-only**.

## Stable Failure Categories (External Perspective)

External failures are grouped into these stable categories:

1. **Validation Failure**
   - The request, command input, or parameters are invalid, incomplete, or inconsistent with expected input rules.
   - Typical examples include malformed input payloads, missing required fields, or unsupported argument combinations.

2. **Runtime Failure**
   - The request or command was accepted as syntactically/structurally valid, but execution could not be completed due to operational conditions.
   - Typical examples include dependency unavailability, timeout conditions, or other execution-time interruptions.

These categories are intended as a stable contract at the CLI/API behavior level.

## Validation vs. Runtime Errors

The distinction is:

- **Validation errors** occur **before successful execution can begin** because the supplied input is not acceptable.
- **Runtime errors** occur **during or after execution begins** when a valid request cannot be completed.

In short: validation is about **input acceptability**; runtime is about **execution outcome**.

## CLI Error Signaling Semantics (High Level)

For CLI consumers:

- CLI invocations signal failure through a **non-successful process exit**.
- Human-readable diagnostics may be emitted to help users understand the failure category and immediate cause.
- Validation and runtime failures are both surfaced as failures, while preserving the validation-vs-runtime conceptual distinction for interpretation and handling.

This document does not define or modify specific numeric exit-code assignments.

## API Error Signaling Semantics (High Level)

For API consumers:

- API failures are signaled through **non-success HTTP responses**.
- Response bodies may include structured error information intended for diagnostics and client handling.
- Validation and runtime failures remain conceptually distinct categories at the API contract level.

This document does not define or modify specific HTTP status-to-error mappings.

## Error Details That Are Not Guaranteed

Unless explicitly documented elsewhere, the following are **not guaranteed to be stable**:

- Exact wording, phrasing, or localization of human-readable error messages.
- Internal exception/type names, stack traces, and implementation-specific diagnostics.
- Ordering, formatting, or incidental fields in verbose/debug output.
- Correlation/trace identifiers and low-level operational metadata.
- Any undocumented error payload fields beyond the stable external category semantics described here.

Consumers should rely on documented API/CLI contracts rather than incidental message text or internal implementation details.

## References and Alignment

- `docs/interfaces/cli_contract.md` is the authoritative reference for concrete CLI exit-code definitions.
- This document defines only conceptual, stable failure categories for external interpretation.
- This document does not redefine CLI exit codes.

## Non-Goals

- No new error codes are introduced.
- No changes to HTTP status mappings.
- No runtime logic changes.
- No changes to internal exception hierarchies.
