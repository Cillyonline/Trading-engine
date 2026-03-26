# Operator Dashboard Runtime Surface

## Overview
The operator-facing runtime surface is the backend-served workbench at `/ui`.

This page is served from `src/ui/index.html` through the FastAPI static mount in `src/api/main.py`. For runtime documentation, `/ui` is the authoritative browser surface, `docs/operations/ui/phase-36-web-activation-contract.md` is the authoritative Phase 36 contract, `docs/architecture/phases/phase-37-status.md` defines the bounded watchlist workflow now present on the same runtime page, `docs/operations/ui/phase-39-charting-contract.md` defines the bounded charting contract now implemented as a read-only visual-analysis surface on that same runtime page, and `docs/architecture/roadmap/cilly_trading_execution_roadmap_updated.md` now reflects that bounded implementation in roadmap terms.

## Runtime Route
- Runtime route: `/ui`
- Served by: backend runtime static mount
- Runtime source: `src/ui/index.html`

## Current Runtime Workbench
The current `/ui` page exposes these visible sections in the runtime shell:

- Overview
- Runtime Status
- Analysis Runs
- Strategy List
- Signals
- Chart Panel
- Visual Analysis Surface
- Journal Artifacts
- Decision Trace
- Screener
- Manage Watchlists
- Watchlist Execution
- Watchlist Ranked Results
- Trade Lifecycle
- Audit Trail

Those section labels are part of the current shell inventory. They are not, by themselves, evidence that later roadmap phases are complete.

## Backend-Connected Workflow
The runtime page currently performs this browser-served work:

| Workbench area | Current runtime behavior |
| --- | --- |
| Runtime State | Read-only summary fetched from `GET /system/state` |
| Run Analysis | Browser form submits `POST /analysis/run` |
| Analysis Results | Returned `analysis_run_id` and signals are rendered in the page |
| Strategy List | Read-only metadata fetched from `GET /strategies` |
| Signals | Read-only latest signal list fetched from `GET /signals` |
| Chart Panel | Read-only chart surface rendered from existing runtime payloads returned by `GET /signals`, `POST /analysis/run`, and `POST /watchlists/{watchlist_id}/execute` |
| Chart Source Markers | Stable runtime markers identify analysis, watchlist-execution, and signal feeds for deterministic `/ui` surface tests |
| Watchlist Management | Create, list, read, update, and delete saved watchlists through `/watchlists` routes |
| Watchlist Execution | Execute a saved watchlist through `POST /watchlists/{watchlist_id}/execute` |
| Watchlist Ranking Output | Render `ranked_results` and `failures` returned by the watchlist execution route |
| Journal Artifacts | Read-only artifact browser fetched from `GET /journal/artifacts` |
| Artifact Preview | Selected artifact content fetched from `GET /journal/artifacts/{run_id}/{artifact_name}` |
| Decision Trace | Read-only trace viewer fetched from `GET /journal/decision-trace` |
| Trade Lifecycle | Read-only order lifecycle viewer fetched from `GET /execution/orders` |

## Phase Boundary
The current `/ui` surface now spans three documented runtime boundaries:

- Phase 36: backend-served browser activation and the original operator workbench shell
- Phase 37: bounded watchlist management, persisted watchlist execution, and ranked-result rendering on that same shell
- Phase 39: bounded read-only charting and visual analysis built from existing runtime payloads on that same shell

This does not imply Phase 40 trading-desk expansion, alerts, or broader later-phase product workflows.

## /owner Separation
`/owner` is not part of the runtime-served operator surface.

The frontend route structure in `frontend/src/App.tsx` may still reference `/owner`, but that does not change the runtime contract:

- `/ui` is the backend-served runtime URL
- `/owner` must not be documented as an equivalent runtime entrypoint
- `/owner` must not be used to describe the Phase 36 browser workflow

## Runtime Versus Development Routes
| Route | Environment | Meaning for documentation |
| --- | --- | --- |
| `/ui` | Backend runtime | Canonical runtime-served operator workbench |
| `/owner` | Frontend route structure only | Non-canonical route reference that must not replace `/ui` in runtime docs |

## Evidence Pointers
Use these repository artifacts when validating this document:

1. `src/api/main.py` mounts `/ui` and includes the bounded API routers serving `GET /system/state`, `POST /analysis/run`, watchlist CRUD routes, `POST /watchlists/{watchlist_id}/execute`, `GET /strategies`, `GET /signals`, `GET /journal/artifacts`, `GET /journal/decision-trace`, and `GET /execution/orders`.
2. `src/ui/index.html` contains the runtime shell and the implemented browser workflow, including watchlist panels, chart-panel markers, and chart-source markers.
3. `tests/api/test_health_endpoints_api.py` verifies the runtime health endpoint surface.
4. `src/api/test_operator_workbench_surface.py` verifies the `/ui` shell markers, watchlist panels, chart-panel markers, and linked runtime endpoints.
5. `tests/test_ui_runtime_browser_flow.py` verifies the browser workflow uses the existing runtime API surface for watchlist CRUD, execution, and deterministic chart-panel markers as well as the existing operator routes.
6. `docs/operations/ui/phase-39-charting-contract.md` defines the bounded read-only charting scope implemented on the same `/ui` surface without expanding into later product phases.

## Verification Outcome
A reviewer should find:

- `/ui` is the runtime-served operator surface
- `/owner` is not a runtime-equivalent route
- the current workbench supports the bounded Phase 36 and Phase 37 browser workflows and the bounded Phase 39 chart panel, without claiming Phase 40 desk scope or later workflow completion
