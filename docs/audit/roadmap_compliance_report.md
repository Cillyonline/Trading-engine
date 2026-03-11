# Roadmap Compliance Report

## 1. Executive Summary

This audit is based only on repository-verifiable evidence (code, tests, endpoints, and documentation files).

The authoritative in-repo source for audited phase taxonomy is `docs/roadmap/execution_roadmap.md`. This report now defers to that roadmap for phase-number meanings and uses this document only for audit findings and traceability.

Owner Dashboard is verifiably backend-served at `/ui` via FastAPI `app.mount("/ui", StaticFiles(..., html=True), ...)` and HTML marker `<title>Owner Dashboard</title>`.

Paper-trading simulator code and tests are present, but documentation artifacts still describe paper trading as unavailable, creating state drift.

Strategy Lifecycle Management and Risk Framework both have repository-verifiable implementation artifacts; earlier status wording that framed them as pending or absent was outdated.

No live trading endpoint, broker integration runtime, or AI decision engine implementation was verified.

Snapshot runtime execution capability is implemented in-repo, while scheduling remains external and no in-repo scheduler runtime was verified.

Documentation and implementation are therefore only partially aligned, with this report updated to remove direct contradictions for the audited phase-status artifacts.

**Current overall alignment assessment:** **Partially Aligned**

---

## 2. Audited Phase Taxonomy Trace

| Phase | Authoritative meaning | Trace path | Audit note |
|-------|-----------------------|------------|------------|
| Phase 5 | External Ready exit gate | `docs/governance/phase-5-exit-criteria.md` | Governance gate, not reassessed for implementation status in this report. |
| Phase 16 | No authoritative in-repo phase taxonomy artifact located | `docs/roadmap/execution_roadmap.md` | Reviewers should treat the phase as unmapped unless a future governance artifact establishes it. |
| Phase 17 | Consumer Interfaces and Usage Patterns umbrella phase | `docs/roadmap/execution_roadmap.md` | Distinct from Phase 17b; secondary index links are navigation only. |
| Phase 17b | Owner Dashboard | `docs/roadmap/execution_roadmap.md` | This report's Owner Dashboard findings map only to Phase 17b. |
| Phase 23 | Research Dashboard | `docs/roadmap/execution_roadmap.md` | Taxonomy authority remains with the roadmap; `docs/phases/phase-23-status.md` is the dedicated status artifact. |
| Phase 25 | Strategy Lifecycle Management | `docs/roadmap/execution_roadmap.md` | Taxonomy authority remains with the roadmap; `docs/phases/phase_25_strategy_lifecycle.md` is the dedicated status artifact aligned to verified lifecycle modules and tests. |
| Phase 26 | No authoritative in-repo phase taxonomy artifact located | `docs/roadmap/execution_roadmap.md` | Reviewers should not infer a Phase 26 meaning from adjacent roadmap blocks. |
| Phase 27 | Risk Framework | `docs/roadmap/execution_roadmap.md` | Taxonomy authority remains with the roadmap; `docs/phases/phase-27-status.md` is the dedicated status artifact, and Phase 27 remains distinct from Phase 27b Pipeline Enforcement Layer artifacts. |

---

## 3. Roadmap Phase Matrix

| Phase | Status | Evidence | Notes |
|-------|--------|----------|-------|
| Phase 17b - Owner Dashboard | Partially Implemented | Backend UI mount in `src/api/main.py` (`app.mount("/ui", StaticFiles(..., html=True), name="ui")`); HTML marker in `src/ui/index.html` (`<title>Owner Dashboard</title>`); tests in `tests/health_endpoint.py`; manual trigger endpoint `POST /analysis/run` in `src/api/main.py`; test in `tests/test_api_manual_analysis_trigger.py`; documentation in `docs/ui/owner_dashboard.md`. | `/ui` is confirmed backend-served. `/owner` appears in documentation but no backend route definition was verified. |
| Hourly Snapshot Runtime | Partially Implemented | `docs/runtime/snapshot_runtime.md` declares in-repo execution capability and external scheduling boundary; `docs/interfaces/batch_execution.md` states no scheduler implementation; no scheduler/cron endpoint verified in `src/api/main.py`. | Runtime execution capability exists in-repo; hourly scheduling is external and not provided by this repository. |
| Phase 24 - Paper Trading Runtime | Partially Implemented | Simulator in `src/cilly_trading/engine/paper_trading.py`; tests in `tests/test_paper_trading_simulator.py`; documentation reference in `docs/RUNBOOK.md`. | Engine-level simulation exists; documentation still partially misaligned. |
| Phase 23 - Research Dashboard | Not Implemented | No repository-verifiable code, tests, or runtime docs were confirmed beyond roadmap/status tracking references. | No direct implementation artifact was found for the audited phase. |
| Phase 25 - Strategy Lifecycle Management | Implemented In Repository | Lifecycle state model in `src/cilly_trading/engine/strategy_lifecycle/model.py`; transition rules in `src/cilly_trading/engine/strategy_lifecycle/transitions.py`; promotion service in `src/cilly_trading/engine/strategy_lifecycle/service.py`; production-only enforcement in `src/cilly_trading/engine/pipeline/orchestrator.py`; tests in `tests/strategy_lifecycle/` and `tests/cilly_trading/engine/test_orchestrator_lifecycle_enforcement.py`. | Earlier "pending PR merge + CI" wording was stale relative to current repo contents. |
| Phase 27 - Risk Framework | Implementation Artifacts Verified | Risk contracts in `src/risk/contracts.py`; concrete gate implementation in `src/cilly_trading/engine/risk/gate.py`; pipeline integration in `src/cilly_trading/engine/pipeline/orchestrator.py`; architecture/runtime docs in `docs/architecture/risk_framework.md` and `docs/risk/risk_framework.md`; tests in `tests/cilly_trading/engine/test_risk_gate.py` and related pipeline enforcement tests. | Audited status documents should not claim the framework is absent where these standalone artifacts exist. |

