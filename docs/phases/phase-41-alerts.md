## Title
Phase 41 alert event model

## Goal
Define the deterministic alert event contract for signal, strategy, and runtime events.

## Scope
- `AlertEvent` is the canonical pre-routing alert envelope.
- Alert severity levels are bounded to `info`, `warning`, and `critical`.
- Alert source types are bounded to `signal`, `strategy`, and `runtime`.
- Deterministic creation utilities derive `event_id` values from canonical event content.
- Signal payloads can be converted into `AlertEvent` instances without notification delivery concerns.

## AlertEvent Contract
- `schema_version`: Fixed at `1.0`.
- `event_id`: Deterministic SHA-256 based identifier prefixed with `alert_`.
- `event_type`: Stable event name such as `signal.generated`.
- `source_type`: One of `signal`, `strategy`, or `runtime`.
- `source_id`: Deterministic identifier of the originating entity.
- `severity`: One of `info`, `warning`, or `critical`.
- `occurred_at`: Required ISO-8601 timestamp string validated by the schema.
- `symbol`: Optional instrument symbol for market-linked alerts.
- `strategy`: Optional strategy identifier.
- `correlation_id`: Optional deterministic correlation identifier.
- `payload`: Structured event attributes for downstream routing and delivery systems.

## Determinism Rules
- Alert IDs are computed only from canonical event fields.
- Payload keys are normalized recursively before hashing.
- No wall-clock timestamps, random values, or notification-side fields participate in alert creation.
- Signal-derived alerts use the existing `signal_id` when present and compute it deterministically when absent.

## Repository Evidence
- Model and utilities: `src/cilly_trading/alerts/alert_models.py`
- Public package exports: `src/cilly_trading/alerts/__init__.py`
- Unit coverage: `tests/alerts/test_alert_models.py`

## Acceptance Criteria Mapping
1. AlertEvent model exists and is documented by the module contract and this phase document.
2. Signals can generate `AlertEvent` objects through `signal_to_alert_event`.
3. Unit tests cover deterministic alert creation, schema validation, and signal-to-alert conversion.
