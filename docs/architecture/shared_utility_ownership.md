# Shared Utility Ownership

Issue: `#696`  
Status: documentation only  
Scope: define canonical ownership for shared utility categories without moving
helpers, changing imports, deleting duplicates, or changing runtime behavior.

## Purpose

This document defines the single source of truth for shared utility logic that
is currently duplicated across multiple modules.

It answers four implementation questions:

- which utility category has canonical ownership
- where helpers in that category must live
- which module categories may consume those helpers
- which module categories must not define competing implementations

This document is an ownership contract only. It does not authorize utility
moves, import rewrites, refactors, or runtime behavior changes in this issue.

## Covered Utility Categories

The ownership model in this document covers the shared utility categories named
in the issue:

- hashing
- normalization
- canonical JSON / serialization
- signal identity helpers
- configuration helpers

The categories are defined narrowly enough to support follow-up implementation
issues without reopening ownership decisions.

## Ownership Principles

The following rules apply to every shared utility category in scope:

1. Every category has exactly one canonical owner boundary.
2. Shared helpers must be defined only in the owner boundary for that category.
3. Consumers may call owner utilities but must not reimplement the same helper
   logic locally.
4. A helper belongs to the narrowest owner that matches its contract. Domain-
   specific variants stay with the owning domain and must not become generic
   shared helpers unless a later issue explicitly expands scope.
5. If a helper is used by more than one module category and its logic is not
   transport-specific or storage-specific, it must live in the canonical owner
   boundary rather than in one consumer module.

## Canonical Ownership Matrix

| Utility category | Canonical owner | Canonical location | Allowed consumers | Must not own competing implementations |
| --- | --- | --- | --- | --- |
| Hashing | shared model / contract boundary | `src/cilly_trading/models.py` or a later model-owned helper module extracted from it | engine core, repositories, alerts, metrics, API adapters that need deterministic IDs or artifact digests | API entrypoints, engine modules, repository modules, alert modules, metrics modules |
| Canonical JSON / serialization | shared model / contract boundary | `src/cilly_trading/models.py` or a later model-owned helper module extracted from it | engine core, repositories, alerts, metrics, artifact writers, API adapters that persist deterministic payloads | API entrypoints, engine modules, repository modules, alert modules, metrics modules |
| Signal identity helpers | shared model / contract boundary | `src/cilly_trading/models.py` or a later model-owned signal-identity helper module extracted from it | engine core, alerts, repositories, orchestration modules | API entrypoints, engine modules, repository modules, alert modules |
| Shared normalization for deterministic identity / canonical serialization | shared model / contract boundary | `src/cilly_trading/models.py` or a later model-owned helper module extracted from it | engine core, alerts, repositories, metrics, artifact writers | API entrypoints, engine modules, repository modules, alert modules, metrics modules |
| Configuration helpers | strategy and config boundary, split by concern | `src/cilly_trading/strategies/config_schema.py` for strategy config; `src/cilly_trading/config/*` for process/runtime config | API entrypoints, engine core, orchestration modules, compliance assembly | API entrypoints, engine modules, strategy implementations, compliance modules |

## Category Definitions

### 1. Hashing

This category includes:

- stable `sha256` digest helpers
- deterministic byte-to-hex helpers
- shared digest wrappers used to create IDs or sidecar hashes

Canonical owner:

- the shared model / contract boundary

Canonical location:

- current owner location: `src/cilly_trading/models.py`
- allowed future extraction target: a model-owned helper module under
  `src/cilly_trading/` that remains below the models / contracts boundary

Ownership rule:

- if hashing exists only to support deterministic shared identities or
  canonical artifact payloads, the helper is model-owned even when an engine,
  alert, or repository consumer calls it

Not included:

- hashing tied to one storage technology
- hashing tied to one external protocol
- one-off file verification behavior that is inseparable from a storage adapter

### 2. Canonical JSON / serialization

