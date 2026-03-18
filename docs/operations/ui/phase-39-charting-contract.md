# Phase 39 /ui Charting Contract

## Purpose
This document is the canonical Phase 39 charting and visual-analysis contract for the runtime-served `/ui` surface.

It defines the bounded Phase 39 scope for the implemented chart panel and visual-analysis surface on `/ui`.

This contract is normative for Phase 39 documentation. It must stay aligned with the current `/ui` runtime shell, the already implemented runtime API surface, and the existing runtime-facing docs that govern `/ui`.

The authoritative chart-data shape, reuse evaluation, and validation boundary live in `docs/operations/api/runtime_chart_data_contract.md`.
Legacy compatibility path: `docs/api/runtime_chart_data_contract.md`.

## Current Repository State
- `/ui` is the canonical runtime-served browser surface.
- The current runtime shell is still the Phase 36 and Phase 37 workbench described in `docs/operations/ui/phase-36-web-activation-contract.md`, `docs/operations/ui/owner_dashboard.md`, and `docs/architecture/phases/phase-37-status.md`.
- `src/ui/index.html` now contains a dedicated chart panel and visual-analysis surface with stable runtime markers for Phase 39 verification.
- Phase 39 chart data is defined as a projection over existing runtime API routes, not as a new chart backend.
- The current `/ui` shell explicitly limits the charting surface to Phase 39 visual analysis and blocks Phase 40 desk widgets, alerts, paper-trading workflow, and live-trading workflow claims.

This file therefore defines the allowed Phase 39 contract boundary for the implemented `/ui` chart panel and for later bounded work on the same surface.

## Canonical Runtime Surface
- Canonical runtime URL: `/ui`
- Serving mechanism: FastAPI static mount
- Runtime page source: `src/ui/index.html`

Phase 39 does not introduce a second runtime browser route. `/owner` is not an equivalent runtime charting route.

## In-Scope Phase 39 Capabilities
Phase 39 is limited to bounded, browser-rendered, read-only visual analysis on the existing runtime `/ui` workbench.

Allowed capability categories:

| Phase 39 category | Allowed bounded capability on `/ui` | Current evidence anchor |
| --- | --- | --- |
| Runtime-backed visualization | Render read-only visual views of data already returned by the current runtime/API surface | `GET /signals`, `POST /analysis/run`, `POST /watchlists/{watchlist_id}/execute`, plus existing runtime context from `/system/state`, `/strategies`, `/journal/artifacts`, `/journal/decision-trace`, `/execution/orders`, and `/watchlists` |
| Analysis result interpretation | Visualize deterministic fields already returned by analysis and watchlist execution responses, such as score, stage, rank, signal strength, and run identity | `POST /analysis/run`, `POST /watchlists/{watchlist_id}/execute` |
| Evidence-linked visual review | Let an operator move between a visual view and the existing journal, decision-trace, and trade-lifecycle evidence for the same runtime context | `/journal/artifacts`, `/journal/decision-trace`, `/execution/orders` |
| Workbench-local interaction | Support bounded browser-side selection, filtering, or switching between already loaded runtime views on the same `/ui` page | Existing `/ui` shell and browser workflow |

Phase 39 is therefore about visual interpretation of existing runtime-served evidence on `/ui`, not about expanding the product surface beyond that runtime workbench.

## Explicit Phase 39 Boundaries
The following are in scope for this contract only if they remain read-only, `/ui`-local, and tied to already governed runtime data:

- visualization of analysis results already returned by `POST /analysis/run`
- visualization of watchlist-ranked results already returned by `POST /watchlists/{watchlist_id}/execute`
- visualization of existing runtime state, signal, strategy, journal, decision-trace, and trade-lifecycle data already reachable from `/ui`
- visual annotations or highlights derived from existing deterministic payload fields already returned by the backend
- browser-side organization of those views within the existing `/ui` workbench

## Implemented Panel Boundary
The implemented chart panel on `/ui` is bounded as follows:

