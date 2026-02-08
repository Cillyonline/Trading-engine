# Engine Runtime Health (read-only)

## Endpoint

- `GET /health`
- Read-only contract: no runtime initialization, no lifecycle transitions, no persistence writes.

## Response payload

```json
{
  "status": "healthy|degraded|unavailable",
  "mode": "<runtime mode>",
  "reason": "<deterministic rule id>",
  "checked_at": "<ISO-8601 UTC timestamp>"
}
```

The payload is intentionally lightweight and derived from runtime introspection plus deterministic evaluation.

## Deterministic evaluation rules

Inputs:
- runtime snapshot (`mode`, `updated_at`)
- injected `now` timestamp

Thresholds:
- `degraded_after = 30s`
- `unavailable_after = 120s`

Rules (in order):

1. If `mode == running` and `now - updated_at <= 30s`:
   - `status = healthy`
   - `reason = runtime_running_fresh`
2. If `mode == running` and `30s < now - updated_at <= 120s`:
   - `status = degraded`
   - `reason = runtime_running_stale`
3. If `mode == running` and `now - updated_at > 120s`:
   - `status = unavailable`
   - `reason = runtime_running_timeout`
4. If `mode == ready`:
   - `status = degraded`
   - `reason = runtime_not_started`
5. Any other mode:
   - `status = unavailable`
   - `reason = runtime_not_available`

These rules are implemented as a pure function so test cases can control both snapshot and time.
