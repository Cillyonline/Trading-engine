# Execution Roadmap - Authoritative Phase Taxonomy

Status: Authoritative  
Scope: Audited phase taxonomy for Phases 5, 16, 17, 17b, 23, 25, 26, 27, 37, and 38  
Owner: Governance  

## Purpose
This file is the single authoritative in-repo source for audited phase-number meanings.

## Authority Relationship
- This file governs the meaning of the audited phase numbers listed below.
- `ROADMAP_MASTER.md` is the single authoritative in-repo source for phase maturity/status labels and status-change decisions.
- `docs/governance/professional-trading-capability-target.md` is the canonical capability-direction anchor for issue prioritization and steering.
- This file does not authoritatively set phase maturity/status labels. Any status wording here, in a per-phase artifact, or in an index must defer to the master roadmap for canonical maturity/status.
- The master roadmap may summarize broader sequencing and implementation-status context, but it must defer to this file for audited phase meaning.
- If wording in a secondary roadmap, index, or audit artifact conflicts with the audited phase meanings defined here, this file controls the taxonomy interpretation.

## Status Update Rule
- Taxonomy updates follow this file.
- Phase maturity/status updates follow `ROADMAP_MASTER.md`.
- Per-phase status artifacts, audit reports, and index/navigation documents may provide evidence, scoped detail, or traceability, but they do not become canonical status sources unless the master roadmap is updated to reflect the change.
- Reviewers should reject status changes that update a secondary document without also updating the master roadmap.

## How to Use
- Use this file to resolve the meaning of an audited phase number before relying on any secondary roadmap, index, or audit artifact.
- Use `docs/governance/professional-trading-capability-target.md` as the primary steering input for capability-priority issue derivation.
- Do not use this taxonomy file by itself as a primary issue-priority mechanism.
- Treat secondary documents as navigation or status evidence only unless they explicitly defer to this file for taxonomy and to the master roadmap for phase maturity/status.
- If a phase is marked here as "no authoritative in-repo meaning located", do not infer a meaning from neighboring phases or legacy headings.

---

## Audited Phase Taxonomy

| Phase | Authoritative meaning | Source trace |
|-------|-----------------------|--------------|
| Phase 5 | External Ready exit gate | `docs/architecture/governance/phase-5-exit-criteria.md` |
| Phase 16 | No authoritative in-repo phase taxonomy artifact was located during the audit. | This roadmap entry is the governing clarification for audited artifacts. |
| Phase 17 | Consumer Interfaces and Usage Patterns umbrella phase | Legacy index references align to this taxonomy; Phase 17b is the audited Owner Dashboard sub-phase. |
| Phase 17b | Owner Dashboard | Verified by this roadmap entry and supporting runtime/documentation evidence. |
| Phase 23 | Research Dashboard | `docs/architecture/phases/phase-23-status.md` |
| Phase 25 | Strategy Lifecycle Management | `docs/architecture/phases/phase_25_strategy_lifecycle.md` |
| Phase 26 | No authoritative in-repo phase taxonomy artifact was located during the audit. | This roadmap entry is the governing clarification for audited artifacts. |
| Phase 27 | Risk Framework | `docs/architecture/phases/phase-27-status.md` |
| Phase 37 | Watchlist Engine | `docs/architecture/phases/phase-37-status.md` |
| Phase 38 | Market Data Integration | `docs/architecture/phases/phase-38-status.md` |

## Taxonomy Guardrails
- Phase 17 and Phase 17b are not interchangeable: Phase 17 is the umbrella phase, and Phase 17b is the Owner Dashboard sub-phase.
- Phase 27 and Phase 27b are not interchangeable: Phase 27 is Risk Framework taxonomy; Phase 27b remains a distinct Pipeline Enforcement Layer artifact.
- Phase 25 and Phase 26 must not be grouped into a shared replacement meaning. Phase 25 is defined above, while Phase 26 remains unmapped in current authoritative in-repo taxonomy.
- This document establishes taxonomy only. Canonical implementation-status corrections must be made in `ROADMAP_MASTER.md`, with any supporting per-phase artifacts updated as derived evidence.

---

## Phase 17b

### Goal
Define and track the Owner Dashboard sub-phase based on repository-verified artifacts and known documentation/runtime boundary conditions.

### Explicit Deliverables
- Backend-served Owner Dashboard surface at `/ui` via FastAPI static mount.
- Repository-served `/ui` runtime artifact from `src/ui/index.html`.
- Manual trigger endpoint `POST /analysis/run` associated with owner-operator flow.
- Evidence-backed documentation and tests for the above artifacts.

