# Canonical /ui Product-Surface Authority Contract

## Purpose
Define canonical website-facing product-surface authority and strict non-inference rules for readiness semantics.

This contract is bounded to repository documentation and verification evidence.

## Canonical Product-Surface Authority
- Canonical website-facing product-surface authority: `/ui`
- Runtime source of authority: `src/ui/index.html` mounted by `src/api/main.py`
- Authority classification: canonical for bounded website-facing workflow semantics only

`/ui` is the only canonical website-facing product-surface authority in this repository revision.

## Non-Authoritative `frontend/` Status
- `frontend/` is non-authoritative for website-facing product-surface authority in this repository revision.
- `frontend/` may contain exploratory or parallel implementation artifacts, but those artifacts are not authority evidence.
- `frontend/` can only become authoritative through explicit governance promotion documented in repository governance artifacts.

## Non-Inference Rules
The repository uses three distinct status classes. Evidence in one class must not be inferred as evidence in another class.

### 1) Technical Implementation Status
Defined by repository-verifiable implementation and test evidence for bounded `/ui` behavior.

Technical implementation status does not imply:
- trader validation status
- operational readiness status
- live trading readiness
- broker execution readiness
- production readiness

### 2) Trader Validation Status
Defined by explicit trader validation evidence under trader-owned validation process.

Trader validation status does not imply:
- technical implementation completion in unrelated surfaces
- operational readiness status
- live trading readiness
- broker execution readiness
- production readiness

### 3) Operational Readiness Status
Defined by explicit operational governance evidence and runbook-gated acceptance criteria.

Operational readiness status does not imply:
- live trading authorization
- broker integration scope completion
- production readiness declarations outside explicit governance contracts

## Language Discipline
Documentation for `/ui` and related product-surface contracts must use strict wording that avoids readiness inference.

Required semantics:
- `/ui` is canonical authority for bounded website-facing workflow semantics.
- `frontend/` is non-authoritative unless governance promotes it.
- Technical implementation, trader validation, and operational readiness are separate status classes.

Prohibited implication patterns:
- treating technical UI implementation as trader validation evidence
- treating technical UI implementation as operational readiness evidence
- treating operational workflow documentation as live trading or broker readiness evidence
- using bounded `/ui` evidence as a production-readiness declaration

## Alignment References
- `docs/operations/ui/phase-23-research-dashboard-contract.md`
- `docs/architecture/ui-runtime-phase-ownership-boundary.md`
- `docs/architecture/phases/phase-23-status.md`

