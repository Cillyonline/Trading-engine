## Title
Runtime /ui watchlist management and execution flow

## Suggested labels
`phase:37`, `ui`, `testing`

## Suggested milestone
`Phase 37B - Watchlist Product Surface`

## Goal
Extend the backend-served `/ui` runtime surface with a dedicated watchlist management and execution workflow for Phase 37.

## Context (optional)
Phase 36 explicitly stops before watchlist CRUD, persistence, ranking, and dedicated watchlist UI. This issue adds only the bounded browser workflow needed for Phase 37.

## IN SCOPE
- Add watchlist management UI to the runtime-served `/ui` surface
- Allow creating, selecting, editing, deleting, and executing watchlists from the browser
- Render ranked watchlist results using the new API surface
- Add focused runtime-surface tests for the new watchlist workflow

## OUT OF SCOPE
- `/owner` runtime routing
- Charting or visual-analysis widgets
- Trading-desk heatmaps or leaderboard views
- Alerts, paper trading, or live trading controls

## Acceptance Criteria
1. `/ui` exposes a watchlist section that supports create, list, update, delete, and execute actions against the backend runtime API.
2. The browser surface renders ranked watchlist results for a completed watchlist run.
3. The watchlist workflow remains clearly bounded to Phase 37 and does not claim Phase 39 or Phase 40 features.
4. Runtime-surface tests verify the new watchlist UI markers and the wired API workflow.

## Test Requirements
- Add or extend `/ui` runtime surface tests
- Verify the watchlist controls are present in the backend-served page
- Verify the browser workflow uses the watchlist API rather than ad hoc client-only state

## Files allowed to change
- src/ui/index.html
- src/api/main.py
- src/api/test_operator_workbench_surface.py
- tests/test_ui_runtime_browser_flow.py
- tests/**

## Files NOT allowed to change
- frontend/src/**
- docs/roadmap/**
- docs/phases/**
- src/cilly_trading/engine/marketdata/**
- src/cilly_trading/engine/backtest_runner.py

## Notes / Risks
`/ui` remains the canonical runtime surface. Do not reframe `/owner` as a backend runtime route.
