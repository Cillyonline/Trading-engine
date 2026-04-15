# /ui Runtime Phase Ownership Boundary

## Purpose
This document defines explicit phase ownership and evidence boundaries for the shared runtime `/ui` surface.

It prevents overlap-based phase claims across Phase 36, 37, 39, 40, and 41.

## Canonical Runtime Surface
- Runtime route: `/ui`
- Served by: `src/api/main.py` static mount
- Runtime page: `src/ui/index.html`

`/ui` is one shared shell. Phase ownership is determined by bounded behavior and evidence, not by adjacency of sections on the same page.

`/ui` is also the single canonical website-facing workflow entrypoint in the bounded IA consolidation contract, with one bounded non-live signal review and trade-evaluation workflow.

Track alignment:
- Product Surface Track authority remains canonical `/ui`.
- Strategy Readiness Track remains separate and is not inferred from `/ui` phase-boundary evidence.

## /ui Section Inventory and Ownership

| Visible `/ui` section or marker | Linked backend surface(s) | Ownership classification |
| --- | --- | --- |
| Browser runtime entrypoint (`/ui`) | static mount | Phase 36 |
| Run Analysis / Analysis Results | `POST /analysis/run` | Phase 36 |
| Runtime State | `GET /system/state` | Phase 36 |
| Strategy Reference | `GET /strategies` | Phase 36 |
| Latest Signals | `GET /signals` | Shared-shell input (not phase-authoritative by itself) |
| Watchlist Management / Saved Watchlists | `POST/GET/PUT/DELETE /watchlists`, `GET /watchlists/{watchlist_id}` | Phase 37 |
| Execute Watchlist / Watchlist Ranked Results | `POST /watchlists/{watchlist_id}/execute` | Phase 37 |
| Journal Artifacts / Decision Trace | `GET /journal/artifacts`, `GET /journal/decision-trace` | Shared-shell evidence navigation |
| Runtime Lifecycle | `GET /execution/orders` | Shared-shell evidence navigation |
| Recent Alerts card (`id="alert-status"`, `id="alert-list"`) | `GET /alerts/history` | Shared-shell read-only inspection boundary |

The `/ui` primary navigation contract is explicitly bounded to one signal review/trade-evaluation workflow with these governed steps:
- `Signal Review Workflow Step 1: Run Analysis`
- `Signal Review Workflow Step 2: Configure Watchlist Scope`
- `Signal Review Workflow Step 3: Evaluate Ranked Signals`
- `Signal Review Workflow Step 4: Inspect Backtest Artifacts`
- `Signal Review Workflow Step 5: Inspect Runtime Data`
- `Signal Review Workflow Step 6: Review Run Evidence`

This navigation contract does not imply live trading, broker execution, trader validation, or operational readiness.
Technical signal visibility and ranked signal output remain separate from trader validation and operational readiness claims.

## Evidence Boundaries by Phase

### Phase 36
What `/ui` evidence proves:
- Backend-served browser activation and bounded operator runtime workflow.
- Read-only runtime inspection plus manual analysis trigger path.

What `/ui` evidence does not prove:
- Watchlist persistence/execution ownership (Phase 37).
- Chart-panel UI implementation ownership (Phase 39).
- Trading desk implementation ownership (Phase 40).
- Alert delivery/notification ownership (Phase 41).

### Phase 37
What `/ui` evidence proves:
- Watchlist CRUD, persisted watchlist selection, bounded execution, deterministic ranked rendering.

What `/ui` evidence does not prove:
- Phase 39 chart-panel implementation.
- Phase 40 trading-desk completion.
- Phase 41 notification delivery completion.

### Phase 39
What `/ui` evidence proves:
- `/ui` remains a valid shared shell containing analysis/watchlist/signal inputs consumed by the chart-data contract.

What `/ui` evidence does not prove:
- Dedicated chart-panel markers or chart-widget runtime implementation.

Authoritative Phase 39 evidence in this repository:
- `docs/operations/api/runtime_chart_data_contract.md`
- `src/api/chart_contract.py`
- `tests/test_api_phase39_chart_contract.py`

### Phase 40
What `/ui` evidence proves:
- There is a shared operator shell that can host future desk capabilities.

What `/ui` evidence does not prove:
- Heatmaps, leaderboard, richer opportunity dashboard views, or full desk workflow completion.

### Phase 41
What `/ui` evidence proves:
- Read-only alert-history inspection panel wired to `GET /alerts/history`.

What `/ui` evidence does not prove:
- Notification delivery system completion (routing, dispatch, subscriptions, external channels, browser notifications).

## Runtime Marker Verification Contract
The runtime-marker tests for this boundary use currently implemented markers only:
- `src/api/test_operator_workbench_surface.py`
- `tests/test_ui_runtime_browser_flow.py`

They verify:
- `/ui` reachability
- bounded Phase 36 and Phase 37 markers
- explicit non-expansion text (`No Phase 39 or Phase 40 features`)
- alert history markers as shared-shell inspection markers

They must not infer Phase 39 chart-panel implementation, Phase 40 desk completion, or Phase 41 delivery completion from section adjacency.
