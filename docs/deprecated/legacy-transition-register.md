# Legacy Transition Register

## Document Status
- Class: Derived
- Canonical Source(s): docs/archive/archive-deprecation-standard.md
- Rationale: This register prepares and tracks first safe deprecation candidates
  without deleting historical documentation.

## Purpose

Prepare an initial, low-risk deprecation path for clearly uncertain legacy
compatibility documents while preserving traceability.

## Initial Candidates

| Legacy path | Class | Superseded by | Navigation role | Status |
| --- | --- | --- | --- | --- |
| `docs/api/public_api_boundary.md` | Deprecated | `docs/operations/api/public_api_boundary.md` | No active-first navigation required | Prepared |
| `docs/api/runtime_chart_data_contract.md` | Deprecated | `docs/operations/api/runtime_chart_data_contract.md` | Compatibility alias retained | Prepared |
| `docs/ui/phase-39-test-plan.md` | Deprecated | `docs/operations/ui/phase-39-test-plan.md` | Compatibility alias retained | Prepared |

## Chain Check (Current)

All listed legacy paths have direct successor targets under `docs/operations/**`
and currently form one-hop successor chains.

## Navigation Check (Current)

- Active API and UI sections in `docs/index.md` already prefer
  `docs/operations/**`.
- Legacy paths are retained only for compatibility references.
