# Phase 39 Runtime Charting Test Plan

## Purpose
This document defines the minimum verification coverage required before Phase 39 runtime charting implementation expands on `/ui`.

It is a bounded test plan, not a product-scope expansion. The goal is to preserve deterministic runtime behavior while explicitly defining the verification gate for the read-only Phase 39 chart panel.

This file is normative for Phase 39 verification coverage and must stay aligned with:

- `docs/ui/phase-39-charting-contract.md`
- `docs/api/runtime_chart_data_contract.md`
- `docs/phases/phase-37-status.md`
- `src/api/test_operator_workbench_surface.py`
- `tests/test_api_phase39_chart_contract.py`
- `tests/test_ui_runtime_browser_flow.py`

## Verification Goal
Phase 39 succeeds only when the repository defines and later passes the minimum test set that proves all of the following:

1. `/ui` exposes stable chart-panel markers for bounded runtime visual analysis.
2. Chart data is projected from existing runtime API responses through a deterministic contract.
3. Existing Phase 37 watchlist CRUD and watchlist execution runtime flows still work on `/ui`.
4. Deterministic runtime expectations remain intact and no new non-deterministic integration flow is introduced.

## Required Coverage Areas

### 1. Runtime UI chart marker coverage
The required `/ui` verification coverage must assert the presence of the bounded Phase 39 charting markers and scope text.

Minimum required assertions:

- `/ui` remains reachable and backend-served.
- `#runtime-chart-panel` is present.
- `data-runtime-surface="chart-panel"` is present.
- `data-runtime-chart-panel="visible"` is present.
- `data-runtime-chart-boundary="phase39-visual-analysis"` is present.
- `#runtime-chart-surface` is present.
- `#chart-source-analysis-run` is present.
- `#chart-source-watchlist-execution` is present.
- `#chart-source-latest-signals` is present.
- `/analysis/run` is referenced as a chart source.
- `/watchlists/{watchlist_id}/execute` is referenced as a chart source.
- `/signals?limit=20&sort=created_at_desc` is referenced as a chart source.
- The `/ui` copy explicitly preserves the boundary text blocking Phase 40 desk widgets, alerts, and live trading controls.

This coverage defines the stable runtime markers that later implementation may use, restyle, or populate without changing the Phase 39 boundary.

### 2. API contract verification for chart-data behavior
The required API-level verification coverage must prove that chart data remains a deterministic projection over existing routes rather than a new backend surface.

Minimum required assertions:

- `POST /analysis/run` projects into the Phase 39 chart contract with authoritative source metadata.
- `POST /watchlists/{watchlist_id}/execute` projects ranked results and failures into the Phase 39 chart contract.
- `GET /signals` is explicitly verified as `fallback_only`.
- The chart contract keeps `snapshot_first = true`.
- The chart contract keeps `live_data_allowed = false`.
- The chart contract keeps `market_data_product = false`.
- The chart contract keeps `chart_route_added = false`.
- Point ordering is deterministic and inherited from the reused source route.
- Unknown contract fields are rejected.

This coverage is the API contract gate for chart-data behavior. It prevents Phase 39 from silently introducing a chart-specific backend contract, live-market semantics, or non-deterministic payload interpretation.

### 3. Phase 37 watchlist regression protection
Phase 39 verification must explicitly protect the already verified Phase 37 runtime workflow on `/ui`.

Minimum required assertions:

- Watchlist create still works through `POST /watchlists`.
- Watchlist list still works through `GET /watchlists`.
- Watchlist read still works through `GET /watchlists/{watchlist_id}`.
- Watchlist update still works through `PUT /watchlists/{watchlist_id}`.
- Watchlist delete still works through `DELETE /watchlists/{watchlist_id}`.
- Watchlist execution still works through `POST /watchlists/{watchlist_id}/execute`.
- Ranked results remain deterministic.
- Symbol-level failures remain isolated into `failures`.
- The `/ui` browser workflow continues to render watchlist management, ranked results, and chart-panel markers together on the same runtime workbench.

This regression gate exists because Phase 39 extends the same `/ui` surface already verified in Phase 37.

### 4. Deterministic runtime behavior protection
Phase 39 verification must preserve deterministic testing expectations.

Minimum required assertions:

- Authoritative chart data remains bound to explicit `ingestion_run_id` sources.
- `GET /signals` remains non-authoritative fallback evidence because it does not provide `ingestion_run_id`.
- Existing runtime browser-flow tests continue to use deterministic fixture data.
- No live data providers are called during the `/ui` browser-flow verification path.
- No new streaming, clock-sensitive, or non-deterministic integration flow is required for Phase 39 verification.

## Minimum Test Set
The minimum implementation-aligned test set for safe Phase 39 work is:

1. `src/api/test_operator_workbench_surface.py`
   Verifies the `/ui` shell, stable chart markers, route references, and bounded-scope text.
2. `tests/test_api_phase39_chart_contract.py`
   Verifies deterministic chart-contract projection behavior for analysis runs, watchlist execution, and signal-log fallback behavior.
3. `tests/test_ui_runtime_browser_flow.py`
   Verifies the end-to-end runtime browser flow against existing APIs, including watchlist CRUD, watchlist execution, and chart-panel markers without external market-data calls.
4. `tests/test_phase39_chart_contract_docs.py`
   Verifies that the repository documentation continues to define the bounded Phase 39 chart contract and this test plan.

No broader frontend refactor suite, non-deterministic browser automation, or new integration harness is required for the minimum Phase 39 verification gate.

## Out-of-Scope Verification
The following are explicitly not required for this Phase 39 test plan:

- alerts verification
- Strategy Lab verification
- paper trading product verification
- live trading verification
- broader trading-desk workflow verification
- new real-time market-data integration tests
- unrelated test-infrastructure rewrites

## Acceptance Criteria Mapping

### Required runtime UI chart marker coverage is explicitly defined
Satisfied by the "Runtime UI chart marker coverage" section and the minimum `/ui` marker assertions listed above.

### Required API contract tests for chart-data behavior are explicitly defined
Satisfied by the "API contract verification for chart-data behavior" section and the minimum contract assertions listed above.

### Regression expectations for existing Phase 37 watchlists and deterministic runtime behavior are explicitly documented
Satisfied by the "Phase 37 watchlist regression protection" and "Deterministic runtime behavior protection" sections.

## Success Condition
Phase 39 verification coverage is considered defined when this plan remains aligned with the current repository and the minimum test set above passes when later implementation work is executed.