---

## 4. MVP Guardrail Validation

### No live trading implemented
- **Status:** Validated  
- **Evidence:** Exclusions in `docs/MVP_SPEC.md`; guardrail reference in `docs/phase-9-exit.md`; no live-order endpoint in `src/api/main.py`.

### No broker integration implemented
- **Status:** Validated  
- **Evidence:** Exclusions in `docs/MVP_SPEC.md`; scope statement in `docs/repo-snapshot.md`; guardrail denylist in `src/cilly_trading/engine/marketdata/guardrails/adapter_guardrails.py`.

### No AI decision engine implemented
- **Status:** Validated  
- **Evidence:** AI exclusion in `docs/MVP_SPEC.md`; deterministic strategy execution in `src/api/main.py` and `src/cilly_trading/strategies/`.

### No out-of-scope expansion detected
- **Status:** Not Validated (documentation drift detected)  
- **Evidence:** Simulator implementation (`src/cilly_trading/engine/paper_trading.py`, `tests/test_paper_trading_simulator.py`) conflicts with documentation statements claiming paper trading is unavailable (`docs/phase-9-exit.md`, `docs/repo-snapshot.md`).

---

## 5. Architectural Drift Check

### Findings

1. **Backend-served Owner Dashboard surface is `/ui` (confirmed).**  
   Confirmed by StaticFiles mount in `src/api/main.py`, HTML marker `<title>Owner Dashboard</title>` in `src/ui/index.html`, and endpoint test assertion in `tests/health_endpoint.py`.

2. **`/owner` route not verified in backend runtime.**  
   Appears in documentation guidance (`docs/ui/owner_dashboard.md`) but no backend route definition verified.

3. **Documentation/runtime capability drift for paper trading.**  
   Simulator code and tests exist while documentation still frames paper trading as unavailable.

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

1. **Proposed Issue:** `Owner Dashboard route documentation clarification (/ui vs /owner)`  
   - Clarify distinction between backend-served `/ui` and any frontend-dev guidance.  
   - **Phase classification:** Phase 17b  

2. **Proposed Issue:** `Paper-trading documentation alignment`  
   - Reconcile documentation statements with implemented simulator artifacts.  
   - **Phase classification:** Phase 24  

3. **Proposed Issue:** `Hourly Snapshot Runtime status declaration`  
   - Formally declare the operational boundary: in-repo runtime execution capability with external scheduling ownership.  
   - **Phase classification:** Snapshot Runtime  

4. **Proposed Issue:** `Phase 23 status artifact`  
   - Keep explicit not-implemented declaration aligned to current repo evidence until implementation artifacts exist.  
   - **Phase classification:** Phase 23  

---

## 7. Risk Assessment

### Structural risks
- Documentation-to-implementation drift reduces operator clarity.
- Previously conflicting phase-number meanings can recur if secondary documents stop deferring to the authoritative roadmap.

### Roadmap ordering risks
- Paper-trading state drift can mis-sequence dependent phases.
- Unmapped phases such as 16 and 26 still require future governance artifacts if they are to carry roadmap meaning.

### Governance risks
- Guardrail compliance proof weakens if future roadmap or index updates bypass the authoritative taxonomy source.
- Review decisions may vary again if status artifacts and taxonomy artifacts are edited independently without cross-review.
