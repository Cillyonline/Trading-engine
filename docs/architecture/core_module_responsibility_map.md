# Core Module Responsibility Map

Issue: `#693`  
Status: documentation only  
Scope: define stable responsibilities for current core module categories without splitting files, renaming modules, or changing code.

## Purpose

This document defines the responsibility map for the current core modules and
module categories so future issues can assign work without re-opening ownership
questions.

It answers four questions for each major area:

- what the area is responsible for
- what the area is allowed to do
- what the area must not do
- whether current modules in that area are overloaded and need later splitting

This is a boundary document only. It does not authorize code movement, code
changes, module renames, or architecture changes in this issue.

## Covered Module Categories

The responsibility map covers the major areas required by the issue:

- API entrypoints
- services / orchestration
- engine core
- repositories
- models
- strategy layer

## Responsibility Map

### 1. API entrypoints

Primary current locations:

- `src/api/`
- especially `src/api/main.py`

Stable purpose:

- expose transport-specific entrypoints for HTTP callers
- validate request payloads and query parameters
- enforce API-local authorization and role checks
- translate application results and errors into HTTP responses

Allowed responsibilities:

- route declaration and FastAPI application wiring
- request parsing and response shaping
- API-local DTOs and transport-only schemas
- startup and shutdown hooks required for the HTTP process itself
- calling service / orchestration entrypoints
- translating domain and service failures into transport status codes

Must not do:

- compose multi-step business workflows
- instantiate or query repositories directly
- execute engine algorithms directly
- own deterministic run construction, ranking policy, or strategy selection policy
- own filesystem or SQLite access except strictly transport-local wiring that is
  later expected to move out

Current mapping notes:

- `src/api/main.py` currently mixes transport concerns with orchestration,
  runtime control, compliance state assembly, repository access, and engine
  execution calls
- `src/api/order_events_sqlite.py` is persistence code physically located in
  the API package and therefore does not match the target responsibility

Later splitting required:

- `src/api/main.py` needs later splitting because it currently combines
  transport boundary, workflow coordination, runtime lifecycle handling,
  compliance composition, and read-side persistence access
- `src/api/order_events_sqlite.py` needs later relocation or extraction because
  repository logic should not remain API-owned

### 2. Services / orchestration

Primary current locations:

- `src/cilly_trading/orchestrator/`
- workflow-oriented modules currently spread across `src/api/` and
  `src/cilly_trading/engine/pipeline/`

Stable purpose:

- coordinate application use cases across engine logic, repositories, and
  policy gates
- own the sequencing of steps required to complete one user or operator action

Allowed responsibilities:

- assemble one use case from multiple collaborators
- coordinate repository reads and writes around engine execution
- enforce application-level execution order
- apply use-case rules that are broader than any one engine algorithm
- choose which engine services, repositories, and strategies participate in one
  workflow

Must not do:

- expose HTTP routes or transport DTOs
- contain raw SQL, schema creation, or storage-adapter code
- embed low-level trading calculations or signal-generation algorithms
- become a second model layer that duplicates shared contracts

Current mapping notes:

- `src/cilly_trading/orchestrator/runtime.py` is currently a narrow and clear
  orchestration example because it evaluates compliance gates before dispatch
- orchestration ownership is still fragmented across `src/api/main.py`,
  `src/cilly_trading/engine/analysis/operator_trigger.py`, and
  `src/cilly_trading/engine/pipeline/orchestrator.py`

Later splitting required:

- orchestration responsibilities need later consolidation from API and engine
  namespaces into a clearer service-owned boundary
- `src/cilly_trading/engine/pipeline/orchestrator.py` should later be reviewed
  for whether it is a pure engine pipeline or a cross-layer use-case
  coordinator

### 3. Engine core

Primary current locations:

- `src/cilly_trading/engine/`
- especially `src/cilly_trading/engine/core.py`
- related domain packages under `src/cilly_trading/engine/*`

Stable purpose:

- own deterministic trading, analysis, runtime, risk, portfolio, telemetry, and
  evaluation logic that is part of the product core

Allowed responsibilities:

- signal generation and analysis execution
- deterministic identity generation tied to engine semantics
- engine-side validation and invariant enforcement
- domain calculations for risk, portfolio, metrics, and lifecycle evaluation
- pure engine pipelines that do not require transport or storage ownership
- engine contracts that are specific to core execution behavior

Must not do:

- import HTTP or route-level code
- instantiate concrete repository implementations inside core execution paths
- own SQL, filesystem persistence, or storage schema management
- shape API response DTOs
- coordinate full application workflows that span transport, repository, and
  operator policy concerns

Current mapping notes:

- `src/cilly_trading/engine/core.py` owns the canonical watchlist-analysis path
  and deterministic run identity logic
- the same module currently also reaches into persistence by importing
  `SqliteLineageRepository`, which makes current ownership broader than the
  stable responsibility defined here
- `src/cilly_trading/engine/data.py` currently mixes engine data access,
  provider integration, validation, ingestion, and persistence-oriented work

Later splitting required:

- `src/cilly_trading/engine/core.py` needs later splitting because engine
  execution, persistence coordination, lineage handling, and artifact output are
  all combined
- `src/cilly_trading/engine/data.py` needs later splitting because provider
  loading, normalization, ingestion, and persistence are combined in one module

### 4. Repositories

Primary current locations:

- `src/cilly_trading/repositories/`
- `src/cilly_trading/db/`
- persistence adapters currently placed elsewhere

Stable purpose:

- isolate persistence concerns and storage access behind repository contracts

Allowed responsibilities:

- database reads and writes
- storage-specific translation between persisted rows and shared model shapes
- schema initialization helpers needed by repository implementations
- file-backed or SQLite-backed persistence adapters
- repository-specific query methods for use cases already defined elsewhere

Must not do:

- expose HTTP behavior
- import engine internals as persistence contracts
- choose business workflow order
- generate signals, enforce trading policy, or own strategy logic
- define transport DTOs

Current mapping notes:

- `src/cilly_trading/repositories/analysis_runs_sqlite.py` is repository-owned
  by purpose, but currently imports `AnalysisRun` from the engine layer
- this upward dependency is a current-state violation and not part of the
  stable responsibility map
- `src/api/order_events_sqlite.py` is functionally a repository and should be
  treated as persistence-owned for future issue creation even though its current
  location is under `src/api/`

Later splitting required:

- repository contracts should later be separated from engine-owned entities
  where repository modules currently depend upward on engine types
- API-local repository code needs later extraction into repository-owned
  modules

### 5. Models

Primary current locations:

- `src/cilly_trading/models.py`
- `src/cilly_trading/contracts/`
- contract-only modules under related packages
- selected shared contract modules currently outside the main package, such as
  `src/risk/contracts.py`

Stable purpose:

- define shared domain entities, value objects, identifiers, and contracts that
  can be exchanged across higher layers without owning transport, storage, or
  orchestration behavior

Allowed responsibilities:

- shared domain entity definitions
- repository-facing and engine-facing contracts
- stable enums, literals, identifiers, and validation shapes
- persistence-independent records
- canonical serialization helpers when they are truly model-level utilities

Must not do:

- define HTTP route handlers or API transport concerns
- import repositories, engine execution modules, or orchestration modules
- own SQL or storage technology details
- embed use-case sequencing behavior
- combine domain models with transport DTO ownership in the same stable module

Current mapping notes:

- `src/cilly_trading/models.py` currently mixes shared domain structures like
  `Signal` and `Trade` with API DTOs such as `SignalReadItemDTO` and
  `SignalReadResponseDTO`
- risk and portfolio contracts are also spread across multiple package roots,
  which weakens the notion of one stable contract owner

Later splitting required:

- `src/cilly_trading/models.py` needs later splitting because domain models and
  API-facing DTOs coexist
- duplicated or competing contract owners in `src/risk/` and
  `src/cilly_trading/risk_framework/` need later clarification

### 6. Strategy layer

Primary current locations:

- `src/cilly_trading/strategies/`
- strategy lifecycle helpers under `src/cilly_trading/engine/strategy_lifecycle/`

Stable purpose:

- define strategy implementations, registration, configuration validation, and
  lifecycle semantics for generating trading signals

Allowed responsibilities:

