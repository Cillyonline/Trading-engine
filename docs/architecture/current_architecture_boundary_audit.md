# Current Architecture Boundary Audit

Issue: `#691`  
Audit date: `2026-03-19`  
Scope: current repository boundaries only. No target-state design, refactoring, import changes, or runtime changes are proposed here.

## Audit method

Manual validation was performed against the current repository structure and selected implementation files under `src/` with emphasis on:

- package layout under `src/api`, `src/cilly_trading`, `src/data_layer`, and `src/risk`
- main execution entrypoints
- import direction between API, orchestration/service logic, engine logic, repositories/persistence, and models/contracts
- modules that combine multiple responsibilities

## Current layer map

The current codebase does not enforce one clean boundary model. The closest current layer split is:

| Layer | Current locations | Current ownership notes |
| --- | --- | --- |
| API / control plane | `src/api/*` | HTTP surface, request/response models, auth/role checks, startup/shutdown hooks, runtime health, journal file reads, watchlist execution orchestration, and some SQLite access |
| Service / orchestration | `src/cilly_trading/orchestrator/runtime.py`, `src/cilly_trading/engine/analysis/operator_trigger.py`, `src/cilly_trading/engine/pipeline/orchestrator.py`, parts of `src/api/main.py` | Split across API and engine namespaces; no single orchestration package owns request-to-engine workflows |
| Engine logic | `src/cilly_trading/engine/*` | Analysis execution, runtime lifecycle, data loading, deterministic execution, telemetry, health, lineage, strategy lifecycle, and some control-plane read models |
| Repositories / persistence | `src/cilly_trading/repositories/*`, `src/cilly_trading/db/*`, plus `src/api/order_events_sqlite.py` | Mostly SQLite-backed persistence, but one repository lives in API and some repositories depend upward on engine types |
| Models / contracts | `src/cilly_trading/models.py`, `src/risk/contracts.py`, `src/cilly_trading/risk_framework/*`, `src/cilly_trading/portfolio/*`, `src/cilly_trading/engine/portfolio/*` | Ownership is split between shared models, API DTOs, risk contracts, and duplicated portfolio/risk concepts |

## Main execution paths

### 1. HTTP control path

Current request flow is primarily:

`src/api/main.py` -> request validation / role checks -> direct repository access -> direct engine/compliance/runtime calls -> response DTO shaping

Observed examples:

- `src/api/main.py:28-71` imports engine analysis, compliance guards, engine runtime lifecycle, engine runtime state, repositories, strategies, shared models, and API-local persistence.
- `src/api/main.py:1451-1529` performs watchlist execution orchestration directly in the API layer: watchlist lookup, ingestion validation, strategy creation, deterministic run ID creation, engine config construction, engine execution, ranking, and analysis-run persistence.
- `src/api/main.py:1010-1098` builds compliance state directly from environment variables and guard functions inside the API module.

### 2. CLI / offline execution path

Current CLI path is:

`src/cilly_trading/__main__.py` -> `src/cilly_trading/cli/*` -> engine modules / metrics

Observed examples:

- `src/cilly_trading/__main__.py` dispatches to `backtest` and `evaluate`.
- `src/cilly_trading/cli/backtest_cli.py` calls `BacktestRunner` and strategy registry directly.
- `src/cilly_trading/engine/deterministic_run.py` performs deterministic snapshot ingestion, strategy resolution, repository construction, engine execution, and output writing in one flow.

### 3. Engine analysis path

Current engine analysis path is:

data load -> strategy execution -> lineage assignment -> reason generation -> signal persistence -> lineage persistence

Observed examples:

- `src/cilly_trading/engine/core.py:24-37` imports data, lineage, logging, reasons, strategy param validation, shared models, repository interfaces, and a concrete SQLite lineage repository.
- `src/cilly_trading/engine/core.py:729-740` falls back to constructing `SqliteLineageRepository` inside the engine and then persists both lineage and signals from the engine core.

## Cross-layer violations

### 1. API layer directly owns orchestration and workflow composition

Severity: High

The API layer is not limited to transport concerns. `src/api/main.py` directly composes multi-step workflows, constructs `EngineConfig`, creates strategies, computes deterministic IDs, invokes engine runs, ranks results, and persists analysis-run artifacts.