This category includes:

- canonical `json.dumps(...)` wrappers
- sorted-key deterministic serialization helpers
- helpers that enforce compact separators, UTF-8 encoding, or newline rules for
  deterministic payload generation

Canonical owner:

- the shared model / contract boundary

Canonical location:

- current owner location: `src/cilly_trading/models.py`
- allowed future extraction target: a model-owned serialization helper module
  under `src/cilly_trading/`

Ownership rule:

- canonical serialization used across more than one module category is a shared
  contract concern, not an engine-local or repository-local concern

Not included:

- schema-specific artifact writer orchestration
- transport response rendering
- storage adapter code that only writes bytes after canonical bytes are already
  produced

### 3. Signal identity helpers

This category includes:

- signal identity payload builders
- signal ID generation helpers
- stable field-order and field-selection rules used to derive signal identity

Canonical owner:

- the shared model / contract boundary

Canonical location:

- current owner location: `src/cilly_trading/models.py`
- allowed future extraction target: a model-owned signal identity helper module
  under `src/cilly_trading/`

Ownership rule:

- signal identity is a shared domain contract and must not be independently
  defined by engine, alert, repository, or API modules

Boundary note:

- this category does not automatically include every deterministic ID in the
  system
- dataset identity, alert-event identity, or analysis-run identity may keep
  domain-specific payload contracts, but any shared normalization or hashing
  primitives they use still belong to their canonical utility owners defined in
  this document

### 4. Shared normalization for deterministic identity / canonical serialization

This category includes:

- recursive normalization helpers used before canonical serialization
- deterministic list / mapping normalization used by identity helpers
- shared value coercion for canonical payload construction

Canonical owner:

- the shared model / contract boundary

Canonical location:

- current owner location: `src/cilly_trading/models.py`
- allowed future extraction target: a model-owned normalization helper module
  under `src/cilly_trading/`

Ownership rule:

- normalization helpers belong here only when they support deterministic shared
  identity or canonical serialization rules across module categories

Not included:

- request validation normalization
- strategy-key validation helpers
- ingestion-specific cleanup
- UI or API input trimming rules

Those narrower normalization concerns remain owned by their current domain
boundaries unless a future issue defines a different shared owner.

### 5. Configuration helpers

This category must be split by configuration concern because one owner would be
too broad and would recreate duplication under a different name.

#### 5a. Strategy configuration helpers

This subcategory includes:

- strategy config key catalogs
- config coercion and alias handling
- strategy-specific defaults
- cross-field strategy validation

Canonical owner:

- strategy boundary

Canonical location:

- `src/cilly_trading/strategies/config_schema.py`

Allowed consumers:

- API entrypoints
- engine core
- orchestration modules
- strategy registry and lifecycle modules

Must not own competing implementations:

- strategy implementation files
- API request handlers
- engine execution modules outside the strategy boundary

#### 5b. Process/runtime configuration helpers

This subcategory includes:

- environment parsing helpers
- runtime default resolution
- process-scoped feature-gate loading
- non-strategy configuration precedence helpers

Canonical owner:

- configuration boundary

Canonical location:

- `src/cilly_trading/config/*`

Allowed consumers:

- API entrypoints
- engine core
- orchestration modules
- compliance assembly

Must not own competing implementations:

- `src/api/*`
- `src/cilly_trading/engine/*`
- compliance guard modules
- strategy implementation modules

Ownership rule:

- no consumer may add new config defaulting or precedence logic outside
  `src/cilly_trading/config/*` or `src/cilly_trading/strategies/config_schema.py`

## Consumer Rules By Module Category

The table below defines which module categories may consume shared utilities and
under what limits.

