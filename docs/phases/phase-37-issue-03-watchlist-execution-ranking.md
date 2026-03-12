## Title
Watchlist execution and ranking workflow

## Suggested labels
`phase:37`, `api`, `testing`

## Suggested milestone
`Phase 37A - Watchlist Foundation`

## Goal
Add a dedicated watchlist execution workflow that runs analysis for a persisted watchlist and returns deterministic ranked results suitable for later UI consumption.

## Context (optional)
The engine already supports watchlist-style multi-symbol analysis, but no full Phase 37 product workflow has been verified for persisted watchlists and ranking output.

## IN SCOPE
- Connect persisted watchlists to the existing analysis orchestration
- Add a dedicated endpoint to execute analysis for a saved watchlist
- Define and return a deterministic ranking/result payload for the watchlist run
- Add tests for ranking order, symbol isolation, and empty-result behavior

## OUT OF SCOPE
- New strategy logic
- New market data provider integrations
- UI rendering
- Heatmaps, leaderboards, or trading-desk features

## Acceptance Criteria
1. A saved watchlist can be analyzed through a dedicated API path using the existing engine orchestration.
2. The response contains deterministic ranked results derived from the produced signals.
3. Symbol-level failures remain isolated and do not crash the whole watchlist run unless the whole request is invalid.
4. Tests cover ranking order, empty-result behavior, and partial-failure isolation.

## Test Requirements
- Add API and/or engine integration tests for persisted-watchlist execution
- Verify deterministic ordering for ranked items
- Verify existing screener behavior is not regressed by the new watchlist path

## Files allowed to change
- src/api/main.py
- src/cilly_trading/engine/core.py
- src/cilly_trading/repositories/**
- tests/**
- docs/api/usage_contract.md

## Files NOT allowed to change
- src/ui/**
- frontend/**
- docs/ui/**
- docs/roadmap/**
- src/cilly_trading/engine/marketdata/**

## Notes / Risks
This issue must stay within the current engine boundaries. Reuse existing orchestration instead of introducing a second execution path.
