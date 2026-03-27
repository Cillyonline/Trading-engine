# Phase 36 /ui Web Activation Contract

## Purpose
This document is the canonical Phase 36 contract for the runtime-served `/ui` surface.

It defines bounded Phase 36 ownership on a shared runtime shell and prevents overlap-based claims for later phases.

## Canonical Runtime Surface
- Canonical runtime URL: `/ui`
- Serving mechanism: FastAPI static mount
- Runtime page source: `src/ui/index.html`

For Phase 36, `/ui` is the runtime-served browser activation route. No other route is an equivalent runtime activation URL.

## Supported Phase 36 Browser Workflow
Phase 36 documents one bounded browser workflow:

1. Open the backend-served runtime workbench at `/ui`.
2. Load read-only runtime context from:
   - `GET /system/state`
   - `GET /strategies`
   - `GET /signals`
   - `GET /journal/artifacts`
   - `GET /execution/orders`
3. Submit manual analysis through `POST /analysis/run`.
4. Review deterministic `analysis_run_id` and returned signals in-browser.
5. Inspect artifact preview, decision trace, and trade lifecycle evidence in the same runtime session.

## Runtime-Reachable Phase 36 Surfaces
| Phase 36 area | Current runtime behavior through `/ui` | Repository-verifiable surface |
| --- | --- | --- |
| Runtime shell | Browser page is served from backend runtime | `/ui` |
| Runtime state | Read-only runtime summary is loaded automatically | `GET /system/state` |
| Analysis trigger | Browser form submits a manual runtime analysis request | `POST /analysis/run` |
| Analysis results | Returned run id and signals are rendered in-browser | `POST /analysis/run` response |
| Strategy reference | Read-only strategy metadata table | `GET /strategies` |
| Latest signals | Read-only signal list | `GET /signals` |
| Journal artifact list | Read-only artifact browser | `GET /journal/artifacts` |
| Journal artifact preview | Artifact content preview after selection | `GET /journal/artifacts/{run_id}/{artifact_name}` |
| Decision trace | Read-only trace view for a selected artifact | `GET /journal/decision-trace` |
| Runtime lifecycle | Read-only order lifecycle view | `GET /execution/orders` |

## Shared-Shell Boundary
The `/ui` page also contains watchlist and alert-history sections. Their presence does not extend Phase 36 scope.

Phase ownership for shared `/ui` sections is defined in:
- `docs/architecture/ui-runtime-phase-ownership-boundary.md`

## /owner Boundary
`/owner` is outside the Phase 36 runtime contract.

That means:
- `/owner` is not a runtime-served backend entrypoint
- `/owner` is not an accepted alternative to `/ui`
- `/owner` must not be cited as the Phase 36 browser activation URL

## Later-Phase Boundary
Phase 36 stops at the bounded browser activation and manual-analysis workflow above.

Claims that belong to later phases include:
- Phase 37 watchlist persistence/CRUD/execution/ranking ownership
- Phase 39 chart-panel UI ownership
- Phase 40 trading-desk completion claims
- Phase 41 alert-delivery/notification claims
- Strategy Lab, paper-trading product workflow, live-trading workflow, broker integration

## Acceptance Evidence
| Evidence area | Repository basis |
| --- | --- |
| Runtime entrypoint | `src/api/main.py` mounts `/ui` with `StaticFiles(..., html=True)` |
| Browser workflow | `src/ui/index.html` includes `/system/state`, `/strategies`, `/signals`, `/journal/artifacts`, `/journal/decision-trace`, `/execution/orders`, and `POST /analysis/run` |
| Route reachability tests | `tests/health_endpoint.py`, `src/api/test_operator_workbench_surface.py`, and `tests/test_ui_runtime_browser_flow.py` |
| Manual analysis behavior | `tests/test_api_manual_analysis_trigger.py` |
| Phase ownership guard | `docs/architecture/ui-runtime-phase-ownership-boundary.md` |

## Outcome
For Phase 36, the canonical runtime contract is:
- enter through `/ui`
- run the bounded manual-analysis operator workflow
- treat shared-shell adjacency as non-authoritative for later-phase completion