| Consumer category | May consume | Must not do |
| --- | --- | --- |
| API entrypoints | configuration helpers; shared hashing / serialization / identity helpers only when required to translate or persist deterministic domain payloads | define new canonical hashing, normalization, serialization, signal identity, or config helpers |
| orchestration modules | configuration helpers and shared domain utilities needed to coordinate use cases | become a second owner for canonical utility logic |
| engine core | shared hashing, canonical serialization, signal identity, deterministic normalization, config helpers | redefine shared helper stacks locally |
| repositories | shared hashing and serialization helpers when persistence requires deterministic payloads | own canonical helper definitions for those categories |
| alerts / metrics / artifact modules | shared hashing, serialization, and normalization helpers | define generic versions of those helpers outside their domain-specific payload rules |
| strategy implementations | validated strategy config outputs and strategy-local validation helpers only when truly local | parse or normalize shared strategy config contracts independently from `config_schema.py` |

## Placement Rules For Follow-up Implementation Issues

Future issues that consolidate duplicated helpers must apply these placement
rules:

1. If the helper is shared across engine and model consumers and defines a
   domain contract, place it in the model / contract owner boundary.
2. If the helper resolves strategy configuration shape, defaults, aliases, or
   coercion, place it in `src/cilly_trading/strategies/config_schema.py`.
3. If the helper resolves process-scoped config loading, precedence, or env
   parsing, place it in `src/cilly_trading/config/*`.
4. If a helper mixes canonical serialization with artifact file writing, split
   ownership conceptually: serialization belongs to the shared owner; file
   writing remains with the artifact or repository owner.
5. If a helper is still specific to one domain contract after review, keep it
   in that domain and do not force it into a generic shared utility layer.

## Prohibited Ownership Patterns

The following patterns are not allowed after this ownership model is adopted:

- engine-local copies of canonical JSON or `sha256` helpers
- repository-local copies of identity normalization helpers
- alert-local copies of generic shared canonical serialization helpers
- API-local parsing of strategy config defaults or aliases
- compliance-local parsing helpers that reimplement runtime config loading rules
- new generic `utils.py` files under unrelated feature modules

## Mapping From Current Duplication Findings

This ownership model resolves the main duplication families identified in
`docs/architecture/code_b6_duplication_audit.md` as follows:

| Current duplication family | Canonical owner defined here |
| --- | --- |
| canonical JSON + SHA-256 + signal identity duplicated between `models.py` and `engine/core.py` | shared model / contract boundary |
| alert-event identity reusing the same normalization + canonical JSON + hash pattern | shared normalization / hashing / serialization primitives in the model boundary; alert-specific payload contract remains alert-owned |
| canonical artifact serialization repeated across artifact modules | canonical serialization and hashing stay shared-owner utilities; file output remains artifact-module-owned |
| strategy config parsing split across schema and strategy implementations | strategy config helpers owned by `src/cilly_trading/strategies/config_schema.py` |
| compliance guard config parsing repeated across modules and API assembly | process/runtime config helpers owned by `src/cilly_trading/config/*` |

## Rules For Future Issue Creation

When creating implementation issues after `#696`:

- name the utility category being consolidated explicitly
- reference the canonical owner from this document
- restrict file scope to the owner boundary plus direct consumers being rewired
- do not combine shared-utility consolidation with unrelated refactors
- do not move domain-specific helper contracts into a generic shared location
  unless this document already names that owner

If a proposed issue cannot name one of the owners defined here, the issue is
not precise enough yet and should be clarified before implementation.

## Manual Validation For Issue #696

Manual validation for this ownership model was performed by reviewing:

- `docs/architecture/code_b6_duplication_audit.md`
- `docs/architecture/core_module_responsibility_map.md`
- `docs/architecture/configuration_boundary.md`

Validation checks:

- each in-scope utility category has one canonical owner
- canonical locations are defined precisely enough to scope follow-up issues
- allowed consumers are stated
- forbidden competing owners are stated
- configuration helpers are split only where a single owner would be ambiguous
- the document stays within scope by defining ownership only, with no runtime
  changes or code movement