- strategy implementations and deterministic signal logic
- strategy registration and lookup
- strategy-specific config schema and validation
- strategy lifecycle state transitions that are part of engine semantics
- preset definitions and reference strategies

Must not do:

- expose HTTP or transport logic
- access repositories or storage directly
- coordinate end-to-end application workflows
- own persistence schema or runtime control-plane behavior
- become a generic dumping ground for unrelated analytics utilities

Current mapping notes:

- `src/cilly_trading/strategies/registry.py` is a clear strategy-layer owner
  because it centralizes deterministic registration and resolution
- strategy execution still depends on the engine core for orchestration and
  execution flow, which is appropriate as long as the strategy layer remains
  focused on strategy definitions and validation rather than use-case assembly

Later splitting required:

- no immediate strategy-module split is mandated by this issue, but future
  issues should keep strategy definition, lifecycle, and orchestration
  ownership separate if additional workflow concerns accumulate here

## Allowed Responsibility Matrix

| Module category | Allowed to own | Must not own |
| --- | --- | --- |
| API entrypoints | HTTP transport, auth checks, request parsing, response shaping, service calls | repository access, engine execution, multi-step workflow composition |
| services / orchestration | use-case sequencing, engine/repository coordination, application-level flow | HTTP routing, raw SQL, low-level strategy or engine algorithms |
| engine core | deterministic domain execution, analysis, risk, portfolio, runtime semantics | transport handling, concrete persistence, API DTO shaping |
| repositories | storage access, row-to-model translation, schema helpers | engine policy, HTTP behavior, use-case orchestration |
| models | shared contracts, entities, value objects, stable shapes | HTTP DTO ownership, SQL, orchestration behavior, upward imports |
| strategy layer | strategy definitions, registration, config validation, lifecycle semantics | transport, repository access, end-to-end workflow coordination |

## Overloaded Modules Requiring Later Refactor Issues

The following modules should be treated as overloaded when future issues are
created. This issue only records them; it does not split them.

| Module | Overload reason | Future split direction |
| --- | --- | --- |
| `src/api/main.py` | route handling, DTO ownership, runtime lifecycle, compliance assembly, workflow composition, repository access | separate transport-only endpoints from orchestration and persistence-backed read/write helpers |
| `src/api/order_events_sqlite.py` | persistence implementation inside API package | move responsibility under repository ownership |
| `src/cilly_trading/engine/core.py` | engine execution, deterministic IDs, lineage coordination, persistence coupling, artifact output | keep pure engine execution separate from persistence and output coordination |
| `src/cilly_trading/engine/data.py` | provider access, validation, normalization, ingestion, persistence | separate engine-facing data contracts from ingestion and persistence adapters |
| `src/cilly_trading/models.py` | shared domain entities and API DTOs combined | separate domain contracts from transport DTO definitions |

## Rules For Future Issue Creation

When creating future issues that touch core modules:

- if the work changes HTTP routes or API payload handling, scope it to API
  entrypoints only
- if the work coordinates multiple repositories and engine calls, scope it to
  services / orchestration
- if the work changes trading logic, risk logic, runtime invariants, or signal
  generation, scope it to engine core or strategy layer
- if the work changes database access or persisted record translation, scope it
  to repositories
- if the work changes shared entities or contracts used across layers, scope it
  to models
- if one proposed issue needs one module to own both transport and persistence,
  or both engine policy and repository code, the issue should be split before
  implementation

## Manual Validation For Issue #693

Manual validation for this responsibility map was performed against current
module usage by reviewing:

- `docs/architecture/target_architecture_layers.md`
- `docs/architecture/current_architecture_boundary_audit.md`
- `src/api/main.py`
- `src/cilly_trading/orchestrator/runtime.py`
- `src/cilly_trading/engine/core.py`
- `src/cilly_trading/repositories/analysis_runs_sqlite.py`
- `src/cilly_trading/models.py`
- `src/cilly_trading/strategies/registry.py`

Validation checks:

- each required major module/category has one documented stable purpose
- each category has explicit allowed responsibilities
- each category has explicit forbidden responsibilities
- overloaded modules needing later refactor are identified explicitly
- the responsibility map is documented in one location under
  `docs/architecture/`
- the document remains within issue scope by avoiding code changes, refactors,
  renames, or file moves
