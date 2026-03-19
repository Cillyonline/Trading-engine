# API Boundary Cleanup Refactor Plan

Issue: `#694`  
Date: `2026-03-19`  
Scope: planning only. This document defines the target API boundary cleanup and the future implementation sequence. It does not authorize runtime changes in this issue.

## Purpose

The current API layer mixes HTTP transport concerns with orchestration, persistence-adjacent logic, filesystem reads, runtime lifecycle hooks, and API-specific DTO ownership. This plan defines a controlled cleanup path that preserves runtime behavior while making the future refactor implementable in small, reviewable issues.

This plan is intentionally specific enough to create later implementation issues. It is not a generic target-state note.

## Planning constraints

- No runtime behavior changes are introduced by this issue.
- `src/api/*` is not modified by this issue.
- Tests are not updated by this issue beyond planning.
- The future cleanup must preserve existing routes, payload shapes, status codes, auth behavior, startup/shutdown behavior, and `/ui` mounting behavior unless a later issue explicitly states otherwise.
- The future cleanup sequence must not require splitting `src/api/main.py` as the first step. `main.py` remains the composition root during the cleanup unless a later, separately approved issue says otherwise.

## Current API responsibility inventory

Manual validation against `src/api/main.py`, `src/api/alerts_api.py`, `src/api/order_events_sqlite.py`, and existing API docs shows that the current API surface owns all of the responsibilities below.

### Transport and application assembly

- FastAPI app creation
- router registration
- `/ui` static mounting
- startup and shutdown hooks
- role header parsing and dependency wiring

### Request and response contracts

- strategy analysis request and response models
- manual analysis request and response models
- screener request and response models
- watchlist CRUD and execution models
- runtime, health, compliance, and portfolio response models
- journal and strategy metadata response models
- query parameter models for signals, order events, and screener result reads
- alert configuration and history models in `src/api/alerts_api.py`

### Endpoint groups currently implemented

- health and runtime state:
  - `GET /health`
  - `GET /health/engine`
  - `GET /health/data`
  - `GET /health/guards`
  - `GET /runtime/introspection`
  - `GET /system/state`
  - `POST /runtime/start`
  - `POST /runtime/pause`
  - `POST /runtime/resume`
  - `POST /runtime/shutdown`
- compliance and portfolio inspection:
  - `GET /compliance/guards/status`
  - `GET /portfolio/positions`
- analysis and screening:
  - `POST /strategy/analyze`
  - `POST /analysis/run`
  - `POST /screener/basic`
  - `GET /screener/v2/results`
  - `GET /signals`
  - `GET /strategies`
  - `GET /ingestion/runs`
- watchlists:
  - `POST /watchlists`
  - `GET /watchlists`
  - `GET /watchlists/{watchlist_id}`
  - `PUT /watchlists/{watchlist_id}`
  - `DELETE /watchlists/{watchlist_id}`
  - `POST /watchlists/{watchlist_id}/execute`
- journal access:
  - `GET /journal/artifacts`
  - `GET /journal/artifacts/{run_id}/{artifact_name}`
  - `GET /journal/decision-trace`
- alerts:
  - `POST /alerts/configurations`
  - `GET /alerts/configurations`
  - `GET /alerts/configurations/{alert_id}`
  - `PUT /alerts/configurations/{alert_id}`
  - `DELETE /alerts/configurations/{alert_id}`
  - `GET /alerts`
  - `GET /alerts/history`
- execution event reads:
  - `GET /execution/orders`

### Orchestration and domain-adjacent logic currently inside the API layer

- ingestion run existence checks
- snapshot readiness checks
- engine runtime state checks
- deterministic analysis run ID computation for manual and watchlist-triggered runs
- engine config construction
- strategy instantiation and default config merging
- watchlist execution orchestration
- operator-triggered analysis orchestration
- screener ranking and watchlist ranking
- compliance guard status composition from guard functions and environment-backed portfolio state
- journal artifact path resolution and JSON/text parsing
- strategy metadata shaping

### Persistence and storage-adjacent logic currently inside the API layer

- direct repository construction and repository calls from route handlers
- SQLite order event repository implementation in `src/api/order_events_sqlite.py`
- in-memory alert configuration and alert history stores on `app.state`
- analysis run and signal read coordination from route handlers

## Cleanup target

The cleanup target is a transport-first API package where routers own HTTP wiring only, services own request-to-domain orchestration, DTO modules own API-facing schemas, and persistence implementations do not live under `src/api`.