Evidence:

- `src/api/main.py:42-71`
- `src/api/main.py:1451-1529`

Why this is a boundary violation:

- orchestration logic is mixed into the transport layer
- HTTP concerns and domain workflow concerns cannot be separated cleanly
- workflow reuse from CLI or non-HTTP callers requires importing or re-implementing API-owned logic

### 2. API layer contains repository/persistence code

Severity: High

`src/api/order_events_sqlite.py` is a SQLite repository placed in the API package, including schema creation, writes, and reads.

Evidence:

- `src/api/order_events_sqlite.py:19-65`
- `src/api/main.py:60`

Why this is a boundary violation:

- persistence is not fully owned by repository/persistence packages
- API package currently mixes HTTP surface and storage implementation

### 3. Repository layer depends upward on engine entities

Severity: High

Repository implementations import engine-layer types instead of depending only on repository-owned or shared contract types.

Evidence:

- `src/cilly_trading/repositories/analysis_runs_sqlite.py:14` imports `AnalysisRun` from `cilly_trading.engine.core`
- `src/cilly_trading/repositories/lineage_repository.py:12` imports `LineageContext` from `cilly_trading.engine.lineage`

Why this is a boundary violation:

- persistence implementations depend on engine internals
- engine entity shape changes can break repositories directly
- repository contracts are not independently owned

### 4. Engine core depends on a concrete repository implementation

Severity: High

`run_watchlist_analysis` accepts abstractions for signals but directly instantiates a concrete SQLite lineage repository when none is supplied.

Evidence:

- `src/cilly_trading/engine/core.py:36`
- `src/cilly_trading/engine/core.py:729-731`

Why this is a boundary violation:

- engine core is coupled to SQLite-specific persistence
- dependency inversion is only partial
- engine runtime behavior is no longer purely application-core logic

### 5. Engine modules depend on top-level sibling packages outside `cilly_trading`

Severity: Medium

Engine and ingestion code import `risk.contracts` and `data_layer.ingestion_validation` from separate top-level packages, while other domain code lives under `cilly_trading.*`.

Evidence:

- `src/cilly_trading/engine/pipeline/orchestrator.py:8`
- `src/cilly_trading/engine/risk/gate.py:9`
- `src/cilly_trading/engine/order_execution_model.py:14`
- `src/cilly_trading/ingestion.py:12`
- `src/cilly_trading/engine/data.py:20-24`

Why this is a boundary violation:

- the package root does not reflect a single ownership boundary
- contracts appear both inside and outside the main product namespace
- dependency direction is hard to reason about from package layout alone

### 6. Shared models package mixes domain models and API DTOs

Severity: Medium

`src/cilly_trading/models.py` contains both domain signal/trade structures and API response DTOs such as `SignalReadItemDTO` and `SignalReadResponseDTO`.

Evidence:

- `src/cilly_trading/models.py` contains `Signal`, `Trade`, `EntryZoneDTO`, `SignalReadItemDTO`, and `SignalReadResponseDTO`
- `src/api/main.py:67` imports API response DTOs from the shared models module
- `src/api/chart_contract.py:7` imports `EntryZoneDTO` and `SignalReadResponseDTO`

Why this is a boundary violation:

- model ownership is split between core domain and transport concerns
- API contracts are not isolated from shared domain contracts

## Mixed responsibilities

### `src/api/main.py`

Current responsibilities include:

- FastAPI application bootstrap and static file mounting
- logging configuration
- request and response schema definitions
- role/authorization helpers
- runtime startup and shutdown lifecycle hooks
- health and compliance computation
- engine runtime control endpoints
- watchlist CRUD endpoints
- watchlist execution orchestration
- journal artifact filesystem reads
- strategy metadata reads
- signal and order-event reads

Observed size indicators:

- 1,544 lines
- 142 top-level `class`, `def`, or route declarations

This module is the clearest overloaded boundary in the repository.

### `src/cilly_trading/engine/core.py`

Current responsibilities include:

- canonical JSON and SHA helpers
- strategy config normalization
- run ID and signal ID generation
- strategy execution loop
- snapshot and external data gating
- lineage coordination
- reason generation
- structured logging
- signal persistence
- audit artifact writing

