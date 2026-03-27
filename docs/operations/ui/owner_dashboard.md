# Operator Dashboard Runtime Surface

## Overview
The operator-facing runtime surface is the backend-served workbench at `/ui`.

This page is served from `src/ui/index.html` through the FastAPI static mount in `src/api/main.py`.

## Runtime Route
- Runtime route: `/ui`
- Served by: backend runtime static mount
- Runtime source: `src/ui/index.html`

## Current Runtime Workbench Inventory
The current `/ui` page exposes these visible runtime sections:

- Run Analysis
- Analysis Results
- Watchlist Management
- Saved Watchlists
- Execute Watchlist
- Watchlist Ranked Results
- Runtime State
- Strategy Reference
- Latest Signals
- Recent Alerts
- Journal Artifacts
- Decision Trace
- Runtime Lifecycle

Those sections share one runtime shell. Adjacency on the same page is not phase-completion evidence.

## Backend-Connected Workflow
| Workbench area | Current runtime behavior |
| --- | --- |
| Runtime State | Read-only summary fetched from `GET /system/state` |
| Run Analysis | Browser form submits `POST /analysis/run` |
| Analysis Results | Returned `analysis_run_id` and signals are rendered in the page |
| Strategy Reference | Read-only metadata fetched from `GET /strategies` |
| Latest Signals | Read-only latest signal list fetched from `GET /signals` |
| Watchlist Management | Create, list, read, update, and delete saved watchlists through `/watchlists` routes |
| Watchlist Execution | Execute a saved watchlist through `POST /watchlists/{watchlist_id}/execute` |
| Watchlist Ranking Output | Render `ranked_results` and `failures` returned by watchlist execution |
| Recent Alerts | Read-only alert history fetched from `GET /alerts/history` |
| Journal Artifacts | Read-only artifact browser fetched from `GET /journal/artifacts` |
| Artifact Preview | Selected artifact content fetched from `GET /journal/artifacts/{run_id}/{artifact_name}` |
| Decision Trace | Read-only trace viewer fetched from `GET /journal/decision-trace` |
| Runtime Lifecycle | Read-only order lifecycle viewer fetched from `GET /execution/orders` |

## Phase Ownership Boundary
Use `docs/architecture/ui-runtime-phase-ownership-boundary.md` as the authoritative phase-ownership mapping for shared `/ui`.

Summary boundary:
- Phase 36 owns browser activation and bounded manual-analysis runtime flow.
- Phase 37 owns watchlist CRUD/execution/ranking behavior on the same shell.
- Phase 39 is bounded by the chart-data API contract and does not require current `/ui` chart-panel markers.
- Phase 40 is not proven by current section adjacency.
- Phase 41 is not proven by the read-only alert-history panel alone.

## /owner Separation
`/owner` is not part of the runtime-served operator surface.

The frontend route structure in `frontend/src/App.tsx` may still reference `/owner`, but that does not change runtime contract boundaries:

- `/ui` is the backend-served runtime URL
- `/owner` is not a runtime-equivalent entrypoint
- `/owner` must not be used as runtime evidence for Phase 36, 37, 39, 40, or 41 claims

## Evidence Pointers
Use these repository artifacts when validating this document:

1. `src/api/main.py` mounts `/ui` and exposes the linked runtime APIs.
2. `src/ui/index.html` contains the runtime shell and browser workflow markers.
3. `src/api/test_operator_workbench_surface.py` verifies `/ui` reachability and runtime markers.
4. `tests/test_ui_runtime_browser_flow.py` verifies runtime browser flow, watchlist workflow, and shared-shell markers.
5. `docs/architecture/ui-runtime-phase-ownership-boundary.md` defines phase ownership and non-inference boundaries for shared `/ui`.