This target is intentionally limited to API boundary cleanup. It does not propose architecture changes outside the API-facing boundary and does not change any endpoint behavior.

## Target separation

### 1. Routers

Target responsibility:

- route path and method declarations
- FastAPI dependency injection
- request DTO binding
- response model declaration
- HTTP error translation only where transport-specific

Target router groups:

- `src/api/routers/health.py`
- `src/api/routers/runtime.py`
- `src/api/routers/compliance.py`
- `src/api/routers/portfolio.py`
- `src/api/routers/analysis.py`
- `src/api/routers/screener.py`
- `src/api/routers/watchlists.py`
- `src/api/routers/journal.py`
- `src/api/routers/strategies.py`
- `src/api/routers/signals.py`
- `src/api/routers/alerts.py`
- `src/api/routers/execution_orders.py`

Planning note:

- `src/api/main.py` should continue to create the `FastAPI` app and include routers during the cleanup sequence.
- Static mounting and startup/shutdown registration remain in `main.py` until the router and service extraction is complete.

### 2. Services

Target responsibility:

- request-to-domain orchestration
- coordination across repositories, engine calls, and runtime helpers
- non-HTTP validation that is shared across routes
- response payload assembly before router-level DTO conversion where needed

Target service groups:

- `src/api/services/runtime_status_service.py`
  - runtime introspection
  - system state reads
  - runtime start, pause, resume, and shutdown orchestration
- `src/api/services/compliance_service.py`
  - guard status evaluation
  - compliance blocking summary
  - environment-backed portfolio/compliance state loading
- `src/api/services/analysis_service.py`
  - manual analysis run orchestration
  - strategy analysis orchestration
  - strategy config merging
  - deterministic run ID coordination for analysis
- `src/api/services/screener_service.py`
  - basic screener orchestration
  - screener result reads
  - ranking logic currently implemented in helper functions
- `src/api/services/watchlist_service.py`
  - watchlist CRUD orchestration
  - watchlist execution orchestration
  - run reuse and persistence coordination for watchlist-triggered analysis
- `src/api/services/journal_service.py`
  - journal artifact listing
  - artifact path validation
  - content parsing
  - decision trace extraction
- `src/api/services/strategy_service.py`
  - strategy metadata reads
  - strategy display-name shaping
- `src/api/services/signal_query_service.py`
  - signal reads
  - ingestion run listing
- `src/api/services/execution_order_service.py`
  - execution order event reads
- `src/api/services/alert_service.py`
  - alert configuration CRUD
  - alert summary listing
  - alert history reads

Planning note:

- Service extraction is an API-boundary cleanup step, not a new application-service architecture for the whole repository.
- Services may continue to call the same underlying engine and repository modules initially. The cleanup goal is to move that coordination out of router modules.

### 3. DTO and query-model modules

Target responsibility:

- API request payload models
- API response payload models
- query parameter models and shared API-specific enums or literals

Target DTO groups:

- `src/api/models/analysis.py`
- `src/api/models/runtime.py`
- `src/api/models/compliance.py`
- `src/api/models/portfolio.py`
- `src/api/models/watchlists.py`
- `src/api/models/screener.py`
- `src/api/models/journal.py`
- `src/api/models/strategies.py`
- `src/api/models/signals.py`
- `src/api/models/alerts.py`
- `src/api/models/execution_orders.py`

Planning note:

- The cleanup should move API-only DTOs out of `src/api/main.py`.
- Shared DTOs currently imported from `cilly_trading.models` should be reviewed during the relevant API issue and either remain shared intentionally or be moved to API-owned DTO modules if they are transport-only. That review belongs to later implementation issues, not this planning issue.

### 4. Dependencies and guards

Target responsibility:

- reusable FastAPI dependencies
- role enforcement helpers
- common request parsing helpers

Target dependency modules:

- `src/api/dependencies/auth.py`
- `src/api/dependencies/query.py`
- `src/api/dependencies/runtime.py`

Planning note:

- `_require_role`, signals query parsing, execution order query parsing, and screener result query parsing are the first obvious extraction candidates.

### 5. Persistence placement target

Target responsibility outside `src/api`:

- concrete SQLite repositories
- schema creation and direct SQL access
- storage-specific serialization helpers

Immediate target:

- move `src/api/order_events_sqlite.py` to the repository/persistence layer in a later issue without changing its behavior

Planning note:

- This plan does not define the final repository package name outside the current repository layer, but it does define that concrete persistence must not remain under `src/api`.

## Module-to-target mapping

The table below identifies the current API-owned responsibilities that should later be split.

