# Phase 39 Runtime Charting Test Plan

## Purpose
This document defines the minimum verification coverage for the bounded Phase 39 chart-data contract while `/ui` is a shared runtime shell.

It is a verification gate, not product-scope expansion.

## Verification Goal
Phase 39 verification succeeds only when all of the following remain true:

1. `/ui` shared-shell markers are stable and continue to enforce non-expansion boundaries.
2. Chart data remains a deterministic projection over existing runtime API responses.
3. Existing Phase 37 watchlist runtime flows remain intact.
4. Deterministic runtime behavior remains intact with no live-data integration path.

## Required Coverage Areas

### 1. Runtime /ui shared-shell marker coverage
Required assertions:

- `/ui` remains reachable and backend-served.
- Existing bounded-shell markers remain present:
  - `id="watchlist-form"`
  - `id="watchlist-ranked-result-list"`
  - `id="alert-status"`
  - `id="alert-list"`
- Route references remain present:
  - `/analysis/run`
  - `/watchlists`
  - `/watchlists/{watchlist_id}/execute`
  - `/alerts/history`
  - `/signals?limit=20&sort=created_at_desc`
- The `/ui` copy keeps explicit non-expansion wording: `No Phase 39 or Phase 40 features`.
- Dedicated Phase 39 chart-panel markers are not required for this gate.

### 2. API contract verification for chart-data behavior
Required assertions:

- `POST /analysis/run` projects into the Phase 39 chart contract with authoritative source metadata.
- `POST /watchlists/{watchlist_id}/execute` projects ranked results and failures into the Phase 39 chart contract.
- `GET /signals` is verified as `fallback_only`.
- Contract flags remain:
  - `snapshot_first = true`
  - `live_data_allowed = false`
  - `market_data_product = false`
  - `chart_route_added = false`
- Point ordering remains deterministic.
- Unknown contract fields are rejected.

### 3. Phase 37 watchlist regression protection
Required assertions:

- Watchlist create/list/read/update/delete remain functional.
- Watchlist execution and deterministic ranking remain functional.
- Symbol-level failures remain isolated in `failures`.

### 4. Deterministic runtime behavior protection
Required assertions:

- Authoritative chart projections remain tied to explicit `ingestion_run_id` sources.
- `GET /signals` remains fallback-only because it does not expose `ingestion_run_id`.
- Runtime browser-flow tests continue using deterministic fixture data.
- No live data providers are invoked during `/ui` browser-flow verification.

## Minimum Test Set
1. `src/api/test_operator_workbench_surface.py`
2. `tests/test_api_phase39_chart_contract.py`
3. `tests/test_ui_runtime_browser_flow.py`
4. `tests/test_phase39_chart_contract_docs.py`
5. `tests/test_ui_runtime_phase_ownership_docs.py`

## Out-of-Scope Verification
- Trading-desk implementation verification
- Notification-delivery verification
- Strategy Lab verification
- Paper-trading product verification
- Live-trading verification
- New real-time market-data integration tests

## Success Condition
Phase 39 verification coverage is considered defined when this plan remains aligned with the repository and the minimum test set above passes.

