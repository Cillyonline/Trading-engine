Closes #935

## Scope
Implements a single deterministic, bounded, explicitly non-live alert delivery path with SQLite-backed persistence for alert configuration and delivery history.

## What changed
- Added bounded channel `bounded_non_live` with no external/live routing.
- Added `AlertDeliveryService` for deterministic event dispatch and persisted delivery results.
- Added SQLite repositories:
  - `SqliteAlertConfigurationRepository`
  - `SqliteAlertDeliveryHistoryRepository`
- Updated alert API/state wiring to use persistence-backed stores.
- Added bounded dispatch endpoint: `POST /alerts/dispatches`.
- Added bounded delivery-results read endpoint: `GET /alerts/delivery-results`.
- Added tests for:
  - deterministic event -> dispatch -> persisted delivery result
  - restart-safe persistence integrity
  - invalid alert configuration rejection
  - API lifecycle coverage for dispatch/history/config persistence

## Acceptance criteria mapping
- AC1: Single deterministic bounded channel implemented (`bounded_non_live`)
- AC2: E2E flow tested through API and persistence (`/alerts/dispatches` -> `/alerts/delivery-results`)
- AC3: Restart persistence tested for config/history/delivery results
- AC4: Delivery path explicitly non-live (`delivery_mode=bounded_non_live`, `live_routing=false`)
- AC5: No P56/runtime/engine/strategy scope impact

## Governance
- Codex A review decision: APPROVED
- Classification: technically good, but traderically weak
- Roadmap maintenance due after merge because Phase 41 should no longer remain pure `Planned`

## Test evidence
- Command: `python -m pytest`
- Result: `1029 passed, 4 warnings`