Observed size indicator:

- 701 lines

This module combines engine policy, execution flow, persistence coordination, and artifact output.

### `src/cilly_trading/engine/data.py`

Current responsibilities include:

- local snapshot file loading
- snapshot validation and normalization
- deterministic snapshot ingestion
- SQLite persistence for ingestion and snapshots
- snapshot metadata reads
- external provider loading from Yahoo and Binance
- OHLCV validation and normalization

Observed size indicator:

- 702 lines

This module mixes ingestion, provider access, normalization, and persistence concerns.

## Unclear ownership

### 1. Portfolio state has two competing owners

Evidence:

- `src/cilly_trading/portfolio/state.py` defines equity-based drawdown and daily-loss state
- `src/cilly_trading/engine/portfolio/state.py` defines read-only position inspection state loaded from environment variables
- `src/api/main.py:38` imports the first as compliance state
- `src/api/main.py:61-64` imports the second as runtime inspection state

Current ambiguity:

- both are named `PortfolioState`
- one is compliance/risk oriented and one is control-plane inspection oriented
- ownership is split between `cilly_trading.portfolio` and `cilly_trading.engine.portfolio`

### 2. Risk contracts have two competing owners

Evidence:

- `src/risk/contracts.py` defines `RiskEvaluationRequest`, `RiskDecision`, and `RiskGate`
- `src/cilly_trading/risk_framework/contract.py` also defines `RiskEvaluationRequest` plus a different `RiskEvaluationResponse` and `RiskEvaluator`

Current ambiguity:

- both modules represent authoritative risk contracts
- request models are named the same but describe different shapes and semantics
- runtime code currently imports `risk.contracts`, not `cilly_trading.risk_framework.contract`

### 3. Ingestion ownership is split

Evidence:

- `src/cilly_trading/ingestion.py` handles ingestion into SQLite using `data_layer.ingestion_validation`
- `src/cilly_trading/engine/data.py` also performs deterministic snapshot ingestion and snapshot persistence

Current ambiguity:

- there is no single ingestion boundary
- ingestion behavior exists both as a product-level module and inside engine data

### 4. Orchestration ownership is split across API, engine, and orchestrator packages

Evidence:

- `src/api/main.py` contains HTTP-triggered orchestration
- `src/cilly_trading/orchestrator/runtime.py` exposes execution gating orchestration
- `src/cilly_trading/engine/analysis/operator_trigger.py` exposes operator-triggered analysis workflow logging
- `src/cilly_trading/engine/pipeline/orchestrator.py` owns risk-before-execution pipeline orchestration

Current ambiguity:

- orchestration is not owned by one package
- some orchestration modules live under `engine`, some under `orchestrator`, and some inside the API layer

## Overloaded modules

The following modules are currently overloaded relative to the intended layer boundaries in this issue:

| Module | Why overloaded |
| --- | --- |
| `src/api/main.py` | Transport, workflow orchestration, runtime lifecycle, compliance evaluation, persistence coordination, filesystem reads, and API DTO ownership all coexist |
| `src/cilly_trading/engine/core.py` | Engine execution, persistence coordination, deterministic identity generation, logging, lineage, and artifact writing coexist |
| `src/cilly_trading/engine/data.py` | Provider access, validation, normalization, ingestion, and persistence coexist |
| `src/cilly_trading/models.py` | Domain models and API DTOs coexist |

## Additional boundary observations

- `src/api/test_*.py` places API tests inside the runtime package tree instead of under `tests/`, which weakens the distinction between production API code and verification assets.
- `src/cilly_trading/engine/order_execution_model.py` enforces orchestrator-only access by inspecting the Python call stack, which signals a missing explicit boundary contract between orchestration and execution rather than a clear package-level dependency boundary.

## Audit conclusion

The repository already has recognizable layer concepts, but they are not cleanly separated in the current implementation. The strongest current issues are:

1. API/control-plane code owns significant workflow orchestration and some persistence.
2. Engine core is coupled to concrete persistence.
3. Repository code depends upward on engine entities.
4. Model and contract ownership is duplicated across multiple package roots.
5. Several large modules currently combine responsibilities from multiple layers.

This audit documents the current state only and is intended to support later target-architecture decisions.