| Current location | Current responsibility | Later target |
| --- | --- | --- |
| `src/api/main.py` app setup | app creation, router inclusion, static mount, startup/shutdown | keep in `main.py` as composition root during cleanup |
| `src/api/main.py` request/response classes | API DTO ownership | `src/api/models/*` |
| `src/api/main.py` `_require_role` and query helpers | reusable dependencies | `src/api/dependencies/*` |
| `src/api/main.py` health and runtime handlers | transport + runtime orchestration | `src/api/routers/health.py`, `src/api/routers/runtime.py`, `src/api/services/runtime_status_service.py` |
| `src/api/main.py` compliance helpers and handlers | transport + compliance aggregation | `src/api/routers/compliance.py`, `src/api/services/compliance_service.py` |
| `src/api/main.py` portfolio handler | transport + portfolio inspection shaping | `src/api/routers/portfolio.py`, `src/api/services/compliance_service.py` or `portfolio` service module |
| `src/api/main.py` analysis handlers | transport + strategy execution orchestration | `src/api/routers/analysis.py`, `src/api/services/analysis_service.py` |
| `src/api/main.py` screener handlers and ranking helpers | transport + screening orchestration | `src/api/routers/screener.py`, `src/api/services/screener_service.py` |
| `src/api/main.py` watchlist handlers | CRUD transport + execution orchestration | `src/api/routers/watchlists.py`, `src/api/services/watchlist_service.py` |
| `src/api/main.py` journal helpers and handlers | filesystem reads and parsing | `src/api/routers/journal.py`, `src/api/services/journal_service.py` |
| `src/api/main.py` strategy metadata handler | response shaping | `src/api/routers/strategies.py`, `src/api/services/strategy_service.py` |
| `src/api/main.py` signals and ingestion read handlers | query parsing + repository coordination | `src/api/routers/signals.py`, `src/api/services/signal_query_service.py` |
| `src/api/main.py` execution orders read handler | query parsing + repository coordination | `src/api/routers/execution_orders.py`, `src/api/services/execution_order_service.py` |
| `src/api/alerts_api.py` | alert DTOs, router, and in-memory store coordination | `src/api/models/alerts.py`, `src/api/routers/alerts.py`, `src/api/services/alert_service.py` |
| `src/api/order_events_sqlite.py` | concrete SQLite persistence | repository/persistence package outside `src/api` |

## Migration path

The migration path must keep every route stable while responsibilities move behind the existing API surface.

### Stage 0: documentation and inventory

Definition:

- capture current API responsibilities
- define target split and sequencing

Status:

- completed by this issue

### Stage 1: extract API DTO modules without changing route behavior

Definition:

- move request, response, and query models from `src/api/main.py` and `src/api/alerts_api.py` into `src/api/models/*`
- keep imports wired back into the existing modules
- do not change route declarations, endpoint paths, or payload schemas

Rationale:

- DTO extraction is the lowest-risk cleanup because it isolates schema ownership first
- later router and service issues become smaller once models are no longer embedded in route modules

### Stage 2: extract reusable dependencies and query binders

Definition:

- move role enforcement and query parsing helpers into `src/api/dependencies/*`
- keep route behavior and auth rules unchanged

Rationale:

- dependency extraction reduces repeated imports and makes later router modules small and uniform

### Stage 3: extract read-only services first

Definition:

- move health, runtime introspection reads, compliance status assembly, strategy metadata reads, signal reads, ingestion run listing, journal reads, and execution order reads behind service modules

Rationale:

- read-only flows have less mutation risk than operator-triggered workflows
- this stage proves the service boundary without changing write paths first

### Stage 4: extract router modules for read-only endpoints

Definition:

- move read-only route declarations into router modules
- keep `main.py` as the composition root that includes those routers

Rationale:

- once DTOs and services exist, router extraction is mostly a transport move
- this stage reduces `main.py` size without forcing a full bootstrap rewrite

### Stage 5: extract operator-triggered workflow services

Definition:

- move manual analysis, strategy analysis, screener execution, watchlist execution, and alert mutation orchestration into service modules

Rationale:

- these paths currently mix transport with orchestration and have the highest boundary-cleanup value
- sequencing them after read-only extraction lowers review risk

### Stage 6: extract router modules for operator-triggered endpoints

Definition:

- move mutation and execution route declarations to router modules
- keep response contracts and status codes unchanged

### Stage 7: relocate API-owned persistence implementations

Definition:

- move `src/api/order_events_sqlite.py` out of `src/api`
- keep the same repository interface and query semantics during the move

