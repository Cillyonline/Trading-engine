# Phase 23 - Website-Facing /ui Workflow Consolidation

## Status
PARTIALLY IMPLEMENTED

## Taxonomy Alignment
Phase 23 means bounded website-facing workflow consolidation under the canonical `/ui` shell in this repository revision.

## Canonical Bounded Message
Phase 23 is `PARTIALLY IMPLEMENTED` because one coherent bounded evidence set now defines one canonical website-facing workflow shell at `/ui`.

The consolidated IA contract is intentionally non-live and does not imply trader validation or operational readiness.
Canonical product-surface authority and non-inference status separation are defined in:
- `docs/operations/ui/product-surface-authority-contract.md`

## Authoritative Bounded Scope
Phase 23 in this revision is the repository-verifiable phase for:
- one canonical `/ui` workflow shell
- one bounded primary navigation contract for website-facing workflow entry
- explicit non-live boundaries that prevent readiness inference from IA consolidation
- explicit separation between technical implementation, trader validation, and operational readiness statuses

This scope does not introduce new product surfaces, live execution claims, or architecture expansion.

## Minimum Repo-Verifiable Evidence Contract
A Phase 23 claim in this repository revision requires all evidence classes below for the same canonical `/ui` shell.

### Required evidence class 1: bounded IA contract
The repository must contain documentation that:
- identifies `/ui` as the canonical website-facing workflow entrypoint
- defines the bounded primary navigation workflow contract
- states explicit non-live and non-readiness boundaries

### Required evidence class 2: runtime/UI implementation artifact
The repository must contain implementation artifacts that enforce the same bounded shell claim:
- `src/ui/index.html` (canonical shell and navigation markers)
- static mount in `src/api/main.py` at `/ui`

### Required evidence class 3: verification artifact
The repository must contain tests that validate canonical ownership and bounded entrypoints:
- `src/api/test_research_dashboard_surface.py`
- `src/api/test_operator_workbench_surface.py`
- `tests/test_ui_runtime_browser_flow.py`
- `tests/test_phase23_research_dashboard_contract.py`

## Classification Rule
- `NOT IMPLEMENTED`: any required evidence class is missing, inconsistent, or points to multiple canonical website-facing entry surfaces
- `PARTIALLY IMPLEMENTED`: all required classes exist, but broader product-surface expansion remains intentionally out of scope
- `IMPLEMENTED`: all required classes exist and support complete bounded scope being claimed, without readiness inference

## Explicit Phase Boundaries
Phase 23 consolidation in this revision does not claim:
- live trading
- broker execution
- production-readiness
- trader-readiness
- operational readiness
- promotion of `frontend/` to authoritative product surface

Adjacency to Phase 39 charting, Phase 40 desk wording, or broader UX ideas is not evidence for this bounded Phase 23 claim.

## Verified Repository Evidence
The current repository review confirms one bounded evidence set for canonical `/ui` ownership:
- bounded contract documentation:
  - `docs/operations/ui/phase-23-research-dashboard-contract.md`
- runtime/UI artifacts:
  - `src/ui/index.html`
  - static mount in `src/api/main.py` at `/ui`
- verification artifacts:
  - `src/api/test_research_dashboard_surface.py`
  - `src/api/test_operator_workbench_surface.py`
  - `tests/test_ui_runtime_browser_flow.py`
  - `tests/test_phase23_research_dashboard_contract.py`

## OPS-P56 Non-Interference
This Phase 23 consolidation contract does not replace or widen operational run logging scope.

`OPS-P56: Start bounded staged paper-trading runbook and evidence log #914` remains the single operational run log issue.

## Explicit Declaration
As of this revision, one repository-verifiable canonical `/ui` website-facing workflow shell is confirmed under bounded non-live scope.
Phase 23 is therefore PARTIALLY IMPLEMENTED under this consolidation contract.
