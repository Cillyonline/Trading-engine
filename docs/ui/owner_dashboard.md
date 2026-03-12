# Operator Dashboard Runtime Surface

## Overview
The operator-facing runtime surface is the backend-served workbench at `/ui`.

This page is served from `src/ui/index.html` through the FastAPI static mount in `src/api/main.py`. For runtime documentation, `/ui` is the authoritative browser surface and `docs/ui/phase-36-web-activation-contract.md` is the authoritative Phase 36 contract.

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
- Journal Artifacts
- Decision Trace
- Screener
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
| Journal Artifacts | Read-only artifact browser fetched from `GET /journal/artifacts` |
| Artifact Preview | Selected artifact content fetched from `GET /journal/artifacts/{run_id}/{artifact_name}` |
| Decision Trace | Read-only trace viewer fetched from `GET /journal/decision-trace` |
| Trade Lifecycle | Read-only order lifecycle viewer fetched from `GET /execution/orders` |

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

1. `src/api/main.py` mounts `/ui` and defines `GET /system/state`, `POST /analysis/run`, `GET /strategies`, `GET /signals`, `GET /journal/artifacts`, `GET /journal/decision-trace`, and `GET /execution/orders`.
2. `src/ui/index.html` contains the runtime shell and the implemented browser workflow.
3. `tests/health_endpoint.py` verifies the runtime page title and route reachability.
4. `src/api/test_operator_workbench_surface.py` verifies the `/ui` shell markers and linked runtime endpoints.
5. `tests/test_ui_runtime_browser_flow.py` verifies the browser workflow uses the existing runtime API surface.

## Verification Outcome
A reviewer should find:

- `/ui` is the runtime-served operator surface
- `/owner` is not a runtime-equivalent route
- the current workbench supports a bounded Phase 36 browser workflow without claiming later watchlist, trading-desk, alerts, paper-trading product, or live-trading scope
