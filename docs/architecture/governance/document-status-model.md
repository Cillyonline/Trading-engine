# Canonical Document Status Model

## Document Status

- Class: Canonical
- Canonical Source(s): N/A (Class=Canonical)
- Rationale: This file is the authoritative source for the document status
  classification model used by governance-/roadmap-/audit-/status-relevant
  documents in this repository.

## Purpose

This document defines one canonical status model for governance-, roadmap-,
audit-, and status-relevant documentation.

The model provides:

- a fixed status vocabulary,
- deterministic classification rules,
- a mandatory intake rule for new status-relevant documents.

## Status Classes

### Canonical

The document is a source-of-truth authority for its scoped claim domain.
Canonical documents may define policy, lifecycle status, or governance gates.

### Derived

The document summarizes, indexes, or explains canonical content but does not set
authority. Derived documents must explicitly defer to canonical sources.

### Evidence

The document records verification, audit, runtime evidence, or compliance trace
material supporting a claim. Evidence does not define canonical policy/status by
itself.

### Deprecated

The document is retained for historical traceability but replaced by a newer
source. Deprecated documents must not be used to set current policy or status.

### Archived

The document is retained as inactive historical record. Archived documents are
outside active governance/update flow.

### Compatibility Alias

A compatibility path kept to preserve legacy links/consumer navigation. Alias
documents or paths must point to the current canonical location and must not
compete with canonical authority.

## Classification Rules

1. Every governance-/roadmap-/audit-/status-relevant document must have exactly
   one status class from this model.
2. Only `Canonical` documents may define authoritative status or governance
   outcomes.
3. `Derived`, `Evidence`, and `Compatibility Alias` documents must defer to one
   or more named canonical documents.
4. `Deprecated` and `Archived` documents are non-authoritative by definition.
5. A canonical document must never be labeled `Deprecated` or `Archived` while
   it remains an active source of truth.

## Canonical Authority Mapping (Current)

The following high-visibility sources are classified as `Canonical` for their
domains:

- `ROADMAP_MASTER.md` (master phase maturity/status authority)
- `docs/architecture/roadmap/execution_roadmap.md` (audited phase taxonomy)
- `docs/architecture/documentation_structure.md`
  (documentation ownership/navigation authority)
- `docs/architecture/governance/phase-5-exit-criteria.md`
  (phase-5 governance gate)
- `docs/releases/release_governance_contract.md`
  (release governance boundary)

## Sample Classification (Acceptance Test Trace)

Sample checks against this model:

| Document | Class | Why |
| --- | --- | --- |
| `ROADMAP_MASTER.md` | Canonical | Single authoritative in-repo source for phase maturity/status. |
| `docs/architecture/roadmap/cilly_trading_execution_roadmap_updated.md` | Derived | Snapshot/explanatory roadmap surface that must defer to `ROADMAP_MASTER.md` for phase maturity/status. |
| `docs/architecture/roadmap/execution_roadmap.md` | Canonical | Explicitly defines authoritative audited taxonomy/phase meaning. |
| `docs/architecture/audit/roadmap_compliance_report.md` | Evidence | Audits alignment; does not set canonical status authority. |
| `docs/architecture/phases/phase-37-status.md` | Derived | Per-phase status surface defers to master roadmap authority model. |
| `docs/index.md` | Derived | Navigation/index surface; must defer to canonical governance sources. |
| `docs/api/runtime_chart_data_contract.md` | Compatibility Alias | Legacy path kept for compatibility with canonical operations path. |

## Intake Rule For New Status-Relevant Documents

A new governance-/roadmap-/audit-/status-relevant document is allowed only if
its status class is explicitly declared in the document front matter section
`Document Status`.

Required header block:

```md
## Document Status
- Class: <Canonical|Derived|Evidence|Deprecated|Archived|Compatibility Alias>
- Canonical Source(s): <required unless Class=Canonical>
- Rationale: <short reason>
```

Review gate for PRs that add these documents:

1. `Document Status` block is present and uses one allowed class name exactly.
2. Non-canonical classes reference canonical source(s).
3. Wording does not promote derived/evidence/alias docs to canonical authority.
4. No active canonical file is reclassified as `Deprecated` or `Archived`.

## Compatibility Notes

This model is compatible with the current documentation structure:

- It preserves existing canonical ownership patterns.
- It allows derived/evidence surfaces to remain in place without mass
  reclassification.
- It supports legacy alias paths while keeping one canonical authority per claim.
