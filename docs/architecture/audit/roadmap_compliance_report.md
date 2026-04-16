# Roadmap Compliance Report

## 1. Executive Summary

This audit is based only on repository-verifiable evidence (code, tests, endpoints, and documentation files).

The authoritative in-repo source for audited phase taxonomy is `docs/architecture/roadmap/execution_roadmap.md`. This report now defers to that roadmap for phase-number meanings and uses this document only for audit findings and traceability.
Canonical phase maturity/status labels are governed only by `ROADMAP_MASTER.md`.

Owner Dashboard is verifiably backend-served at `/ui` via FastAPI `app.mount("/ui", StaticFiles(..., html=True), ...)` and HTML marker `<title>Owner Dashboard</title>`.

Paper-trading simulator code and tests are present, and the repository documentation now describes the simulator as an implemented engine-level capability with explicit non-live boundaries.

Strategy Lifecycle Management and Risk Framework both have repository-verifiable implementation artifacts; earlier status wording that framed them as pending or absent was outdated.

No live trading endpoint, broker integration runtime, or AI decision engine implementation was verified.

Snapshot runtime execution capability is implemented in-repo, while scheduling remains external and no in-repo scheduler runtime was verified.

Documentation and implementation are aligned for the audited paper-trading and owner-dashboard surfaces, with remaining caution focused on still-unimplemented roadmap phases rather than stale contradictions.

**Current overall alignment assessment (audit snapshot, non-canonical):** **Aligned for audited active surfaces**

---

## 2. Audited Phase Taxonomy Trace

| Phase | Authoritative meaning | Trace path | Audit note |
|-------|-----------------------|------------|------------|
| Phase 5 | External Ready exit gate | `docs/architecture/governance/phase-5-exit-criteria.md` | Governance gate, not reassessed for implementation status in this report. |
| Phase 16 | No authoritative in-repo phase taxonomy artifact located | `docs/architecture/roadmap/execution_roadmap.md` | Reviewers should treat the phase as unmapped unless a future governance artifact establishes it. |
| Phase 17 | Consumer Interfaces and Usage Patterns umbrella phase | `docs/architecture/roadmap/execution_roadmap.md` | Distinct from Phase 17b; secondary index links are navigation only. |
| Phase 17b | Owner Dashboard | `docs/architecture/roadmap/execution_roadmap.md` | This report's Owner Dashboard findings map only to Phase 17b. |
| Phase 23 | Research Dashboard | `docs/architecture/roadmap/execution_roadmap.md` | Taxonomy authority remains with the roadmap; `docs/architecture/phases/phase-23-status.md` is a derived evidence artifact. |
| Phase 25 | Strategy Lifecycle Management | `docs/architecture/roadmap/execution_roadmap.md` | Taxonomy authority remains with the roadmap; `docs/architecture/phases/phase_25_strategy_lifecycle.md` is a derived evidence artifact aligned to verified lifecycle modules and tests. |
| Phase 26 | No authoritative in-repo phase taxonomy artifact located | `docs/architecture/roadmap/execution_roadmap.md` | Reviewers should not infer a Phase 26 meaning from adjacent roadmap blocks. |
| Phase 27 | Risk Framework | `docs/architecture/roadmap/execution_roadmap.md` | Taxonomy authority remains with the roadmap; `docs/architecture/phases/phase-27-status.md` is a derived evidence artifact, and Phase 27 remains distinct from Phase 27b Pipeline Enforcement Layer artifacts. |

---

## 3. Roadmap Phase Matrix (Audit Snapshot)

| Phase | Audit observation (non-canonical snapshot) | Evidence | Notes |
|-------|--------|----------|-------|
| Phase 17b - Owner Dashboard | Implemented | Backend UI mount in `src/api/main.py` (`app.mount("/ui", StaticFiles(..., html=True), name="ui")`); HTML marker in `src/ui/index.html` (`<title>Owner Dashboard</title>`); tests in `tests/health_endpoint.py`; manual trigger endpoint `POST /analysis/run` in `src/api/main.py`; test in `tests/test_api_manual_analysis_trigger.py`; documentation in `docs/operations/ui/owner_dashboard.md` and `docs/index.md`. | `/ui` is confirmed backend-served. `/owner` is documented only as a frontend development route and not as a runtime backend route. |
| Hourly Snapshot Runtime | Partially Implemented | `docs/operations/runtime/snapshot_runtime.md` declares in-repo execution capability and external scheduling boundary; `docs/operations/interfaces/batch_execution.md` states no scheduler implementation; no scheduler/cron endpoint verified in `src/api/main.py`. | Runtime execution capability exists in-repo; hourly scheduling is external and not provided by this repository. |
| Phase 24 - Paper Trading Runtime | Implemented | Simulator in `src/cilly_trading/engine/paper_trading.py`; tests in `tests/test_paper_trading_simulator.py`; documentation in `docs/operations/paper-trading.md`, `docs/operations/runbook.md`, `docs/architecture/phase-9-exit.md`, and `docs/getting-started/repo-snapshot.md`. | Engine-level simulation exists and is now documented consistently as non-live and non-broker-integrated. |
| Phase 23 - Research Dashboard | Not Implemented | No repository-verifiable code, tests, or runtime docs were confirmed beyond roadmap/status tracking references. | No direct implementation artifact was found for the audited phase. |
| Phase 25 - Strategy Lifecycle Management | Implemented In Repository | Lifecycle state model in `src/cilly_trading/engine/strategy_lifecycle/model.py`; transition rules in `src/cilly_trading/engine/strategy_lifecycle/transitions.py`; promotion service in `src/cilly_trading/engine/strategy_lifecycle/service.py`; production-only enforcement in `src/cilly_trading/engine/pipeline/orchestrator.py`; tests in `tests/strategy_lifecycle/` and `tests/cilly_trading/engine/test_orchestrator_lifecycle_enforcement.py`. | Earlier "pending PR merge + CI" wording was stale relative to current repo contents. |
| Phase 27 - Risk Framework | Implementation Artifacts Verified | Risk contracts in `src/risk/contracts.py`; concrete gate implementation in `src/cilly_trading/engine/risk/gate.py`; pipeline integration in `src/cilly_trading/engine/pipeline/orchestrator.py`; architecture/runtime docs in `docs/architecture/risk_framework.md` and `docs/architecture/risk/risk_framework.md`; tests in `tests/cilly_trading/engine/test_risk_gate.py` and related pipeline enforcement tests. | Audited status documents should not claim the framework is absent where these standalone artifacts exist. |

