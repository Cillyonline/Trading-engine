# Phase 12 – Engine ↔ API Runtime Integration: Scope Declaration

## Goal
Phase 12 integrates the engine runtime lifecycle into the API layer so process startup and shutdown correctly coordinate runtime availability. This work builds on the already tested lifecycle foundation from Phase 11 and brings it into API execution flow. The objective is to ensure request handling behavior is governed by runtime state without introducing unrelated functional changes.

## Background
Phase 11 introduced an explicit, tested engine runtime lifecycle.

## In Scope
- Engine runtime integration into API startup and shutdown
- Runtime state guarding for API request handling

## Out of Scope (Non-Goals)
- New API endpoints
- Strategy or trading logic
- Performance, observability, or refactoring

## Integration Boundaries
Runtime integration happens only within the API process lifecycle at start and stop. It does not include broader application bootstrapping concerns outside runtime lifecycle wiring.

At API request handling time, state guarding means requests are only allowed or denied based on current runtime state. This boundary is limited to gating request handling behavior and does not introduce new request types or processing paths.

Phase 12 does not add endpoints, does not implement or alter strategy/trading logic, and does not include performance work, observability changes, or refactoring.

## Exit Criteria (Ready for Execution Issues)
- Scope declaration document exists for Phase 12 runtime integration
- Integration boundaries are explicitly defined and unambiguous
- Non-goals are clearly documented and separated from in-scope work
- Execution issues can proceed for A1, A2, and A3 within this declared scope
