# External Error Semantics (CLI and API)

## Purpose and Scope

This document defines stable, external-facing error semantics for users of the CLI and API. It is intentionally high level and is documentation-only.

## Stable Failure Categories (External Perspective)

External failures are grouped into these stable categories:

1. Validation Failure
   - The request, command input, or parameters are invalid, incomplete, or inconsistent with expected input rules.
   - Typical examples include malformed input payloads, missing required fields, or unsupported argument combinations.

2. Authentication Failure
   - The request targets a protected API endpoint, but the caller does not present valid credentials for an authenticated principal.
   - Typical examples include missing credentials, malformed credentials, expired credentials, or any other condition where identity cannot be established.

3. Authorization Failure
   - The request targets a protected API endpoint, the caller is authenticated, and the caller's role is not permitted for that endpoint.
   - Typical examples include a `read_only` caller attempting to invoke an operator-only mutation or an `operator` caller attempting to invoke an owner-only control action.

4. Runtime Failure
   - The request or command was accepted as syntactically and structurally valid, but execution could not be completed due to operational conditions.
   - Typical examples include dependency unavailability, timeout conditions, or other execution-time interruptions.

These categories are intended as a stable contract at the CLI/API behavior level.

## Validation vs Authentication vs Authorization vs Runtime

The distinction is:

- Validation errors are about input acceptability.
- Authentication errors are about whether the caller identity is established.
- Authorization errors are about whether the established caller identity is permitted to use the endpoint.
- Runtime errors are about execution outcome after an acceptable request is allowed to run.

## CLI Error Signaling Semantics (High Level)

For CLI consumers:

- CLI invocations signal failure through a non-successful process exit.
- Human-readable diagnostics may be emitted to help users understand the failure category and immediate cause.
- Validation, authentication, authorization, and runtime failures are all surfaced as failures while preserving their conceptual distinction for interpretation and handling.

This document does not define or modify specific numeric exit-code assignments.

## API Error Signaling Semantics (High Level)

For API consumers:

- API failures are signaled through non-success HTTP responses.
- Response bodies may include structured error information intended for diagnostics and client handling.
- Validation, authentication, authorization, and runtime failures remain conceptually distinct categories at the API contract level.

## Protected Operator Endpoint Semantics

For the protected operator-facing endpoints listed in `docs/operations/access-policy.md`, once authorization enforcement is implemented:

- `401 Unauthorized` is the required response when the caller is not authenticated.
- `403 Forbidden` is the required response when the caller is authenticated but does not hold the minimum allowed role for the endpoint.
- `401` and `403` responses must not perform endpoint side effects.
- Endpoint-specific validation and runtime failures remain separate from authentication and authorization failures.

## Error Details That Are Not Guaranteed

Unless explicitly documented elsewhere, the following are not guaranteed to be stable:

- Exact wording, phrasing, or localization of human-readable error messages.
- Internal exception/type names, stack traces, and implementation-specific diagnostics.
- Ordering, formatting, or incidental fields in verbose/debug output.
- Correlation or trace identifiers and low-level operational metadata.
- Any undocumented error payload fields beyond the stable external category semantics described here.

Consumers should rely on documented API and CLI contracts rather than incidental message text or internal implementation details.

## References and Alignment

- `docs/operations/access-policy.md` is the authoritative reference for current protected operator-facing API endpoint permissions.
- `docs/operations/interfaces/cli_contract.md` is the authoritative reference for concrete CLI exit-code definitions.
- This document defines stable external error categories and the required `401` versus `403` semantics for covered operator-facing API endpoints.

## Non-Goals

- No new runtime behavior is implemented by this document.
- No authentication or authorization middleware is introduced by this document.
- No new CLI exit codes are introduced by this document.
- No internal exception hierarchy is changed by this document.