---

## 4. MVP Guardrail Validation

### No live trading implemented
- **Status:** Validated  
- **Evidence:** Exclusions in `docs/architecture/mvp-spec.md`; guardrail reference in `docs/architecture/phase-9-exit.md`; no live-order endpoint in `src/api/main.py`.

### No broker integration implemented
- **Status:** Validated  
- **Evidence:** Exclusions in `docs/architecture/mvp-spec.md`; scope statement in `docs/getting-started/repo-snapshot.md`; guardrail denylist in `src/cilly_trading/engine/marketdata/guardrails/adapter_guardrails.py`.

### No AI decision engine implemented
- **Status:** Validated  
- **Evidence:** AI exclusion in `docs/architecture/mvp-spec.md`; deterministic strategy execution in `src/api/main.py` and `src/cilly_trading/strategies/`.

### No out-of-scope expansion detected
- **Status:** Validated  
- **Evidence:** Simulator implementation (`src/cilly_trading/engine/paper_trading.py`, `tests/test_paper_trading_simulator.py`) is documented consistently as deterministic simulation only in `docs/operations/paper-trading.md`, `docs/architecture/phase-9-exit.md`, and `docs/getting-started/repo-snapshot.md`, while live trading and broker integration remain excluded.

---

## 5. Architectural Drift Check

### Findings

1. **Backend-served Owner Dashboard surface is `/ui` (confirmed).**  
   Confirmed by StaticFiles mount in `src/api/main.py`, HTML marker `<title>Owner Dashboard</title>` in `src/ui/index.html`, and endpoint test assertion in `tests/health_endpoint.py`.

2. **`/owner` is documented as a frontend-only development route, not a backend runtime route.**  
   This distinction is documented in `docs/operations/ui/owner_dashboard.md` and `docs/index.md`, while the verified backend-served surface remains `/ui`.

3. **Paper-trading documentation is aligned to the simulator boundary.**  
   Simulator code and tests exist, and documentation now describes the capability as deterministic simulation only, with live trading and broker integration still excluded.

4. **Phase 25 status wording was stale.**  
   The dedicated phase artifact described Phase 25 as pending PR merge and CI even though lifecycle modules and tests are already present in the repository.

5. **Orphaned directories.**  
   No conclusive orphaned directory identified.

6. **Dead endpoints.**  
   No confirmed backend dead endpoint identified.

7. **UI without backend support.**  
   No finding: `/ui` and `POST /analysis/run` are both verified.

8. **Backend features without tests.**  
   No conclusive untested high-surface endpoint in audited scope.

9. **Test files without runtime linkage.**  
   No conclusive orphan test file identified.

---

## 6. Identified Gaps

1. **Proposed Issue:** `Hourly Snapshot Runtime status declaration`  
   - Formally declare the operational boundary: in-repo runtime execution capability with external scheduling ownership.  
   - **Phase classification:** Snapshot Runtime  

2. **Proposed Issue:** `Phase 23 evidence artifact alignment`  
   - Keep Phase 23 evidence wording aligned to current repo evidence until additional implementation artifacts exist.  
   - **Phase classification:** Phase 23  

---

## 7. Risk Assessment

### Structural risks
- Remaining documentation drift risk is reduced for audited active surfaces, but future edits can reintroduce contradictions if they stop deferring to verified runtime behavior.
- Previously conflicting phase-number meanings can recur if secondary documents stop deferring to the authoritative roadmap.

### Roadmap ordering risks
- Future roadmap sequencing still depends on keeping paper-trading governance and broader Phase 44 claims separate.
- Unmapped phases such as 16 and 26 still require future governance artifacts if they are to carry roadmap meaning.

### Governance risks
- Guardrail compliance proof weakens if future roadmap or index updates bypass the authoritative taxonomy source.
- Review decisions may vary again if status artifacts and taxonomy artifacts are edited independently without cross-review.
