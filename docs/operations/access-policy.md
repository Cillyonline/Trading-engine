# Access Policy

## Decision

The application is accessed locally only. Within that local-only deployment model, the current operator-facing API in `src/api/main.py` is protected by an explicit three-role contract: `owner`, `operator`, and `read_only`.

## Supported Access Mode

- Local execution on the user's own machine only.

## Explicitly Unsupported Access Modes

- Hosted access is unsupported.
- Cloud access is unsupported.
- Web access is unsupported.
- SaaS access is unsupported.
- Remote access is unsupported.

## Role Meanings

- `owner`: full control-plane authority. May inspect all covered operator endpoints, trigger manual analysis/screener actions, and change engine execution state.
- `operator`: day-to-day control-plane operator. May inspect all covered operator endpoints and trigger manual analysis/screener actions, but may not change engine execution state.
- `read_only`: inspection-only consumer. May call covered read-only endpoints, but may not trigger any mutating operator action.

For the covered endpoints in this document, `owner` is a superset of `operator`, and `operator` is a superset of `read_only`.

## Covered Operator-Facing API Surfaces

This contract is normative for the current operator-facing routes defined in `src/api/main.py`:

- health and runtime inspection
- compliance and portfolio inspection
- analysis, screener, and ingestion inspection
- journal and audit inspection
- execution control

This contract does not cover `/ui` static assets or any future route that is not listed below. Runtime enforcement of this contract belongs in a separate implementation issue.

## Endpoint Permission Contract

Classification rule:

- `read_only`: the endpoint is inspection-only and must not change runtime state or persist new operator-triggered work.
- `mutating`: the endpoint can change execution state or persist/operator-trigger new work, regardless of HTTP verb conventions.

All covered endpoints are protected. Anonymous access is out of contract. The minimum allowed role for each endpoint is:

| Method | Endpoint | Classification | Minimum allowed role |
| --- | --- | --- | --- |
| `GET` | `/health` | `read_only` | `read_only` |
| `GET` | `/health/engine` | `read_only` | `read_only` |
| `GET` | `/health/data` | `read_only` | `read_only` |
| `GET` | `/health/guards` | `read_only` | `read_only` |
| `GET` | `/compliance/guards/status` | `read_only` | `read_only` |
| `GET` | `/runtime/introspection` | `read_only` | `read_only` |
| `GET` | `/system/state` | `read_only` | `read_only` |
| `GET` | `/portfolio/positions` | `read_only` | `read_only` |
| `GET` | `/ingestion/runs` | `read_only` | `read_only` |
| `GET` | `/journal/artifacts` | `read_only` | `read_only` |
| `GET` | `/journal/artifacts/{run_id}/{artifact_name}` | `read_only` | `read_only` |
| `GET` | `/journal/decision-trace` | `read_only` | `read_only` |
| `GET` | `/strategies` | `read_only` | `read_only` |
| `GET` | `/signals` | `read_only` | `read_only` |
| `GET` | `/execution/orders` | `read_only` | `read_only` |
| `GET` | `/screener/v2/results` | `read_only` | `read_only` |
| `POST` | `/strategy/analyze` | `mutating` | `operator` |
| `POST` | `/analysis/run` | `mutating` | `operator` |
| `POST` | `/screener/basic` | `mutating` | `operator` |
| `POST` | `/execution/pause` | `mutating` | `owner` |
| `POST` | `/execution/resume` | `mutating` | `owner` |

Effective role permissions derived from the table:

- `read_only` may call every listed `GET` endpoint and no listed `POST` endpoint.
- `operator` may call every `read_only` endpoint plus `POST /strategy/analyze`, `POST /analysis/run`, and `POST /screener/basic`.
- `owner` may call every covered endpoint, including `POST /execution/pause` and `POST /execution/resume`.

## Deterministic Denial Behavior

Protected endpoint behavior is deterministic for the covered routes once authorization enforcement is applied:

- If the caller is unauthenticated or the presented credentials do not establish a valid principal, the endpoint returns `401 Unauthorized`.
- If the caller is authenticated but does not hold the minimum allowed role for the endpoint, the endpoint returns `403 Forbidden`.
- If the caller holds the required role, the request proceeds to normal endpoint-specific validation and execution.
- A `401` or `403` response must not perform endpoint side effects.

## Rationale

This document makes the current operator control plane reviewable without inference by defining one role vocabulary, one endpoint matrix, and one denial model for the existing routes in `src/api/main.py`.