### Explicitly Out of Scope
- Treating `/owner` as backend-implemented without a verified backend route definition.
- Claiming Phase 17b as fully implemented while route documentation mismatch remains unresolved.

### Acceptance Evidence Requirements
- Repository evidence in code and tests confirms `/ui` serving behavior and the current runtime artifact.
- Repository evidence confirms `POST /analysis/run` exists and is tested.
- Documentation references are present and aligned with verified backend route behavior.

---

## Phase 23

### Goal
Define the authoritative audited taxonomy meaning of Phase 23 as
`Research Dashboard`.

> Governance Note  
> Canonical phase maturity/status for Phase 23 is governed only by
> `ROADMAP_MASTER.md`.  
> `docs/architecture/phases/phase-23-status.md` is a derived evidence artifact.

### Explicit Deliverables
- Phase 23 references use the canonical meaning `Research Dashboard`.
- Issues and PRs that mention Phase 23 map scope wording to this taxonomy.

### Explicitly Out of Scope
- Setting canonical phase maturity/status inside this taxonomy file.
- Using phase-number progression as a substitute for capability-impact steering.

### Acceptance Evidence Requirements
- Secondary artifacts that mention Phase 23 defer status to
  `ROADMAP_MASTER.md`.
- Issue and PR history keeps `Research Dashboard` wording aligned to this
  taxonomy entry.

---

## Phase 27

### Goal
Define the authoritative audited taxonomy meaning of Phase 27 as
`Risk Framework`.

> Governance Note  
> Canonical phase maturity/status for Phase 27 is governed only by
> `ROADMAP_MASTER.md`.  
> `docs/architecture/phases/phase-27-status.md` is a derived evidence artifact.

### Explicitly Out of Scope
- Setting canonical phase maturity/status inside this taxonomy file.
- Collapsing Phase 27 taxonomy into Phase 27b or other risk-adjacent artifacts.

### Acceptance Evidence Requirements
- Secondary artifacts that mention Phase 27 defer status to
  `ROADMAP_MASTER.md`.
- Issue and PR wording preserves the taxonomy distinction between Phase 27
  (`Risk Framework`) and Phase 27b (Pipeline Enforcement Layer).

---

## Phase 37

### Goal
Define Phase 37 using the bounded watchlist workflow that is verifiable in the repository.

> Governance Note  
> The implementation status of Phase 37 is explicitly documented in:  
> `docs/architecture/phases/phase-37-status.md`

### Verified Existing Artifacts
- SQLite-backed watchlist persistence and CRUD behavior.
- Watchlist CRUD API endpoints and deterministic response models.
- Snapshot-only watchlist execution with deterministic ranking output and isolated symbol failures.
- Backend-served `/ui` watchlist management and execution markers tied to the implemented API routes.

### Explicitly Out of Scope
- Claiming Phase 37 as market-data expansion, charting, alerts, or trading-desk completion.
- Treating Phase 37 evidence as proof of later dashboard/product phases.

### Acceptance Evidence Requirements
- Repository-verifiable code and tests exist for watchlist persistence, CRUD, execution, ranking, and `/ui` watchlist behavior.
- Roadmap and runtime-facing docs describe the watchlist workflow as bounded Phase 37 scope rather than as later-phase product completion.

---

## Phase 38

### Goal
Define Phase 38 using a bounded contract that separates direct provider adapter presence from deterministic runtime-safe usage claims.

> Governance Note  
> The implementation status of Phase 38 is explicitly documented in:  
> `docs/architecture/phases/phase-38-status.md`

### Verified Existing Artifacts
- Direct provider-facing loader functions exist in `src/cilly_trading/engine/data.py`.
- Provider registry/failover contract artifacts exist in `src/cilly_trading/engine/data/market_data_provider.py`.
- Snapshot-only API behavior and deterministic/non-deterministic boundary language is documented in `docs/operations/api/usage_contract.md`.

### Explicitly Out of Scope
- Treating direct adapter presence as proof of production-ready runtime integration.
- Claiming broker integration, live feeds, or websocket delivery under Phase 38.

### Acceptance Evidence Requirements
- Repository status wording must not claim direct provider integrations are absent where code exists.
- Runtime-safe claims must include deterministic snapshot-bound usage evidence, not only adapter-presence evidence.
