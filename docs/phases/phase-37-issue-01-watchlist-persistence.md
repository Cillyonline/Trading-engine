## Title
Watchlist persistence contract and repository

## Suggested labels
`phase:37`, `api`, `testing`

## Suggested milestone
`Phase 37A - Watchlist Foundation`

## Goal
Introduce a deterministic watchlist persistence boundary so named watchlists and their symbol membership can be stored and read by the runtime without changing the existing engine architecture.

## Context (optional)
Phase 37 is currently only partially implemented. Engine-level multi-asset analysis already exists, but no repository-verified watchlist CRUD or persistence layer has been confirmed.

## IN SCOPE
- Define a watchlist persistence model suitable for local SQLite-backed storage
- Implement repository methods for create, list, read, update, and delete watchlists
- Preserve deterministic symbol ordering and stable identifiers
- Add focused repository tests for CRUD and ordering behavior

## OUT OF SCOPE
- New execution architecture
- UI work
- Ranking response contracts
- Roadmap or status documentation changes beyond code comments if strictly required

## Acceptance Criteria
1. A watchlist can be created with a stable identifier, a human-readable name, and a symbol list.
2. A stored watchlist can be read back with deterministic symbol ordering.
3. A watchlist can be updated and deleted through the repository boundary.
4. Repository tests cover create, read, list, update, delete, duplicate-name or duplicate-id handling, and empty-symbol validation behavior.

## Test Requirements
- Add repository-focused pytest coverage for watchlist CRUD behavior
- Verify deterministic ordering for symbols and list results
- Verify failure behavior does not partially persist invalid watchlists

## Files allowed to change
- src/cilly_trading/repositories/**
- src/cilly_trading/db/**
- tests/**

## Files NOT allowed to change
- src/ui/**
- frontend/**
- docs/roadmap/**
- docs/ui/**
- engine/**

## Notes / Risks
Keep the implementation local and SQLite-backed. Do not introduce a new storage subsystem or external service dependency.
