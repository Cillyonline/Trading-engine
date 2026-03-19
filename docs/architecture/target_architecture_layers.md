# Target Architecture Layers

Issue: `#692`  
Status: target-state architecture definition only  
Scope: documentation only. This document does not move files, refactor modules, change imports, or change runtime behavior.

## Purpose

This document defines the canonical target architecture for the system and the
intended boundaries between:

- API
- services / orchestration
- engine logic
- repositories / persistence
- models

It is the target-state contract that later controlled refactors must converge
toward. It is not a migration plan and it does not require immediate code
movement.

## Canonical Layers

### 1. Models

Purpose:

- define shared domain entities, value objects, repository contracts, engine
  contracts, and transport-independent schemas
- provide the stable shapes exchanged between higher layers

This layer owns:

- core domain entities and value objects
- request / response contracts between internal layers
- repository interfaces and persistence-independent records
- enums, identifiers, and validation rules that are not transport-specific

This layer does not own:

- HTTP routing concerns
- workflow composition
- persistence implementation details
- provider-specific I/O code

### 2. Repositories / Persistence

Purpose:

- isolate data access and persistence concerns behind repository contracts

This layer owns:

- database access
- file-backed persistence
- schema creation or migration helpers when needed by repository modules
- external storage adapters
- repository implementations that translate storage records to and from models

This layer does not own:

- HTTP request handling
- orchestration decisions
- engine policy or signal-generation logic

### 3. Engine Logic

Purpose:

- own deterministic trading, analysis, evaluation, risk, strategy, portfolio,
  and runtime domain logic

This layer owns:

- signal-generation logic
- strategy execution
- domain calculations
- engine-side risk evaluation
- domain validation tied to engine semantics
- pure engine workflows that do not depend on transport concerns

This layer does not own:

- HTTP transport handling
- endpoint authorization
- storage technology decisions
- multi-step application workflow composition that coordinates transport,
  repositories, and engine together

### 4. Services / Orchestration

Purpose:

- coordinate application use cases across repositories and engine logic

This layer owns:

- use-case orchestration
- transaction boundaries where applicable
- request-to-engine workflow composition
- coordination of repository reads and writes around engine execution
- application-level policies that are broader than a single engine algorithm

This layer does not own:

- HTTP routing or serialization details
- direct SQL or storage implementation
- low-level engine algorithm implementation

### 5. API

Purpose:

- expose transport-specific entrypoints and convert transport payloads into
  service calls

This layer owns:

- HTTP routes and handlers
- request parsing and response shaping
- authentication and authorization checks
- transport-level status codes and error translation
- API-specific DTOs only when they are strictly transport-facing

This layer does not own:

- business workflow composition
- engine execution logic
- repository implementation logic
- persistence schema management

## Canonical Dependency Direction

The canonical dependency direction is:

`API -> services / orchestration -> engine`

`services / orchestration -> repositories`

`engine -> models`

`repositories -> models`

`API -> models` only for transport adapters and DTO translation

`services / orchestration -> models` for use-case inputs and outputs

No other direct dependency direction is part of the target architecture.

## Allowed Dependency Matrix

| From layer | May depend on | Must not depend on |
| --- | --- | --- |
| API | services / orchestration, models | engine, repositories / persistence |
| services / orchestration | engine, repositories / persistence, models | API |
| engine logic | models | API, services / orchestration, repositories / persistence |
| repositories / persistence | models | API, services / orchestration, engine logic |
| models | none | API, services / orchestration, engine logic, repositories / persistence |

## Boundary Rules

The following rules are mandatory for the target architecture.

### Rule 1: API is a transport boundary only

- API modules may parse requests, enforce auth, call services, and map results
  into transport responses.
- API modules must not compose engine workflows directly.
- API modules must not instantiate or query repository implementations directly.

### Rule 2: Services own application use cases

- Cross-cutting workflows belong to services / orchestration.
- A service may call multiple repositories and engine modules in one use case.
- A service is the only layer that may coordinate both engine logic and
  persistence in the same workflow.

### Rule 3: Engine logic is storage-agnostic

- Engine modules must depend on models and engine-owned logic only.
- Engine modules must not import concrete database, filesystem, or HTTP modules.
- When engine logic needs persisted data, that data must be provided through
  service-owned coordination using model contracts.

### Rule 4: Repository code is domain-contract aware, not engine aware

- Repository implementations may depend on models and repository contracts.
- Repository implementations must not import engine modules or engine entities.
- Repository return types must be model-layer contracts rather than
  engine-internal objects.

### Rule 5: Models are the lowest shared contract layer

- Models must remain dependency-free with respect to the other four layers.
- Models may be shared across API, services, engine, and repositories.
- Models must not include transport handlers, storage code, or orchestration
  behavior.

### Rule 6: DTO ownership must be explicit

- Transport DTOs belong to the API layer.
- Domain models and internal contracts belong to the models layer.
- The same class or module must not act as both a transport DTO owner and a
  canonical domain-model owner.

### Rule 7: One module should have one primary layer owner

- Each module should map to exactly one canonical layer.
- If a module combines route handling, orchestration, engine policy, and
  persistence, it violates the target architecture even if behavior is correct.

