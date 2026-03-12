# Phase 36 Web Activation Evidence

## Purpose
This note records the repository-verifiable evidence that supports Phase 36 roadmap and status reviews without overstating later phases.

## Canonical Runtime Surface
- Canonical runtime browser URL: `/ui`
- Served by: FastAPI static mount in `src/api/main.py`
- Runtime page source: `src/ui/index.html`

`/ui` is the Phase 36 runtime-served browser surface. `/owner` is not the canonical runtime entrypoint.

## Supported Phase 36 Browser Workflow
The repository currently verifies this bounded browser workflow:

1. Open `/ui`.
2. Load runtime context already fetched by the page from:
   - `GET /system/state`
   - `GET /strategies`
   - `GET /signals`
   - `GET /journal/artifacts`
   - `GET /execution/orders`
3. Submit manual analysis through `POST /analysis/run`.
4. Review the returned `analysis_run_id` and signals in the same browser session.
5. Inspect artifact preview, decision trace, and trade lifecycle evidence in-browser.

## Phase Boundary
The current `/ui` shell is Phase 36 evidence for browser activation and bounded runtime analysis only.

It is not evidence of:

- Phase 37 watchlist CRUD, persistence, ranking, or dedicated watchlist management UI
- Phase 40 heatmaps, leaderboard views, richer opportunity dashboards, or broader trading-desk workflow
- alerts or notifications
- paper-trading product workflow
- live-trading workflow
- broker integration

## Repository Evidence
| Evidence area | Repository basis |
| --- | --- |
| Runtime entrypoint | `src/api/main.py` mounts `/ui` with `StaticFiles(..., html=True)` |
| Browser workflow | `src/ui/index.html` loads `/system/state`, `/strategies`, `/signals`, `/journal/artifacts`, `/journal/decision-trace`, `/execution/orders`, and submits `POST /analysis/run` |
| `/ui` route reachability | `tests/health_endpoint.py` |
| Runtime shell markers and linked endpoints | `src/api/test_operator_workbench_surface.py` |
| End-to-end browser workflow | `tests/test_ui_runtime_browser_flow.py` |
| Manual analysis action | `tests/test_api_manual_analysis_trigger.py` |

## Review Use
Use this note together with `docs/ui/phase-36-web-activation-contract.md` and `docs/ui/owner_dashboard.md` when preparing any later Phase 36 roadmap or status update.
