# Phase 36 Web Activation Evidence

## Purpose
This note records repository-verifiable evidence for bounded Phase 36 status review.

## Canonical Runtime Surface
- Canonical runtime browser URL: `/ui`
- Served by: FastAPI static mount in `src/api/main.py`
- Runtime page source: `src/ui/index.html`

`/ui` is the Phase 36 runtime-served browser surface. `/owner` is not the canonical runtime entrypoint.

## Supported Phase 36 Browser Workflow
The repository verifies this bounded workflow:

1. Open `/ui`.
2. Load runtime context from:
   - `GET /system/state`
   - `GET /strategies`
   - `GET /signals`
   - `GET /journal/artifacts`
   - `GET /execution/orders`
3. Submit manual analysis through `POST /analysis/run`.
4. Review returned `analysis_run_id` and signals.
5. Inspect artifact preview, decision trace, and lifecycle evidence.

## Phase Boundary
The current `/ui` shell is Phase 36 evidence for browser activation and manual-analysis runtime workflow only.

It is not, by itself, evidence of:
- Phase 37 ownership
- Phase 39 chart-panel UI ownership
- Phase 40 desk completion
- Phase 41 notification-delivery completion

Shared-shell phase ownership rules are defined in:
- `docs/architecture/ui-runtime-phase-ownership-boundary.md`

## Repository Evidence
| Evidence area | Repository basis |
| --- | --- |
| Runtime entrypoint | `src/api/main.py` mounts `/ui` |
| Browser workflow | `src/ui/index.html` includes the bounded runtime flow |
| `/ui` route reachability | `tests/health_endpoint.py` |
| Runtime shell markers and linked endpoints | `src/api/test_operator_workbench_surface.py` |
| End-to-end browser workflow | `tests/test_ui_runtime_browser_flow.py` |
| Manual analysis action | `tests/test_api_manual_analysis_trigger.py` |

## Review Use
Use this note together with:
- `docs/operations/ui/phase-36-web-activation-contract.md`
- `docs/operations/ui/owner_dashboard.md`
- `docs/architecture/ui-runtime-phase-ownership-boundary.md`