### Rule 8: Dependency inversion happens at contracts, not through upward imports

- Higher-level layers may define the use case and call lower-level layers.
- Lower-level layers must not regain access to higher-level logic by importing
  upward.
- Repository and engine boundaries are crossed through model contracts rather
  than concrete upward imports.

## Target Folder / Module Structure

The target structure below is the canonical ownership model for production code
under `src/`. It defines where each layer belongs conceptually. It does not
require immediate file movement.

### API layer target ownership

Canonical target areas:

- `src/api/`

Expected responsibilities under this area:

- route modules
- API startup and shutdown wiring
- auth and role enforcement
- API-local request and response DTOs
- transport error mappers

### Services / orchestration target ownership

Canonical target areas:

- `src/cilly_trading/orchestrator/`
- service-oriented modules currently embedded elsewhere that coordinate
  multi-step workflows

Expected responsibilities under this area:

- analysis execution use cases
- runtime control use cases
- watchlist execution use cases
- application workflow coordination across engine and repositories

### Engine logic target ownership

Canonical target areas:

- `src/cilly_trading/engine/`
- engine-owned domain packages under `src/cilly_trading/` that hold strategy,
  risk, portfolio, compliance, metrics, or journal logic when those modules are
  pure domain logic rather than orchestration or persistence

Expected responsibilities under this area:

- strategies and evaluation
- risk and portfolio calculations
- engine runtime semantics
- data normalization and domain validation that are part of engine policy

### Repositories / persistence target ownership

Canonical target areas:

- `src/cilly_trading/repositories/`
- `src/cilly_trading/db/`
- persistence adapters currently outside those areas that should conceptually be
  repository-owned

Expected responsibilities under this area:

- SQLite repositories
- file-backed stores
- persistence adapters
- database helpers used only by repository code

### Models target ownership

Canonical target areas:

- `src/cilly_trading/models.py` or a future model-focused package under
  `src/cilly_trading/`
- `src/cilly_trading/contracts/`
- other contract-only modules that define shared domain records without taking
  on orchestration, transport, or persistence behavior

Expected responsibilities under this area:

- domain entities
- repository contracts
- engine contracts
- shared validation shapes

## Practical Mapping For Current System Components

The target architecture must remain practical for the existing repository. The
following current component groups are covered by the canonical layers above.

| Current component group | Target layer |
| --- | --- |
| `src/api/*` HTTP routes, auth, transport responses | API |
| `src/cilly_trading/orchestrator/*` runtime and use-case coordination | services / orchestration |
| `src/cilly_trading/engine/*` deterministic analysis, strategy execution, runtime domain logic | engine logic |
| `src/cilly_trading/repositories/*`, `src/cilly_trading/db/*`, API-local SQLite access that should become repository-owned | repositories / persistence |
| `src/cilly_trading/models.py`, `src/cilly_trading/contracts/*`, shared contracts now split across packages | models |

The current top-level `src/data_layer/` and `src/risk/` packages are covered by
this target architecture as follows:

- code in `src/data_layer/` belongs either to repositories / persistence or to
  models, depending on whether it implements storage access or shared
  validation contracts
- code in `src/risk/` belongs either to engine logic or to models, depending on
  whether it implements runtime evaluation logic or shared risk contracts

This mapping is intentionally practical: it classifies current system
components without requiring immediate package moves in this issue.

## Explicit Forbidden Access Patterns

The following direct accesses are forbidden in the target architecture:

- API -> repositories / persistence
- API -> engine logic
- engine logic -> repositories / persistence
- engine logic -> API
- repositories / persistence -> engine logic
- repositories / persistence -> services / orchestration
- repositories / persistence -> API
- models -> any higher layer

These forbidden accesses are unambiguous even when they appear convenient for a
single workflow. Convenience does not override the layer contract.

## Decision Rules For Future Refactor Work

- If a module handles HTTP or another transport protocol, it belongs to API.
- If a module coordinates a use case across multiple collaborators, it belongs
  to services / orchestration.
- If a module performs trading, analysis, risk, portfolio, or strategy domain
  logic, it belongs to engine logic.
- If a module reads or writes databases, files, or storage adapters, it belongs
  to repositories / persistence.
- If a module defines shared entities or contracts with no transport or storage
  behavior, it belongs to models.

If a module appears to fit multiple categories, its responsibilities are not yet
properly separated and later refactor work should split those responsibilities
without changing the target layer definitions in this document.

## Manual Validation For Issue #692

Manual validation for this issue should confirm all of the following:

- the five canonical layers are named exactly as required by the issue
- allowed dependencies are documented explicitly
- forbidden dependency directions are documented explicitly
- boundary rules are stated in imperative form and are not ambiguous
- the target folder / module structure is documented under `docs/architecture/`
- the target architecture clearly classifies current system component groups,
  including API, orchestration, engine, repositories, models, `data_layer`, and
  `risk`
- the document does not propose runtime code changes, file moves, or refactors

## Relationship To Current-State Audit

This document defines the target architecture.

`docs/architecture/current_architecture_boundary_audit.md` documents the current
state and existing violations against this target direction.
