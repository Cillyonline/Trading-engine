# Bounded Alert Delivery Channels

Status: Bounded operational scope (Phase 41)
Owner: Alerts subsystem

## Purpose

Document the bounded external delivery channels that complete the existing
alert workflow. These channels make alerting practically useful for operators
without expanding scope into live trading, broker execution, or uncontrolled notification platforms.

## Non-live and Non-readiness Boundary

The bounded alert delivery surface is **explicitly not** a live trading,
broker, or production-readiness signal. In particular:

- No bounded delivery channel performs broker integration or order execution.
- No bounded delivery channel implies the engine is approved for live trading,
  paper-trading promotion, or profitability claims.
- All deliveries are recorded under `delivery_mode="bounded_non_live"` and the
  `/alerts/dispatches` API responses always carry `live_routing: false`.
- Channel registration is closed: only the channels listed below participate
  in dispatch. There is no dynamic plugin discovery surface.

## Registered Channels

### 1. `bounded_non_live` (default)

The original bounded, deterministic, no-op channel. It validates the alert
event identity and records a successful delivery without performing any
external I/O. It remains the default channel and preserves all previously
documented dispatch semantics.

### 2. `file_sink` (opt-in external sink)

A bounded external delivery channel that appends one JSON object per
delivered alert event to a local JSONL file. It is enabled only when the
operator opts in by setting the `CILLY_ALERT_FILE_SINK_PATH` environment
variable to a writable filesystem path before the API process starts.

Properties:

- Append-only JSONL output. One alert event per line.
- Local filesystem only. No network I/O. No webhook or third-party platform
  integration.
- Deterministic content: the line is the canonical
  `AlertEvent.model_dump_json()` representation of the dispatched event.
- Audit-friendly: each successful delivery is also recorded in the
  `alert_delivery_history` table via the existing delivery-result persistence
  path.
- Failure-aware: write failures (for example a missing parent directory when
  parent creation is disabled, or a non-directory blocking the parent path)
  are caught by the dispatcher, recorded as `delivered=false` rows in the
  delivery history, and surfaced through the `/alerts/delivery-results` and
  `/alerts/dispatches` APIs without aborting the dispatch fan-out to other
  channels.

Configuration:

| Variable                       | Description                                            | Default        |
| ------------------------------ | ------------------------------------------------------ | -------------- |
| `CILLY_ALERT_FILE_SINK_PATH`   | Absolute or relative path to the JSONL sink file.      | unset (off)    |

When the variable is unset or empty, the file sink channel is not registered
and dispatch behaviour is byte-identical to the prior bounded baseline.

## Dispatch Semantics

`POST /alerts/dispatches` and `AlertDeliveryService.dispatch_event(event)`:

1. Fan out the event to every registered channel in deterministic
   `channel_name` order.
2. Capture per-channel success or failure as `ChannelDeliveryResult`.
3. Persist one row per channel into `alert_delivery_history` with
   `delivery_mode="bounded_non_live"`.
4. Return the aggregate `AlertDispatchResult` with explicit `delivered` and
   `error` values per channel; `live_routing` is always `false`.

The `/alerts/delivery-results` read surface continues to expose the persisted
per-channel rows, including failures. The `/alerts/history` read surface
continues to expose the underlying `AlertEvent` records exactly as before.

## Backwards Compatibility

- Default behaviour without `CILLY_ALERT_FILE_SINK_PATH` is unchanged:
  exactly one `bounded_non_live` delivery row per dispatched event.
- Existing alert configuration CRUD endpoints are unchanged.
- Existing alert-history and delivery-results read surfaces are unchanged in
  shape, ordering, and pagination behaviour.

## Test Coverage

Regression coverage lives alongside the rest of the alert workflow tests:

- `tests/alerts/test_file_sink_channel.py` — unit tests for the file sink
  channel itself, the delivery service success path, the explicit failure
  path, and the unchanged default channel set.
- `tests/integration/test_alert_file_sink_delivery.py` — end-to-end coverage
  through the `/alerts/dispatches` and `/alerts/delivery-results` APIs for
  both the success path (JSONL line written, two delivery rows persisted)
  and the failure path (file sink failure is surfaced and persisted while
  the bounded non-live channel still succeeds).
- `tests/alerts/test_bounded_alert_delivery_mvp.py` and
  `tests/integration/test_alert_delivery_lifecycle.py` continue to cover the
  default bounded baseline and restart-safety contract.
