# Execution Roadmap – Canonical Source of Truth

Status: Authoritative  
Scope: Phases 17b, 23, 24, 27, 25–31  
Owner: Governance  

## Purpose
One canonical in-repo roadmap artifact that defines phase goals and acceptance boundaries.

## How to Use
- This file is the authoritative source for phase definitions.
- Issues/PRs should reference the relevant phase.
- Acceptance evidence requirements must be satisfied for phase completion.

---

## Phase 17b

### Goal
Define and track the Owner Dashboard phase based on repository-verified artifacts and known documentation/runtime boundary conditions.

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
> docs/phases/phase-23-status.md

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

## Phase 24

### Goal
Define and track Paper Trading Runtime status from repository-verified implementation and documentation evidence.

### Explicit Deliverables
- Paper-trading simulator artifact in engine code.
- Tests validating paper-trading simulator behavior.
- Documentation references that describe phase runtime status.

### Explicitly Out of Scope
- Declaring full alignment while documentation still describes paper trading as unavailable.
- Expanding scope beyond paper-trading runtime status/evidence alignment.

### Acceptance Evidence Requirements
- Simulator and related tests remain present and passing for phase-scoped behavior.
- Documentation is updated to align with verified simulator state before closure.
- Phase 24 PRs/issues cite concrete repository files for implementation and docs alignment.

---

## Phase 27

### Goal
Explicitly distinguish risk-related artifacts from a standalone Risk Framework implementation.

> Governance Note  
> The implementation status of Phase 27 is explicitly documented in:  
> docs/phases/phase-27-status.md

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

---

## Phases 25–31

### Phase 25

#### Goal
Define Phase 25 status from available repository evidence.

#### Explicit Deliverables
- Explicit status declaration: phase-tagged artifacts not confirmed in repository.

#### Explicitly Out of Scope
- Claiming Phase 25 implementation without repository-verified phase-mapped artifacts.

#### Acceptance Evidence Requirements
- Any status change is supported by repository-verifiable phase-mapped code/docs/tests and linked issue/PR evidence.

### Phase 26

#### Goal
Define Phase 26 status from available repository evidence.

#### Explicit Deliverables
- Explicit status declaration: phase-tagged artifacts not confirmed in repository.

#### Explicitly Out of Scope
- Claiming Phase 26 implementation without repository-verified phase-mapped artifacts.

#### Acceptance Evidence Requirements
- Any status change is supported by repository-verifiable phase-mapped code/docs/tests and linked issue/PR evidence.

### Phase 27

#### Goal
Define Phase 27 status from available repository evidence within the 25–31 phase block.

#### Explicit Deliverables
- Explicit status declaration: phase-tagged artifacts not confirmed in repository for the broader 25–31 set.
- Refer to the dedicated Phase 27 section above for framework-specific status details.

#### Explicitly Out of Scope
- Reclassifying Phase 27 as implemented within the 25–31 block without framework-level repository evidence.

#### Acceptance Evidence Requirements
- Any status change is supported by repository-verifiable phase-mapped code/docs/tests and linked issue/PR evidence.

### Phase 28

#### Goal
Define Phase 28 status from available repository evidence.

#### Explicit Deliverables
- Explicit status declaration: phase-tagged artifacts not confirmed in repository.

#### Explicitly Out of Scope
- Claiming Phase 28 implementation without repository-verified phase-mapped artifacts.

#### Acceptance Evidence Requirements
- Any status change is supported by repository-verifiable phase-mapped code/docs/tests and linked issue/PR evidence.

### Phase 29

#### Goal
Define Phase 29 status from available repository evidence.

#### Explicit Deliverables
- Explicit status declaration: phase-tagged artifacts not confirmed in repository.

#### Explicitly Out of Scope
- Claiming Phase 29 implementation without repository-verified phase-mapped artifacts.

#### Acceptance Evidence Requirements
- Any status change is supported by repository-verifiable phase-mapped code/docs/tests and linked issue/PR evidence.

### Phase 30

#### Goal
Define Phase 30 status from available repository evidence.

#### Explicit Deliverables
- Explicit status declaration: phase-tagged artifacts not confirmed in repository.

#### Explicitly Out of Scope
- Claiming Phase 30 implementation without repository-verified phase-mapped artifacts.

#### Acceptance Evidence Requirements
- Any status change is supported by repository-verifiable phase-mapped code/docs/tests and linked issue/PR evidence.

### Phase 31

#### Goal
Define Phase 31 status from available repository evidence.

#### Explicit Deliverables
- Explicit status declaration: phase-tagged artifacts not confirmed in repository.

#### Explicitly Out of Scope
- Claiming Phase 31 implementation without repository-verified phase-mapped artifacts.

#### Acceptance Evidence Requirements
- Any status change is supported by repository-verifiable phase-mapped code/docs/tests and linked issue/PR evidence.
