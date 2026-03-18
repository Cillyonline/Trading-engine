## Title
Phase 41 operator dashboard alert history panel

## Goal
Add a deterministic read-only alert history API and panel to the operator dashboard so operators can inspect recent alert events without accessing logs.

## Scope
- Implement a read-only API endpoint at `/alerts/history` returning deterministic alert events sorted by `occurred_at` descending.
- Ensure the endpoint supports pagination (`limit`, `offset`) and returns read-only results.
- Add an operator dashboard alert panel in `/ui` that fetches `/alerts/history` and renders events.
- Show deterministic rendering behavior for loaded state, empty state, and error state.
- Keep all changes read-only on runtime data and do not alter alert generation logic.

## Alert History API Contract
- URI: `GET /alerts/history`
- Authorization: `X-Cilly-Role: read_only` required.
- Query params:
  - `limit` (int, default 20, max 200)
  - `offset` (int, default 0)
- Response shape:
  - `items`: list of deterministic `AlertEvent` objects
  - `total`: total count of stored alert events
- Ordering: deterministic descending by `occurred_at` then `event_id` as a tiebreaker.

## Dashboard UI Contract
- `/ui` includes a Recent Alerts card with:
  - Table header columns: Occurred, Severity, Event Type, Symbol, Source
  - Empty-state placeholder when no events exist.
  - Error message when fetch fails.
- UI uses read-only header for fetch requests.

## Acceptance Criteria Mapping
1. `/alerts/history` endpoint exists and is read-only.
2. API response is deterministic and sorted by `occurred_at` descending.
3. Operator dashboard displays recent alerts using `/alerts/history`.
4. Dashboard renders deterministic empty-state and error-state.
5. UI integration tests verify alert panel and API integration.
6. Browser flow tests validate dashboard and endpoint presence.