Rationale:

- persistence relocation should happen after the API no longer directly owns most orchestration logic
- this avoids mixing boundary cleanup concerns in the same issue

### Stage 8: reduce `main.py` to composition-root responsibilities only

Definition:

- leave `main.py` responsible for app creation, router inclusion, app-state initialization, static mounting, and startup/shutdown registration
- no route handlers, API DTO classes, or orchestration helpers should remain in `main.py` except temporary compatibility imports that can later be removed

Rationale:

- this is the end state for the cleanup sequence
- it satisfies the issue goal without requiring a separate application bootstrap architecture change

## Future implementation issue sequence

The later implementation work should be split into small issues with tight file scope. The sequence below is the recommended order.

1. Extract API DTO models from `src/api/main.py` into `src/api/models/*`.
2. Extract alert DTO models from `src/api/alerts_api.py` into `src/api/models/alerts.py`.
3. Extract auth and query dependencies from `src/api/main.py` into `src/api/dependencies/*`.
4. Introduce read-only services for health, runtime, compliance, strategies, signals, ingestion runs, journal reads, and execution order reads.
5. Move read-only route declarations into router modules and include them from `src/api/main.py`.
6. Introduce workflow services for strategy analysis, manual analysis, screener execution, watchlist execution, and alerts.
7. Move operator-triggered and mutation route declarations into router modules and include them from `src/api/main.py`.
8. Relocate `src/api/order_events_sqlite.py` into the repository/persistence layer with no behavior change.
9. Remove obsolete helper code from `src/api/main.py` once imports and call sites are fully migrated.

## Suggested issue boundaries

Each future issue should stay narrow enough to review behavior equivalence.

### Issue group A: DTO extraction

- allowed files:
  - `src/api/main.py`
  - `src/api/alerts_api.py`
  - `src/api/models/*`
- acceptance focus:
  - no endpoint behavior change
  - identical OpenAPI schema for affected routes

### Issue group B: dependency extraction

- allowed files:
  - `src/api/main.py`
  - `src/api/alerts_api.py`
  - `src/api/dependencies/*`
- acceptance focus:
  - identical role enforcement
  - identical validation for query parameters

### Issue group C: read-only service and router extraction

- allowed files:
  - `src/api/main.py`
  - `src/api/routers/*`
  - `src/api/services/*`
  - `src/api/models/*`
- acceptance focus:
  - identical read-only route behavior
  - unchanged status codes and response bodies

### Issue group D: workflow service and router extraction

- allowed files:
  - `src/api/main.py`
  - `src/api/routers/*`
  - `src/api/services/*`
  - `src/api/models/*`
- acceptance focus:
  - identical operator-triggered route behavior
  - unchanged deterministic run reuse behavior
  - unchanged watchlist execution and analysis behavior

### Issue group E: persistence relocation

- allowed files:
  - current API repository module
  - target repository/persistence module
  - API import call sites
- acceptance focus:
  - identical SQL behavior
  - identical read ordering and payload mapping

## Invariants for all later issues

- No route path changes.
- No HTTP method changes.
- No auth header or auth role behavior changes.
- No request or response schema changes unless a later issue explicitly targets that contract.
- No startup or shutdown lifecycle changes.
- No `/ui` mount changes.
- No repository query semantic changes during API boundary cleanup.
- No new business capability added as part of the cleanup.

## Manual validation coverage for this plan

This plan was manually validated against the current API responsibility inventory and covers all current API-owned responsibility buckets:

- transport assembly
- API DTO ownership
- auth and query dependencies
- health, runtime, compliance, and portfolio inspection
- analysis, screener, and watchlist workflows
- journal artifact reads
- strategy and signal read APIs
- alert APIs
- execution order event reads
- API-local persistence implementation

Because each current endpoint family is mapped to a target router and service ownership area, the plan is specific enough to create later implementation issues without requiring generic reinterpretation.

## Non-goals of this plan

- redesigning the engine layer
- redesigning repository abstractions outside what is necessary to move API-owned persistence out of `src/api`
- changing public API behavior
- changing test strategy beyond later behavior-preservation checks
- splitting `src/api/main.py` as part of this planning issue

## Exit condition for issue `#694`

This planning issue is complete when reviewers can use this document to open targeted follow-up issues for:

- DTO extraction
- dependency extraction
- read-only service extraction
- read-only router extraction
- workflow service extraction
- workflow router extraction
- API-owned persistence relocation

No further design interpretation should be required to start those issues.
