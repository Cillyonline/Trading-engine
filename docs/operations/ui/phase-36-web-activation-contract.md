# Phase 36 /ui Web Activation Contract

## Purpose
This document is the canonical Phase 36 contract for the runtime-served `/ui` surface.

It fixes four things for audit and status review:

- `/ui` is the only canonical runtime browser entrypoint for this phase
- the supported browser workflow is limited to the repository-verifiable flow already implemented
- `/owner` is separated from the runtime contract
- later phases such as 37 and 40 are not implied by the presence of UI sections in the current shell

This contract is normative for Phase 36 documentation. It must stay aligned with `src/api/main.py`, `src/ui/index.html`, and the existing tests for those surfaces.

## Canonical Runtime Surface
- Canonical runtime URL: `/ui`
- Serving mechanism: FastAPI static mount
- Runtime page source: `src/ui/index.html`

For Phase 36, `/ui` is the runtime-served browser surface. No other route is an equivalent runtime activation URL.

## Supported Browser Workflow
Phase 36 documents one bounded browser workflow that is implemented today:

1. Open the backend-served runtime workbench at `/ui`.
2. Load the read-only runtime context already fetched by the page:
   - `GET /system/state`
   - `GET /strategies`
   - `GET /signals`
   - `GET /journal/artifacts`
   - `GET /execution/orders`
3. Submit the browser-triggered manual analysis request from the `/ui` form through `POST /analysis/run`.
4. Review the returned analysis result in-browser, including the deterministic `analysis_run_id` and any emitted signals.
5. Inspect related evidence in the same `/ui` session through journal artifact preview, decision trace lookup, and trade lifecycle visibility.

This is a bounded runtime workflow. It is not a claim that Phase 36 already provides a broader browser-native product surface beyond the implemented `/ui` workbench.

## Runtime-Reachable Phase 36 Surfaces
The following surfaces are in scope because the current `/ui` page reaches them directly and repository tests verify the route family:

| Phase 36 area | Current runtime behavior through `/ui` | Repository-verifiable surface |
| --- | --- | --- |
| Runtime shell | Browser page is served from the backend runtime | `/ui` |
| Runtime state | Read-only runtime summary is loaded automatically | `GET /system/state` |
| Analysis trigger | Browser form submits a manual runtime analysis request | `POST /analysis/run` |
| Analysis results | Returned run id and signals are rendered in-browser | `POST /analysis/run` response |
| Strategy reference | Read-only strategy metadata table | `GET /strategies` |
| Latest signals | Read-only signal list | `GET /signals` |
| Journal artifact list | Read-only artifact browser | `GET /journal/artifacts` |
| Journal artifact preview | Artifact content preview after selection | `GET /journal/artifacts/{run_id}/{artifact_name}` |
| Decision trace | Read-only trace view for a selected artifact | `GET /journal/decision-trace` |
| Trade lifecycle | Read-only order lifecycle view | `GET /execution/orders` |

The current `/ui` shell also visibly includes Overview, Runtime Status, Analysis Runs, Screener, and Audit Trail labels. Their presence in the shell is Phase 36 evidence only for browser activation and section visibility. It is not evidence of later product-scope completion unless separate repository artifacts verify that behavior.

## /owner Boundary
`/owner` is outside the Phase 36 runtime contract.

That means:

- `/owner` is not a runtime-served backend entrypoint
- `/owner` is not an accepted alternative to `/ui`
- `/owner` must not be cited as the Phase 36 browser activation URL
- frontend route definitions do not redefine the runtime contract

## Later-Phase Boundary
Phase 36 stops at the bounded `/ui` workflow above.

The following remain out of scope for this phase:

- Phase 37 watchlist product behavior such as watchlist CRUD, persistence, ranking, or dedicated watchlist management UI
- Phase 40 trading-desk expansion such as heatmaps, leaderboard views, richer opportunity dashboards, or a broader professional desk workflow
- alerts or notifications
- Strategy Lab workflows
- paper-trading product workflows
- live-trading workflows
- broker integration

If a browser claim depends on those capabilities, it belongs to a later issue and later evidence set.

## Acceptance Evidence
The following repository evidence is sufficient to support later Phase 36 status review without inventing extra scope:

| Evidence area | Repository basis |
| --- | --- |
| Runtime entrypoint | `src/api/main.py` mounts `/ui` with `StaticFiles(..., html=True)` |
| Browser workflow | `src/ui/index.html` loads `/system/state`, `/strategies`, `/signals`, `/journal/artifacts`, `/journal/decision-trace`, `/execution/orders`, and submits `POST /analysis/run` |
| Route reachability tests | `tests/health_endpoint.py`, `src/api/test_operator_workbench_surface.py`, and `tests/test_ui_runtime_browser_flow.py` verify the `/ui` surface and its browser workflow |
| Manual analysis behavior | `tests/test_api_manual_analysis_trigger.py` verifies the deterministic `POST /analysis/run` flow |
| Scope guard | The implemented `/ui` page and the listed tests do not verify watchlist CRUD, trading-desk expansion, alerts, paper-trading product workflow, or live-trading workflow |

## Review Checklist
Reviewers should verify:

1. `src/api/main.py` still mounts `/ui` as the runtime-served browser surface.
2. `src/ui/index.html` still implements the bounded Phase 36 workflow described here.
3. `/owner` is not presented anywhere as a runtime-equivalent route.
4. The docs remain silent on unimplemented watchlist, trading-desk, alerts, paper-trading product, and live-trading claims.
5. Roadmap wording and runtime-facing wording both describe Phase 36 as bounded browser activation rather than later-phase feature completion.

## Outcome
For Phase 36, the canonical runtime contract is:

- enter through `/ui`
- use the implemented browser workflow already served by the backend
- inspect runtime data and trigger bounded manual analysis in-browser
- stop before watchlist-engine and trading-desk feature expansion claimed by later phases
