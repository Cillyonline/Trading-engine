# Execution Roadmap - Authoritative Phase Taxonomy

Status: Authoritative  
Scope: Audited phase taxonomy for Phases 5, 16, 17, 17b, 23, 25, 26, and 27  
Owner: Governance  

## Purpose
This file is the single authoritative in-repo source for audited phase-number meanings.

## How to Use
- Use this file to resolve the meaning of an audited phase number before relying on any secondary roadmap, index, or audit artifact.
- Treat secondary documents as navigation or status evidence only unless they explicitly defer to this file.
- If a phase is marked here as "no authoritative in-repo meaning located", do not infer a meaning from neighboring phases or legacy headings.

---

## Audited Phase Taxonomy

| Phase | Authoritative meaning | Source trace |
|-------|-----------------------|--------------|
| Phase 5 | External Ready exit gate | `docs/governance/phase-5-exit-criteria.md` |
| Phase 16 | No authoritative in-repo phase taxonomy artifact was located during the audit. | This roadmap entry is the governing clarification for audited artifacts. |
| Phase 17 | Consumer Interfaces and Usage Patterns umbrella phase | Legacy index references align to this taxonomy; Phase 17b is the audited Owner Dashboard sub-phase. |
| Phase 17b | Owner Dashboard | Verified by this roadmap entry and supporting runtime/documentation evidence. |
| Phase 23 | Research Dashboard | `docs/phases/phase-23-status.md` |
| Phase 25 | Strategy Lifecycle Management | `docs/phases/phase_25_strategy_lifecycle.md` |
| Phase 26 | No authoritative in-repo phase taxonomy artifact was located during the audit. | This roadmap entry is the governing clarification for audited artifacts. |
| Phase 27 | Risk Framework | `docs/phases/phase-27-status.md` |

## Taxonomy Guardrails
- Phase 17 and Phase 17b are not interchangeable: Phase 17 is the umbrella phase, and Phase 17b is the Owner Dashboard sub-phase.
- Phase 27 and Phase 27b are not interchangeable: Phase 27 is Risk Framework taxonomy; Phase 27b remains a distinct Pipeline Enforcement Layer artifact.
- Phase 25 and Phase 26 must not be grouped into a shared replacement meaning. Phase 25 is defined above, while Phase 26 remains unmapped in current authoritative in-repo taxonomy.
- This document establishes taxonomy only. Implementation-status corrections remain scoped to the relevant status artifacts and follow-on issues.

---

## Phase 17b

### Goal
Define and track the Owner Dashboard sub-phase based on repository-verified artifacts and known documentation/runtime boundary conditions.

### Explicit Deliverables
- Backend-served Owner Dashboard surface at `/ui` via FastAPI static mount.
- Owner Dashboard HTML marker (`<title>Owner Dashboard</title>`) in the served UI.
- Manual trigger endpoint `POST /analysis/run` associated with owner-operator flow.
- Evidence-backed documentation and tests for the above artifacts.

### Explicitly Out of Scope
- Treating `/owner` as backend-implemented without a verified backend route definition.
- Claiming Phase 17b as fully implemented while route documentation mismatch remains unresolved.

### Acceptance Evidence Requirements
- Repository evidence in code and tests confirms `/ui` serving behavior and Owner Dashboard marker.
- Repository evidence confirms `POST /analysis/run` exists and is tested.
- Documentation references are present and aligned with verified backend route behavior.

---

## Phase 23

### Goal
Define Phase 23 status using only repository-verified evidence.

> Governance Note  
> The implementation status of Phase 23 is explicitly documented in:  
> `docs/phases/phase-23-status.md`

### Explicit Deliverables
- Explicit status declaration: Research Dashboard implementation artifact not confirmed in repository.
- Phase 23 tracking issue/PR references this canonical roadmap entry when changing status.

### Explicitly Out of Scope
- Claiming a Research Dashboard implementation without verified code, docs, or tests.
- Inferring hidden or external artifacts as in-repo completion evidence.

### Acceptance Evidence Requirements
- Any status change from "Not Implemented" is backed by repository-verifiable code/docs/tests.
- PR/issue history explicitly maps new artifacts to Phase 23.

---

## Phase 27

### Goal
Explicitly distinguish risk-related artifacts from a standalone Risk Framework implementation.

> Governance Note  
> The implementation status of Phase 27 is explicitly documented in:  
> `docs/phases/phase-27-status.md`

### Verified Existing Artifacts
- Risk-related configuration fields exist.
- Risk-related metrics and tests exist.

### Framework Status
No standalone Phase 27 Risk Framework module was verified.

### Explicitly Out of Scope
- Treating config fields or metrics as proof of a completed framework.
- Declaring framework completion without standalone artifact evidence.

### Acceptance Evidence Requirements
- Standalone repository-verifiable framework module(s).
- Explicit policy logic definition.
- Documentation and tests mapped directly to Phase 27 framework scope.
