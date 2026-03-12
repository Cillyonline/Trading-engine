# Phase 36 /ui Web Activation Contract

## Purpose
This document is the canonical Phase 36 runtime contract for the browser-served `/ui` surface.

It defines:

- the fixed runtime entrypoint for Phase 36
- the minimum browser workflow covered by this phase
- the runtime capabilities that must be reachable through `/ui`
- the boundary between Phase 36 and later roadmap phases

This contract is normative for Phase 36 documentation and review. It must be read against the current repository-verified runtime behavior in `src/ui/index.html`, `src/api/main.py`, and the existing tests covering those surfaces.

## Canonical Runtime Entrypoint
- Canonical browser runtime entrypoint: `/ui`
- Served by: backend FastAPI static mount
- Runtime source: `src/ui/index.html`

For Phase 36, `/ui` is the only canonical browser runtime surface.

`/owner` is not part of the Phase 36 runtime surface. If it exists in frontend development code, it remains a development-only route and must not be treated as a runtime URL, fallback runtime entrypoint, or equivalent browser activation path.

## Minimum Browser Workflow
Phase 36 covers one bounded browser workflow:

1. Open the backend-served workbench at `/ui`.
2. Land on the runtime shell that identifies itself as the FastAPI-served operator workbench.
3. Use the browser surface to inspect currently reachable runtime data that the page already loads from the backend.
4. Navigate within the bounded runtime sections exposed by the current `/ui` page.
5. Review the returned runtime data in-browser without requiring a separate frontend-only route.

This phase does not require a full browser-native product workflow. It only requires that the browser runtime surface is fixed, documented, and bounded around the currently verifiable `/ui` behavior.

## Required Runtime Views And Actions
The following runtime views are covered by Phase 36 because they are repository-verifiable from the current `/ui` page and backend routes.

| Phase 36 area | Reachability requirement through `/ui` | Repository-verifiable backend surface |
| --- | --- | --- |
| Runtime shell | `/ui` loads the browser workbench shell | `/ui` static mount |
| Strategies | Reachable as a read-only table in the browser | `GET /strategies` |
| Signals | Reachable as a read-only table in the browser | `GET /signals` |
| Journal artifact list | Reachable as a read-only artifact browser in the browser | `GET /journal/artifacts` |
| Journal artifact preview | Reachable by selecting an artifact in the browser | `GET /journal/artifacts/{run_id}/{artifact_name}` |
| Decision trace | Reachable from selected journal artifacts in the browser | `GET /journal/decision-trace` |
| Trade lifecycle | Reachable as a read-only order timeline in the browser | `GET /execution/orders` |

The following workbench sections are part of the bounded Phase 36 shell because they are visibly present in the current `/ui` page, but this contract does not require additional product behavior beyond their current repository-verifiable shell state:

- Overview
- Runtime Status
- Analysis Runs
- Screener
- Audit Trail

Within Phase 36, these shell sections may exist as placeholders or reserved panels. This contract does not elevate them into broader workflow commitments unless the repository already verifies that behavior.

## Phase 36 Action Boundary
Phase 36 is a browser activation phase, not a browser feature expansion phase.

The contract requires browser reachability and bounded runtime inspection through `/ui`. It does not require:

- watchlist CRUD
- watchlist persistence or ranking
- alerts, notifications, or messaging
- Strategy Lab workflows
- paper-trading product workflows
- live trading workflows
- broker integration
- broader trading-desk expansion

## Explicit Later-Phase Separation
Phase 36 ends at the bounded `/ui` runtime contract described above.

The following capabilities are explicitly outside this phase and remain separated into later roadmap work:

- Phase 37: watchlist engine behavior such as watchlist CRUD, repeatable watchlist product workflow, persistence, ranking, and dedicated watchlist management UI
- Phase 40: expanded trading-desk dashboard behavior such as richer opportunity dashboards, heatmaps, leaderboard-style views, and broader professional desk workflow

If a browser feature depends on those capabilities, it is not part of Phase 36 unless the roadmap and repository evidence are updated in a later issue.

## /owner Boundary
`/owner` is out of scope for runtime use in Phase 36.

That means:

- `/owner` is not a runtime entrypoint
- `/owner` is not an accepted alternative to `/ui`
- `/owner` must not be cited as part of the Phase 36 runtime workflow
- frontend development routing does not redefine the runtime contract

## Verification Basis
This contract is intentionally limited to behavior that is reviewable in the repository today.

Reviewers should verify:

1. `src/api/main.py` mounts `/ui` as the backend-served static runtime surface.
2. `src/ui/index.html` identifies the page as the FastAPI-served workbench at `/ui`.
3. `src/ui/index.html` fetches only the runtime data surfaces claimed in this contract.
4. Existing tests verify the `/ui` route and the covered backend endpoints claimed here.
5. No statement in this contract expands Phase 36 into watchlist, trading-desk, alerting, Strategy Lab, paper-trading product, live trading, or broker-integration scope.

## Outcome
For Phase 36, the canonical browser runtime contract is:

- enter through `/ui`
- use the current backend-served browser workbench
- inspect the currently reachable runtime data surfaces already wired into that page
- stop before watchlist-engine and trading-desk expansion work that belongs to later phases