- dedicated stable markers: `#runtime-chart-panel`, `data-runtime-surface="chart-panel"`, `data-runtime-chart-panel="visible"`, `data-runtime-chart-boundary="phase39-visual-analysis"`, and `#runtime-chart-surface`
- visible source markers: `#chart-source-analysis-run`, `#chart-source-watchlist-execution`, and `#chart-source-latest-signals`
- active data feeds:
  - `POST /analysis/run` for manual-analysis scores and stages
  - `POST /watchlists/{watchlist_id}/execute` for ranked watchlist scores and signal strength
  - `GET /signals?limit=20&sort=created_at_desc` for fallback score visibility when no session-local analysis result has been rendered yet
- panel behavior remains read-only and browser-local; it does not create, mutate, or stream market data
- chart consumers must use the existing runtime API routes through the contract in `docs/operations/api/runtime_chart_data_contract.md`
- `GET /signals` remains fallback-only historical evidence for the chart panel because its response does not expose `ingestion_run_id`

## Explicitly Out of Scope
Phase 39 does not include:

- implementing new backend runtime behavior or new API routes solely for charting
- treating `/owner` as a runtime-equivalent charting surface
- Phase 40 trading-desk expansion such as heatmaps, leaderboard views, richer opportunity dashboards, or broader desk workflow claims
- alerts or notifications
- Strategy Lab workflows, optimization flows, or experiment-management UX
- paper-trading product workflows
- live-trading workflows
- broker controls, order entry, order cancellation, or execution-side mutation from charts
- market-data productization changes, new provider commitments, streaming feeds, or real-time market-data claims

The chart panel therefore consumes existing runtime API routes and stops before any new market-data product or dedicated chart backend claim.

If a charting claim depends on those capabilities, it belongs to a later issue and later evidence set.

## Evidence Pointers
Use these repository artifacts when reviewing Phase 39 wording:

| Evidence area | Repository basis |
| --- | --- |
| Runtime `/ui` route boundary | `src/api/main.py` mounts `/ui` as the backend-served browser surface |
| Runtime chart-data contract | `docs/operations/api/runtime_chart_data_contract.md` defines the bounded chart payload shape and the existing runtime API routes that feed it |
| Current `/ui` shell markers | `src/ui/index.html` contains the current workbench sections, chart panel markers, and explicit Phase 39 boundary text |
| Runtime `/ui` shell verification | `src/api/test_operator_workbench_surface.py` verifies the `/ui` shell markers, route references, chart-panel markers, and the "No Phase 40 desk widgets, alerts, or live trading controls" boundary text |
| Browser workflow verification | `tests/test_ui_runtime_browser_flow.py` verifies the existing `/ui` browser workflow and deterministic chart-panel markers against the current runtime API surface |
| Phase 36 boundary | `docs/operations/ui/phase-36-web-activation-contract.md` defines the bounded Phase 36 `/ui` workflow |
| Current runtime workbench inventory | `docs/operations/ui/owner_dashboard.md` documents the current `/ui` shell and backend-connected workflow |
| Phase 37 boundary | `docs/architecture/phases/phase-37-status.md` defines the bounded watchlist workflow already present on `/ui` |
| Roadmap status context | `docs/architecture/roadmap/cilly_trading_execution_roadmap_updated.md` records the bounded `/ui` chart panel as implemented in repository terms without expanding into Phase 40 desk scope |

## Review Checklist
Reviewers should verify:

1. The contract keeps `/ui` as the only canonical runtime-served browser surface for Phase 39 work.
2. Every allowed Phase 39 capability is read-only, browser-rendered, and anchored to existing runtime API routes and the chart-data contract in `docs/operations/api/runtime_chart_data_contract.md`.
3. The contract claims only the implemented bounded chart panel, the existing runtime API routes, and stable markers already verified in `src/ui/index.html` and the existing `/ui` tests.
4. The exclusions explicitly block Phase 40 trading-desk claims, alerts, Strategy Lab, paper-trading product workflow, and live-trading workflow claims.
5. The wording stays consistent with the existing Phase 36 and Phase 37 `/ui` documentation and keeps `GET /signals` fallback-only rather than authoritative snapshot state.

## Outcome
For Phase 39, the canonical bounded contract is:

- stay on `/ui`
- visualize only repository-governed runtime data already reachable from `/ui`
- keep the experience read-only and evidence-linked
- stop before Phase 40 desk expansion, alerts, Strategy Lab, paper-trading product workflow, and live-trading claims
