## Title
Watchlist CRUD API surface

## Suggested labels
`phase:37`, `api`, `testing`

## Suggested milestone
`Phase 37A - Watchlist Foundation`

## Goal
Expose a bounded operator-facing API for watchlist CRUD on top of the new watchlist repository boundary.

## Context (optional)
The current API already supports manual analysis and screener access, but there is no verified watchlist management surface for Phase 37.

## IN SCOPE
- Add watchlist create, list, read, update, and delete endpoints
- Reuse the existing local/operator API style in `src/api/main.py`
- Apply the existing role model consistently to the new endpoints
- Add focused API tests for allowed, forbidden, and invalid requests

## OUT OF SCOPE
- Browser workflow implementation in `/ui`
- Watchlist execution/ranking behavior beyond CRUD
- Charting, alerts, or portfolio simulation
- Broad access-policy redesign

## Acceptance Criteria
1. The API exposes bounded watchlist CRUD endpoints with deterministic request and response shapes.
2. Operator and owner roles may perform watchlist mutation; read_only may only inspect watchlists if a read endpoint is exposed.
3. Invalid payloads return deterministic validation errors and do not partially persist state.
4. API tests cover success, validation failure, unauthorized, and forbidden cases.

## Test Requirements
- Add FastAPI tests for each CRUD endpoint
- Verify role enforcement matches the current access-policy style
- Verify list responses and symbol arrays are deterministic

## Files allowed to change
- src/api/main.py
- src/api/test_*.py
- src/cilly_trading/repositories/**
- tests/**

## Files NOT allowed to change
- src/ui/**
- frontend/**
- docs/roadmap/**
- docs/ui/**
- src/cilly_trading/engine/**

## Notes / Risks
Keep endpoint naming and response style aligned with existing API conventions. Do not redesign unrelated request models.
