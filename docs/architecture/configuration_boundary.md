# Canonical Configuration Boundary

## Purpose

This document defines the canonical validated configuration boundary for
runtime, environment, and strategy-related inputs.

It is a contract document for issue `#605`. It does not implement the boundary
and it does not refactor existing consumers. Its purpose is to remove
precedence, ownership, and file-scope ambiguity before implementation begins.

## Included Sources

The canonical boundary includes every raw input that changes runtime behavior,
request behavior, or strategy behavior.

### 1. Process environment inputs

These are process-scoped values read from the environment today:

- `CILLY_LOG_LEVEL` read in `src/api/main.py`
- `CILLY_PORTFOLIO_POSITIONS` read in
  `src/cilly_trading/engine/portfolio/state.py`

Future environment-backed runtime switches belong to the same boundary even if
their final parsing location moves.

### 2. Process-wide runtime defaults and feature gates

These are code-defined defaults or toggles that affect process behavior today:

- `EXTERNAL_DATA_ENABLED` in `src/cilly_trading/config/external_data.py`
- `SIGNALS_READ_MAX_LIMIT` in `src/api/config.py`
- any future process-wide defaults that are currently embedded in consumers

These values are part of the canonical boundary even when they are presently
stored as module constants.

### 3. Request-scoped runtime inputs

These are raw request inputs that shape one API read or one engine run today:

- request defaults and constraints in `src/api/main.py`
- `market_type`, `lookback_days`, `min_score`, `limit`, and similar request
  fields
- `strategy_config`, `preset_id`, `preset_ids`, and preset payload parameters
- inline `default_strategy_configs` currently merged in `src/api/main.py`

Request models remain the transport surface, but their runtime defaults and
override semantics belong to the canonical configuration boundary.

### 4. Strategy schema artifacts

These are the strategy-specific configuration artifacts that already exist:

- `ConfigKeySpec`
- `RSI2_SCHEMA`
- `TURTLE_SCHEMA`
- `normalize_rsi2_config(...)`
- `normalize_turtle_config(...)`

Those artifacts currently live in
`src/cilly_trading/strategies/config_schema.py` and are part of the canonical
boundary because they define the allowed structure, types, defaults, and
invariants of strategy configuration.

## Excluded Sources

The following are outside this contract:

- consumer-specific implementation details after configuration has already been
  resolved
- database rows, snapshots, and persisted analysis artifacts
- UI-based config editing flows
- secret-management or credential-distribution work
- refactoring unrelated config consumers

## Ownership Model

The authoritative owner of runtime configuration loading is the configuration
boundary under `src/cilly_trading/config`.

The intended ownership split is:

- `src/cilly_trading/config` owns process-scoped loading, precedence, and
  validated runtime objects
- `src/cilly_trading/strategies/config_schema.py` owns strategy-specific key
  catalogs, coercion rules, defaults, aliases, and cross-field validation
- API request models own only request transport validation that is necessary to
  parse HTTP input
- engine and API consumers own no additional defaults or precedence rules

This means consumer modules may gather raw inputs, but they are not the final
authority for combining defaults, environment overrides, and strategy overrides.

## Validation and Defaulting Expectations

The follow-up implementation should apply these rules:

### Validation

- Raw values are parsed and validated exactly once at the boundary.
- Invalid process-scoped configuration fails fast during startup or boundary
  initialization.
- Invalid request-scoped configuration fails at request-entry validation and is
  not recovered through silent fallback.
- Invalid explicit strategy values are rejected by the strategy schema layer.
- Unknown strategy keys are rejected at the boundary.
- Alias resolution happens before strategy validation completes.

### Defaulting

- Defaults come only from canonical boundary definitions.
- Missing process-scoped values may use documented boundary defaults.
- Missing request-scoped values may use documented boundary defaults.
- Missing strategy keys may use schema-defined defaults.
- An explicitly provided invalid value must not be replaced silently with a
  default.

### Precedence

The canonical precedence order is:

1. boundary-defined base defaults
2. validated process-scoped environment overrides
3. validated boundary-owned runtime or preset defaults for the current request
4. validated explicit request overrides

Within the strategy subdocument, the order is:

1. strategy schema defaults
2. boundary-owned default strategy bundle for the selected strategy, if one
   exists
3. explicit preset or request strategy overrides

No consumer may add another precedence layer outside this order.

## Intended Authoritative Loading Boundary

The intended runtime flow is:

1. process startup loads process-scoped config once through the canonical
   boundary
2. request entrypoints submit raw request inputs to the canonical boundary
3. the boundary returns validated runtime and strategy config objects
4. engine and API consumers execute only against those resolved objects

Under this contract:

- `src/api/main.py` is a caller of the boundary, not the owner of config
  defaulting
- inline defaults in consumer modules are temporary raw artifacts that must move
  behind the boundary in follow-up work
- strategy normalization is invoked by the boundary, not reimplemented by
  request handlers

## Minimal Initial Implementation File Scope

The first implementation slice should stay narrow and modify only these files:

- `src/cilly_trading/config/__init__.py`
- `src/cilly_trading/config/external_data.py`
- `src/api/config.py`
- `src/cilly_trading/strategies/config_schema.py`

That initial slice is responsible only for defining the canonical runtime
boundary primitives:

- process-scoped config entrypoints
- process-wide defaults and feature-gate definitions
- strategy-schema validation/defaulting interfaces
- exported helpers that later consumer-wiring issues can call

Consumer rewiring in `src/api/main.py`, engine modules, or other request paths
is intentionally out of this initial slice and should be handled by separate
follow-up issues after the boundary primitives exist.

## Manual Review Checklist for #605

Manual design review should confirm that this contract accounts for the current
artifact classes below without leaving precedence decisions open:

| Artifact class | Current examples | Boundary decision |
| --- | --- | --- |
| Env gates | `CILLY_LOG_LEVEL`, `CILLY_PORTFOLIO_POSITIONS` | process-scoped, boundary-owned |
| Runtime constants | `EXTERNAL_DATA_ENABLED`, `SIGNALS_READ_MAX_LIMIT` | process-scoped defaults, boundary-owned |
| API defaults | request model defaults and `default_strategy_configs` in `src/api/main.py` | raw request inputs today, boundary-owned precedence later |
| Strategy schema artifacts | `RSI2_SCHEMA`, `TURTLE_SCHEMA`, normalization helpers | strategy-owned validation/defaulting, called by boundary |

Success for this review is that a follow-up implementer can begin the boundary
work without making new decisions about source inclusion, validation ownership,
defaulting behavior, or precedence order.
