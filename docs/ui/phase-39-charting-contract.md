# Phase 39 /ui Charting Contract

## Purpose
This document is the canonical Phase 39 charting and visual-analysis contract for the runtime-served `/ui` surface.

It defines the bounded Phase 39 scope without claiming that chart components are already implemented in the repository today.

This contract is normative for Phase 39 documentation. It must stay aligned with the current `/ui` runtime shell, the already implemented runtime API surface, and the existing runtime-facing docs that govern `/ui`.

## Current Repository State
- `/ui` is the canonical runtime-served browser surface.
- The current runtime shell is still the Phase 36 and Phase 37 workbench described in `docs/ui/phase-36-web-activation-contract.md`, `docs/ui/owner_dashboard.md`, and `docs/phases/phase-37-status.md`.
- No repository-verified Phase 39 chart component or visual-analysis panel is currently claimed by `src/ui/index.html` or the existing `/ui` tests.
- The current `/ui` shell explicitly states that it exposes no Phase 39 or Phase 40 features.

This file therefore defines the allowed Phase 39 contract boundary for later work on `/ui`; it does not change the current implementation status.

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
| Runtime-backed visualization | Render read-only visual views of data already returned by the current runtime/API surface | `/system/state`, `/signals`, `/strategies`, `/journal/artifacts`, `/journal/decision-trace`, `/execution/orders`, `/watchlists`, `POST /watchlists/{watchlist_id}/execute`, `POST /analysis/run` |
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
- any claim that the current repository already contains verified Phase 39 chart components

If a charting claim depends on those capabilities, it belongs to a later issue and later evidence set.

## Evidence Pointers
Use these repository artifacts when reviewing Phase 39 wording:

| Evidence area | Repository basis |
| --- | --- |
| Runtime `/ui` route boundary | `src/api/main.py` mounts `/ui` as the backend-served browser surface |
| Current `/ui` shell markers | `src/ui/index.html` contains the current workbench sections and explicitly states that no Phase 39 or Phase 40 features are exposed there today |
| Runtime `/ui` shell verification | `src/api/test_operator_workbench_surface.py` verifies the `/ui` shell markers, route references, and the "No Phase 39 or Phase 40 features" boundary text |
| Browser workflow verification | `tests/test_ui_runtime_browser_flow.py` verifies the existing `/ui` browser workflow against the current runtime API surface |
| Phase 36 boundary | `docs/ui/phase-36-web-activation-contract.md` defines the bounded Phase 36 `/ui` workflow |
| Current runtime workbench inventory | `docs/ui/owner_dashboard.md` documents the current `/ui` shell and backend-connected workflow |
| Phase 37 boundary | `docs/phases/phase-37-status.md` defines the bounded watchlist workflow already present on `/ui` |
| Roadmap status context | `docs/roadmap/cilly_trading_execution_roadmap_updated.md` records Phase 39 as planned rather than implemented |

## Review Checklist
Reviewers should verify:

1. The contract keeps `/ui` as the only canonical runtime-served browser surface for Phase 39 work.
2. Every allowed Phase 39 capability is read-only, browser-rendered, and anchored to an already documented runtime/API surface.
3. The contract does not claim any current chart implementation in `src/ui/index.html` or the existing `/ui` tests.
4. The exclusions explicitly block Phase 40 trading-desk claims, alerts, Strategy Lab, paper-trading product workflow, and live-trading workflow claims.
5. The wording stays consistent with the existing Phase 36 and Phase 37 `/ui` documentation.

## Outcome
For Phase 39, the canonical bounded contract is:

- stay on `/ui`
- visualize only repository-governed runtime data already reachable from `/ui`
- keep the experience read-only and evidence-linked
- stop before Phase 40 desk expansion, alerts, Strategy Lab, paper-trading product workflow, and live-trading claims
