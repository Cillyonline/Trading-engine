# Alerts API

The alert API exposes deterministic, in-memory alert configuration endpoints for operators and read-only retrieval endpoints for inspection, including recent alert event history for the operator dashboard.

## Authorization

All endpoints use the `X-Cilly-Role` header already enforced by the main API surface.

- `operator`: create, update, and delete alert configurations
- `read_only`: list and read alert configurations, list alerts, read alert history

## Endpoints

### `POST /alerts/configurations`

Creates a new alert configuration.

Request body:

```json
{
  "alert_id": "drawdown-warning",
  "name": "Drawdown Warning",
  "description": "Warn when drawdown breaches threshold.",
  "source": "risk",
  "metric": "drawdown_pct",
  "operator": "gte",
  "threshold": 5.0,
  "severity": "warning",
  "enabled": true,
  "tags": ["risk", "drawdown"]
}
```

Validation rules:

- `alert_id`, `name`, `source`, and `metric` must be non-empty strings
- `operator` must be one of `gt`, `gte`, `lt`, `lte`, `eq`
- `severity` must be one of `info`, `warning`, `critical`
- `threshold` must be a finite numeric value
- `tags` must not contain blanks or duplicates
- unknown fields are rejected

Returns `201 Created` with the stored configuration.

### `GET /alerts/configurations`

Returns all alert configurations in deterministic `alert_id` order.

Response shape:

```json
{
  "items": [
    {
      "alert_id": "drawdown-warning",
      "name": "Drawdown Warning",
      "description": "Warn when drawdown breaches threshold.",
      "source": "risk",
      "metric": "drawdown_pct",
      "operator": "gte",
      "threshold": 5.0,
      "severity": "warning",
      "enabled": true,
      "tags": ["risk", "drawdown"]
    }
  ],
  "total": 1
}
```

### `GET /alerts/configurations/{alert_id}`

Returns one alert configuration.

Missing IDs return `404 alert_configuration_not_found`.

### `PUT /alerts/configurations/{alert_id}`

Replaces an existing alert configuration using the same validation schema as create, except the `alert_id` is taken from the path.

Request body:

```json
{
  "name": "Drawdown Critical",
  "description": "Escalate when drawdown is severe.",
  "source": "risk",
  "metric": "drawdown_pct",
  "operator": "gte",
  "threshold": 8.5,
  "severity": "critical",
  "enabled": false,
  "tags": ["risk", "critical"]
}
```

### `DELETE /alerts/configurations/{alert_id}`

Deletes an existing alert configuration and returns:

```json
{
  "alert_id": "drawdown-warning",
  "deleted": true
}
```

### `GET /alerts`

Returns a compact alert listing view for inspection.

Response shape:

```json
{
  "items": [
    {
      "alert_id": "drawdown-warning",
      "name": "Drawdown Warning",
      "severity": "warning",
      "enabled": true,
      "source": "risk",
      "metric": "drawdown_pct",
      "operator": "gte",
      "threshold": 5.0
    }
  ],
  "total": 1
}
```

### `GET /alerts/history`

Returns recent alert events for dashboard inspection in deterministic `triggered_at` descending order. If multiple events share the same `triggered_at`, ties are broken by `event_id` descending and then `alert_id` descending.

Response shape:

```json
{
  "items": [
    {
      "event_id": "evt-runtime-critical",
      "alert_id": "runtime-critical",
      "name": "Runtime Halted",
      "severity": "critical",
      "source": "runtime",
      "triggered_at": "2026-03-16T09:00:00Z",
      "summary": "Runtime entered a blocked state.",
      "symbol": null,
      "strategy": null
    },
    {
      "event_id": "evt-drawdown-warning",
      "alert_id": "drawdown-warning",
      "name": "Drawdown Warning",
      "severity": "warning",
      "source": "risk",
      "triggered_at": "2026-03-16T08:00:00Z",
      "summary": "Drawdown crossed the warning threshold.",
      "symbol": "AAPL",
      "strategy": "RSI2"
    }
  ],
  "total": 2
}
```

Notes:

- The endpoint is strictly read-only.
- The UI must consume this endpoint directly and must not invent alert events client-side.
- Empty history returns `{ "items": [], "total": 0 }`.

## Test Verification

Test command:

```powershell
python -m pytest tests/api/test_alerts_api.py tests/ui/test_alert_panel.py tests/test_ui_runtime_browser_flow.py
```

Test output:

```text
Captured after implementation.
```
