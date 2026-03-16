# Alerts API

The alert API exposes deterministic, in-memory alert configuration endpoints for operators and read-only retrieval endpoints for inspection.

## Authorization

All endpoints use the `X-Cilly-Role` header already enforced by the main API surface.

- `operator`: create, update, and delete alert configurations
- `read_only`: list and read alert configurations, list alerts

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

## Test Verification

Test command:

```powershell
python -m pytest tests/api/test_alerts_api.py
```

Test output:

```text
============================= test session starts =============================
platform win32 -- Python 3.13.2, pytest-8.4.1, pluggy-1.6.0
rootdir: C:\dev\Trading-engine
configfile: pytest.ini
plugins: anyio-4.9.0
collected 3 items

tests\api\test_alerts_api.py ...                                         [100%]

============================== warnings summary ===============================
src\api\main.py:683
  C:\dev\Trading-engine\src\api\main.py:683: DeprecationWarning:
          on_event is deprecated, use lifespan event handlers instead.

          Read more about it in the
          [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).

    @app.on_event("startup")

..\..\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py:4495
..\..\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py:4495
  C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py:4495: DeprecationWarning:
          on_event is deprecated, use lifespan event handlers instead.

          Read more about it in the
          [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).

    return self.router.on_event(event_type)

src\api\main.py:690
  C:\dev\Trading-engine\src\api\main.py:690: DeprecationWarning:
          on_event is deprecated, use lifespan event handlers instead.

          Read more about it in the
          [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).

    @app.on_event("shutdown")

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 3 passed, 4 warnings in 3.48s ========================
```
