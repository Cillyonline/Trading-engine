# Roadmap Compliance Report

## 1. Executive Summary
This audit is based only on repository-verifiable evidence (code, tests, endpoints, and documentation files).
A canonical Execution Roadmap source file for phases 17b/23/24/27/25–31 was not located in the repo.
Owner Dashboard is verifiably backend-served at `/ui` via FastAPI `app.mount("/ui", StaticFiles(..., html=True), ...)` and HTML marker `<title>Owner Dashboard</title>`.
Paper-trading simulator code and tests are present, but a dedicated owner-facing runtime command is still documented as unavailable.
No live trading endpoint, broker integration runtime, or AI decision engine implementation was verified.
Snapshot ingestion creation/scheduling is documented as out-of-band and no in-repo scheduler runtime was verified.
Documentation and implementation are only partially aligned due to capability/state drift around paper-trading availability statements.

**Current overall alignment assessment:** **Partially Aligned**

## 2. Roadmap Phase Matrix

| Phase | Status | Evidence | Notes |
|---|---|---|---|
| Phase 17b – Owner Dashboard | Partially Implemented | Backend UI mount: `src/api/main.py` (`app.mount("/ui", StaticFiles(..., html=True), name="ui")`); backend-served HTML marker: `src/ui/index.html` (`<title>Owner Dashboard</title>`); endpoint behavior test includes marker check: `tests/health_endpoint.py`; manual analysis endpoint: `POST /analysis/run` in `src/api/main.py`; manual trigger test: `tests/test_api_manual_analysis_trigger.py`; related doc: `docs/ui/owner_dashboard.md`. | `/ui` is confirmed as backend-served Owner Dashboard surface. `/owner` is documented in `docs/ui/owner_dashboard.md` as frontend dev guidance, but no backend route for `/owner` was verified. |
| Hourly Snapshot Runtime | Not Implemented | `docs/interfaces/batch_execution.md` states no scheduler implementation; `docs/api/usage_contract.md` and `docs/analyst-workflow.md` state snapshot ingestion is out-of-band; no scheduler/cron endpoint in `src/api/main.py`. | Snapshot consumption exists; hourly in-app runtime scheduling is not verified. |
| Phase 24 – Paper Trading Runtime | Partially Implemented | Simulator implementation: `src/cilly_trading/engine/paper_trading.py`; simulator tests: `tests/test_paper_trading_simulator.py`; runbook statement about no dedicated owner-facing paper-trading run command: `docs/RUNBOOK.md`. | Engine-level simulation is implemented; operator runtime surface remains limited per docs. |
| Phase 23 Integration – Research Dashboard | Not Implemented | Research Dashboard implementation artifact: Not confirmed (path not verified in repo). | No verified code/docs/tests were found for a Research Dashboard integration artifact. |
| Phase 27 – Risk Framework | Not Implemented | Phase-27 specific implementation artifact: Not confirmed (path not verified in repo). Existing risk-related references are non-framework artifacts (`src/cilly_trading/strategies/config_schema.py`, `tests/strategies/test_strategy_config_schema.py`, `docs/backtesting/metrics_contract.md`). | Risk-related fields/metrics exist, but no standalone phase-scoped risk framework artifact was verified. |
| Later Phases (25–31 grouped) | Not Implemented | Phase 25–31 implementation artifacts: Not confirmed (path not verified in repo). | No phase-tagged implementation artifacts were verified for phases 25–31. |

## 3. MVP Guardrail Validation

- **No live trading implemented**
  - **Status:** Validated
  - **Evidence:** Exclusions in `docs/MVP_SPEC.md`; guardrail statement in `docs/phase-9-exit.md`; no live-trading endpoint in `src/api/main.py`.

- **No broker integration implemented**
  - **Status:** Validated
  - **Evidence:** Exclusions in `docs/MVP_SPEC.md`; scope statement in `docs/repo-snapshot.md`; adapter guardrail denylist includes broker path token in `src/cilly_trading/engine/marketdata/guardrails/adapter_guardrails.py`.

- **No AI decision engine implemented**
  - **Status:** Validated
  - **Evidence:** Exclusions in `docs/MVP_SPEC.md`; deterministic strategy execution surfaces in `src/api/main.py`; strategy modules under `src/cilly_trading/strategies/`.

