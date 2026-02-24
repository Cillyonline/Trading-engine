# Roadmap Compliance Report

## 1. Executive Summary

This audit is based only on repository-verifiable evidence (code, tests, endpoints, and documentation files).

A canonical `Execution Roadmap` source file for phases 17b/23/24/27/25–31 was not located in the repository; assessment therefore uses concrete repository evidence only.

Owner Dashboard is verifiably backend-served at `/ui` via FastAPI `app.mount("/ui", StaticFiles(..., html=True), ...)` and HTML marker `<title>Owner Dashboard</title>`.

Paper-trading simulator code and tests are present, but documentation artifacts still describe paper trading as unavailable, creating state drift.

No live trading endpoint, broker integration runtime, or AI decision engine implementation was verified.

Snapshot runtime execution capability is implemented in-repo, while scheduling remains external and no in-repo scheduler runtime was verified.

Documentation and implementation are therefore only partially aligned.

**Current overall alignment assessment:** **Partially Aligned**

---

## 2. Roadmap Phase Matrix

| Phase | Status | Evidence | Notes |
|-------|--------|----------|-------|
| Phase 17b – Owner Dashboard | Partially Implemented | Backend UI mount in `src/api/main.py` (`app.mount("/ui", StaticFiles(..., html=True), name="ui")`); HTML marker in `src/ui/index.html` (`<title>Owner Dashboard</title>`); tests in `tests/health_endpoint.py`; manual trigger endpoint `POST /analysis/run` in `src/api/main.py`; test in `tests/test_api_manual_analysis_trigger.py`; documentation in `docs/ui/owner_dashboard.md`. | `/ui` is confirmed backend-served. `/owner` appears in documentation but no backend route definition was verified. |
| Hourly Snapshot Runtime | Partially Implemented | `docs/runtime/snapshot_runtime.md` declares in-repo execution capability and external scheduling boundary; `docs/interfaces/batch_execution.md` states no scheduler implementation; no scheduler/cron endpoint verified in `src/api/main.py`. | Runtime execution capability exists in-repo; hourly scheduling is external and not provided by this repository. |
| Phase 24 – Paper Trading Runtime | Partially Implemented | Simulator in `src/cilly_trading/engine/paper_trading.py`; tests in `tests/test_paper_trading_simulator.py`; documentation reference in `docs/RUNBOOK.md`. | Engine-level simulation exists; documentation still partially misaligned. |
| Phase 23 – Research Dashboard | Not Implemented | Research Dashboard implementation artifact: Not confirmed (no verified code/docs/tests). | No repository-verified artifact found. |
| Phase 27 – Risk Framework | Not Implemented | No standalone phase-scoped risk framework module verified; related artifacts include `src/cilly_trading/strategies/config_schema.py`, `tests/strategies/test_strategy_config_schema.py`, `docs/backtesting/metrics_contract.md`. | Risk-related fields exist but no framework-level artifact verified. |
| Phases 25–31 | Not Implemented | Phase-tagged artifacts: Not confirmed (no verified modules/docs). | No concrete phase-mapped implementation artifacts verified. |

---

## 3. MVP Guardrail Validation

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

## 4. Architectural Drift Check

### Findings

1. **Backend-served Owner Dashboard surface is `/ui` (confirmed).**  
   Confirmed by StaticFiles mount in `src/api/main.py`, HTML marker `<title>Owner Dashboard</title>` in `src/ui/index.html`, and endpoint test assertion in `tests/health_endpoint.py`.

2. **`/owner` route not verified in backend runtime.**  
   Appears in documentation guidance (`docs/ui/owner_dashboard.md`) but no backend route definition verified.

3. **Documentation/runtime capability drift for paper trading.**  
   Simulator code and tests exist while documentation still frames paper trading as unavailable.

4. **Orphaned directories.**  
   No conclusive orphaned directory identified.

5. **Dead endpoints.**  
   No confirmed backend dead endpoint identified.

6. **UI without backend support.**  
   No finding: `/ui` and `POST /analysis/run` are both verified.

7. **Backend features without tests.**  
   No conclusive untested high-surface endpoint in audited scope.

8. **Test files without runtime linkage.**  
   No conclusive orphan test file identified.

---

## 5. Identified Gaps

1. **Proposed Issue:** `ROADMAP: Add canonical Execution Roadmap source document`  
   - Add one authoritative roadmap file binding phases to deliverables and acceptance criteria.  
   - **Phase classification:** Governance / Planning  

2. **Proposed Issue:** `Owner Dashboard route documentation clarification (/ui vs /owner)`  
   - Clarify distinction between backend-served `/ui` and any frontend-dev guidance.  
   - **Phase classification:** Phase 17b  

3. **Proposed Issue:** `Paper-trading documentation alignment`  
   - Reconcile documentation statements with implemented simulator artifacts.  
   - **Phase classification:** Phase 24  

4. **Proposed Issue:** `Hourly Snapshot Runtime status declaration`  
   - Formally declare the operational boundary: in-repo runtime execution capability with external scheduling ownership.  
   - **Phase classification:** Snapshot Runtime  

5. **Proposed Issue:** `Phase 23 status artifact`  
   - Add explicit not-implemented declaration or implementation artifact.  
   - **Phase classification:** Phase 23  

6. **Proposed Issue:** `Phase 27 status artifact`  
   - Add explicit declaration distinguishing framework-level risk system from existing risk-related fields.  
   - **Phase classification:** Phase 27  

---

## 6. Risk Assessment

### Structural risks
- Missing canonical roadmap source increases interpretation variance.
- Documentation-to-implementation drift reduces operator clarity.

### Roadmap ordering risks
- Paper-trading state drift can mis-sequence dependent phases.
- Undefined phase artifacts for 23/27/25–31 increase planning ambiguity.

### Governance risks
- Guardrail compliance proof weakens without a single roadmap authority artifact.
- Review decisions may vary without a clear phase-acceptance reference.