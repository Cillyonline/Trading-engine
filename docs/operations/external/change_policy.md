# External Change Policy

## Purpose and Scope
This policy defines how external-facing contract changes are classified and communicated for documented contracts only. It is documentation-only guidance and does not change runtime behavior, APIs, CLI structure, or implementation details.

## 1) What Counts as a Breaking Change (External Contract Perspective)
A change is **breaking** when it can invalidate a client that correctly follows the current documented external contract.

Breaking changes include:
- Removing a documented endpoint, command, field, flag, response property, error code, or workflow step.
- Renaming documented external elements without preserving documented compatibility.
- Changing documented request/response shapes in an incompatible way (for example, required/optional status, type, allowed value set, or structural layout).
- Tightening documented validation, preconditions, or limits so that previously valid documented usage becomes invalid.
- Changing documented error semantics or status mapping in a way that breaks documented client handling expectations.
- Changing documented ordering, idempotency, or determinism guarantees where clients are allowed to rely on those guarantees.

## 2) Non-Breaking Change Categories
A change is **non-breaking** when it preserves compatibility for clients that rely on documented contracts.

Non-breaking categories include:
- Documentation clarifications that do not alter contract meaning.
- Additive extensions marked optional/non-required in the contract (for example, new optional fields or optional parameters).
- Internal implementation changes with no change to documented external behavior.
- Performance, observability, or operational improvements that do not change documented external contract semantics.
- New capabilities introduced in a way that does not alter existing documented behavior.

## 3) Undocumented Behavior Policy
Undocumented behavior is **not part of the external compatibility contract**.

Policy:
- Compatibility commitments apply to behavior explicitly documented as contract.
- Undocumented behavior may change without being treated as a breaking contract change.
- Once behavior is documented as contract, future compatibility classification follows this policy.

## 4) Pre-Versioning Compatibility Expectations
Before any formal versioning model is defined, compatibility is governed by documented external contracts.

Expectations:
- Avoid breaking documented contracts unless a change is explicitly communicated as breaking.
- Prefer additive and clarifying changes over incompatible contract edits.
- Evaluate changes against currently documented contract surfaces before release.

## 5) Documentation-Level Change Communication Expectations
When a contract-relevant change is made, documentation should communicate:
- The affected documented contract surface.
- Whether the change is breaking or non-breaking under this policy.
- Required client action (if any).
- Effective timing or rollout context where applicable.

This communication requirement is documentation-level only and does not define release tagging, branching, or automation processes.

## 6) Runtime/Implementation Boundary
This policy is descriptive and governance-oriented. It introduces no runtime guarantees beyond already documented contracts and has no direct execution or API implications.