- **No out-of-scope expansion detected**
  - **Status:** Not Validated (documentation drift detected)
  - **Evidence:** Simulator artifacts exist (`src/cilly_trading/engine/paper_trading.py`, `tests/test_paper_trading_simulator.py`), while repository docs still include “not available” framing for paper-trading/simulation (`docs/phase-9-exit.md`, `docs/repo-snapshot.md`).

## 4. Architectural Drift Check

### Findings
1. **Backend-served Owner Dashboard surface is `/ui` (confirmed).**
   - Confirmed by FastAPI StaticFiles mount in `src/api/main.py` and HTML marker `<title>Owner Dashboard</title>` in `src/ui/index.html`, with endpoint test assertion in `tests/health_endpoint.py`.

2. **`/owner` route usage is not verified in backend runtime.**
   - `/owner` appears in documentation guidance (`docs/ui/owner_dashboard.md`), but no backend route definition for `/owner` was verified in `src/api/main.py`.

3. **Documentation/runtime capability drift for paper trading.**
   - Implemented simulator code/tests (`src/cilly_trading/engine/paper_trading.py`, `tests/test_paper_trading_simulator.py`) coexist with docs that still state paper trading/simulation is unavailable (`docs/phase-9-exit.md`, `docs/repo-snapshot.md`).

4. **Orphaned directories.**
   - No conclusive orphaned directory finding from verified repository evidence.

5. **Dead endpoints.**
   - No backend dead endpoint was conclusively verified in this audit scope.

6. **UI without backend support.**
   - No finding for Owner Dashboard: UI surface `/ui` and backend endpoint `POST /analysis/run` are both verified in `src/api/main.py`.

7. **Backend features without tests.**
   - No conclusive finding in audited scope for `/ui`, `/health`, `/analysis/run`, and paper-trading simulator (tests verified).

8. **Test files without runtime linkage.**
   - No conclusive finding from verified evidence in audited scope.

## 5. Identified Gaps

1. **Proposed Issue:** `ROADMAP: Add canonical Execution Roadmap source document for audited phases`
   - **Description:** Add one authoritative roadmap file for phases 17b/23/24/27/25–31 to bind implementation checks to a single verified source.
   - **Phase classification:** Governance / Planning

2. **Proposed Issue:** `Owner Dashboard route documentation clarification (/ui backend-served vs /owner frontend-dev doc usage)`
   - **Description:** Clarify documentation so backend-served `/ui` evidence and any frontend-dev `/owner` guidance are explicitly distinguished.
   - **Phase classification:** Phase 17b – Owner Dashboard

3. **Proposed Issue:** `Paper-trading documentation alignment with implemented simulator artifacts`
   - **Description:** Reconcile documentation status statements with verified simulator implementation and tests.
   - **Phase classification:** Phase 24 – Paper Trading Runtime

4. **Proposed Issue:** `Hourly Snapshot Runtime status declaration`
   - **Description:** Add explicit declaration on whether hourly snapshot scheduling remains permanently out-of-band or is planned in-repo.
   - **Phase classification:** Hourly Snapshot Runtime

5. **Proposed Issue:** `Phase 23 Research Dashboard status artifact`
   - **Description:** Add explicit not-implemented or implementation artifact so phase status is verifiable.
   - **Phase classification:** Phase 23 Integration – Research Dashboard

6. **Proposed Issue:** `Phase 27 Risk Framework status artifact`
   - **Description:** Add explicit not-implemented or implementation artifact distinguishing framework status from existing risk-related fields.
   - **Phase classification:** Phase 27 – Risk Framework

## 6. Risk Assessment

- **Structural risks**
  - Missing canonical roadmap source increases interpretation variance.
  - Documentation-to-implementation drift can reduce operator confidence.

- **Roadmap ordering risks**
  - Partial paper-trading implementation with conflicting status docs can mis-sequence dependent work.
  - Unclear phase-status artifacts for 23/27/25–31 can cause parallel planning assumptions.

- **Governance risks**
  - Guardrail compliance evidence is weaker when source-of-truth roadmap artifacts are absent.
  - Review outcomes may vary without a single roadmap reference for phase acceptance.
