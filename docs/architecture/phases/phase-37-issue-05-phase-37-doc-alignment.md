## Title
Phase 37 status and contract alignment

## Suggested labels
`phase:37`, `docs`, `governance`

## Suggested milestone
`Phase 37B - Watchlist Product Surface`

## Goal
Document the repository-verified Phase 37 contract and status using the implementation evidence produced by the watchlist foundation, API, and `/ui` issues.

## Context (optional)
Phase 36 explicitly excludes watchlist CRUD, persistence, ranking, and dedicated watchlist management UI. Once those artifacts exist, the repository needs a canonical Phase 37 status/contract update.

## IN SCOPE
- Add a dedicated Phase 37 contract or status artifact
- Update roadmap wording to reflect repository-verified implementation reality
- Update `/ui` and API documentation to distinguish Phase 37 from later phases
- Link evidence to the implemented code and tests

## OUT OF SCOPE
- Implementing missing watchlist functionality
- Market data provider expansion
- Charting, alerts, or trading-desk product claims
- Rewriting unrelated roadmap phases

## Acceptance Criteria
1. A canonical Phase 37 documentation artifact exists and states the verified scope in repository terms.
2. Roadmap wording for Phase 37 is aligned with actual code and tests, without overstating later phases.
3. The `/ui` and API docs describe the bounded watchlist workflow consistently.
4. The documentation points to repository evidence for watchlist CRUD, persistence, execution, ranking, and `/ui` behavior.

## Test Requirements
- Documentation review against implemented endpoints, runtime page markers, and tests
- No contradictory wording remains in the touched docs for Phase 37 scope

## Files allowed to change
- docs/roadmap/**
- docs/ui/**
- docs/api/**
- docs/phases/**
- docs/index.md

## Files NOT allowed to change
- src/**
- tests/**
- frontend/**

## Notes / Risks
Keep status wording evidence-based. Do not mark later phases as implemented through implication.
