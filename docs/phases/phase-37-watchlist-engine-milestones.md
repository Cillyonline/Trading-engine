# Phase 37 Watchlist Engine Milestones

## Milestone 1

**Title:** `Phase 37A - Watchlist Foundation`

**Purpose**

Create the persistence, API, and execution foundations for watchlists without overstating the broader product workflow.

**Exit Condition**

Watchlists are storable, readable, updatable, deletable, and executable through a bounded API path that returns deterministic ranked results.

**Planned Issues**

1. `Watchlist persistence contract and repository`
2. `Watchlist CRUD API surface`
3. `Watchlist execution and ranking workflow`

## Milestone 2

**Title:** `Phase 37B - Watchlist Product Surface`

**Purpose**

Extend the runtime-served `/ui` surface with watchlist management and align the repository documentation to Phase 37 implementation evidence.

**Exit Condition**

An operator can manage and execute watchlists from the runtime-served `/ui`, review ranked results, and the repository documentation reflects the verified Phase 37 scope without implying later phases.

**Planned Issues**

1. `Runtime /ui watchlist management and execution flow`
2. `Phase 37 status and contract alignment`

## Suggested GitHub Creation Order

1. Create milestone `Phase 37A - Watchlist Foundation`
2. Create milestone `Phase 37B - Watchlist Product Surface`
3. Create label `phase:37`
4. Create the five issues and assign them to the milestones in package order
