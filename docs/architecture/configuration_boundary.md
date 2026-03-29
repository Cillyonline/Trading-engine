# Canonical Configuration Ownership

## Purpose

This document defines the single source of truth for configuration ownership
across strategy configuration, runtime request configuration, validation,
normalization, and documentation references.

It is a documentation-only contract for issue `#697`. It does not refactor
configuration code, remove inline defaults, or change runtime behavior. Its
purpose is to stop ownership drift before later implementation issues move code.

## Current Ownership Points Verified Manually

Manual validation against the current config flow shows that ownership is
currently split across these locations:

| Current source | Current role in config flow | Ownership risk |
| --- | --- | --- |
| `src/api/main.py` request models | Defines transport defaults and request constraints for fields such as `market_type`, `lookback_days`, `min_score`, and `limit` | API layer appears to own runtime defaults |
| `src/api/main.py` `default_strategy_configs` | Supplies request-time strategy defaults before execution | Strategy defaults live outside strategy schema ownership |
| `src/cilly_trading/strategies/config_schema.py` `ConfigKeySpec` and per-strategy schema tuples | Defines strategy keys, schema defaults, coercion, and some per-key validation | Schema ownership overlaps with API defaults |
| `src/cilly_trading/strategies/config_schema.py` normalization helpers | Applies coercion, default fill-in, and cross-field repair for known strategies | Normalization semantics are separate from API merge semantics |
| `src/api/config.py` and `src/cilly_trading/config/external_data.py` | Hold process-wide constants and runtime toggles | Process defaults are distributed across modules |
| Architecture and strategy docs | Describe parts of the flow in separate documents | Documentation can describe the same rule in multiple places |

This issue defines who owns those responsibilities without changing the current
implementation locations yet.

## Canonical Ownership Model

Configuration ownership is assigned by responsibility, not by the module that
currently happens to contain a default.

The canonical owners are:

| Responsibility | Canonical owner | What that owner controls | What that owner does not control |
| --- | --- | --- | --- |
| Process-wide runtime defaults and environment-backed runtime config | Runtime configuration boundary under `src/cilly_trading/config` | Process-scoped defaults, environment parsing, precedence for process config, validated runtime config objects | Strategy key catalogs, request transport schemas |
| Strategy configuration defaults, aliases, coercion, and cross-field normalization | Strategy schema layer in `src/cilly_trading/strategies/config_schema.py` | Canonical strategy keys, default values, allowed types, alias handling, normalization rules, cross-field validation | HTTP parsing, endpoint-specific request shape |
| Request transport parsing | API request models and query models in `src/api/main.py` | HTTP payload shape, basic request-entry validation needed to parse a request | Canonical ownership of runtime defaults, strategy defaults, or normalization semantics |
| Documentation references for config behavior | This document | Ownership rules, boundary rules, precedence rules, and documentation-routing rules | Repeating detailed default tables or transport examples that belong elsewhere |

## OPS-P46 Bounded Server Environment and Filesystem Contract

For issue `#833`, this document also defines ownership of the bounded
first-paper server environment contract.

Canonical ownership for the deployment contract:

| Responsibility | Canonical owner | Contract scope |
| --- | --- | --- |
| First-clean-server environment variable contract | `docs/operations/runtime/staging-server-deployment.md` and `.env.example` | Required env keys, host bind-mount variables, runtime env defaults, UID/GID contract |
| Conditional provider secret requirements | `docs/operations/runtime/staging-server-deployment.md` | Snapshot-first default (no provider secrets required), explicit out-of-scope condition for future provider-secreted modes |
| Bounded filesystem path contract | `docker/staging/docker-compose.staging.yml` and `docs/operations/runtime/staging-server-deployment.md` | DB/artifact/journal/log/runtime-state path mapping and persistence class per path |
| Ownership and permissions expectations | `docker/staging/docker-compose.staging.yml` and `docs/operations/runtime/staging-server-deployment.md` | Container runtime UID/GID and host writable-directory precondition |

Server deployment boundary rules for first paper deployment:
- One bounded server environment contract exists and is authoritative in the
  staging runbook plus `.env.example`.
- Compose, docs, and env guidance must define the same path values.
- Persistence expectations must explicitly distinguish restart/redeploy
  continuity from host-directory deletion reset behavior.
- Runtime-state and file-log paths may be bind-mounted while runtime authority
  remains in-process and stdout/stderr logs remain authoritative unless a later
  issue changes that contract.

## Single Source of Truth Rules

The single source of truth is determined by decision type:

- Strategy config defaults are owned by the strategy schema layer.
- Strategy config validation is owned by the strategy schema layer.
- Strategy config normalization is owned by the strategy schema layer.
- Process-wide runtime defaults are owned by the runtime configuration boundary.
- Request model defaults are transport conveniences today, not canonical config
  ownership.
- Documentation that needs to state who owns a config rule must point to this
  document instead of redefining ownership locally.

If an implementation artifact conflicts with this ownership model, the artifact
is treated as temporary placement and a follow-up issue must align code to the
owner defined here.

## Responsibility Boundaries

### 1. Strategy Config Defaults

Canonical owner: `src/cilly_trading/strategies/config_schema.py`

Rules:

- The authoritative default for a strategy key comes from the strategy schema,
  not from API-layer merge dictionaries.
- A strategy-specific default bundle may exist as a boundary-level input, but
  it is an override source consumed by the boundary, not a second owner of the
  default catalog.
- Consumer modules must not invent or persist their own strategy default sets.
- Inline dictionaries such as `default_strategy_configs` are current-state
  implementation artifacts, not long-term authorities.

### 2. Validation

Canonical owners:

- Request-entry transport validation: API request and query models.
- Runtime config validation: runtime configuration boundary.
- Strategy config validation: strategy schema layer.

Rules:

- API models validate only enough to parse HTTP input safely.
- API models must not become the owner of strategy semantics.
- The runtime configuration boundary validates process-scoped runtime inputs and
  any request-scoped runtime fields it canonically resolves.
- The strategy schema layer validates known strategy keys, allowed value types,
  aliases, and cross-field invariants.
- Consumers after boundary resolution must treat config as already validated and
  must not silently revalidate into different semantics.

### 3. Normalization

Canonical owner: strategy schema layer for strategy config; runtime
configuration boundary for process/runtime config.

Rules:

- Normalization means canonical key selection, type coercion, default fill-in,
  and deterministic cross-field repair for configuration the owner owns.
- Strategy normalization belongs in the strategy schema layer because it depends
  on strategy-specific keys and invariants.
- Runtime normalization for process-scoped values belongs in the runtime
  configuration boundary.
- API handlers may package raw request input, but they do not own canonical
  normalization behavior.
- Engine and strategy consumers must not apply a second normalization pass that
  changes previously resolved semantics.

### 4. Documentation References

Canonical owner: this document for ownership and boundary decisions.

Rules:

- Documents that describe strategy behavior may mention config keys and examples
  but must not redefine which layer owns defaults, validation, or
  normalization.
- Documents that describe API payloads may document request fields but must not
  claim ownership of config semantics beyond transport parsing.
- When another document needs an ownership statement, it should reference this
  document and keep only context-specific details locally.
- Future issues may add detailed implementation docs, but those docs must
  inherit ownership from this document instead of restating competing rules.

## Precedence and Flow

This issue does not change runtime behavior, but the intended canonical
resolution order is:

1. runtime-boundary process defaults
2. validated environment overrides
3. strategy schema defaults
4. boundary-level strategy default bundle for the selected strategy, if one is
   explicitly defined
5. validated request or preset overrides

Within that flow:

- The API layer may collect raw request values.
- The boundary resolves runtime configuration ownership.
- The strategy schema layer resolves strategy configuration ownership.
- Execution consumes only resolved configuration objects.

No consumer may add a separate hidden precedence layer after canonical
resolution.

## Boundary Rules

The following rules are mandatory for later implementation issues:

- One responsibility, one owner. A layer may consume another layer's config but
  must not become a second authority for the same decision.
- Defaults must be defined where the corresponding validation semantics live.
- Validation and normalization for the same config domain must stay in the same
  ownership layer.
- Request parsing is not equivalent to config ownership.
- Consumer convenience must not create new canonical defaults.
- Documentation examples are informative only unless they point back to the
  canonical owner defined here.
- If current code still embeds defaults in a non-owner layer, follow-up issues
  must preserve behavior first and then move ownership without changing the
  contract.

## Implementation Readiness for Follow-up Issues

Later issues can use this document without making new ownership decisions:

- Move API-layer strategy defaults behind the canonical owner without changing
  effective behavior.
- Align request handling so transport parsing stays in `src/api/main.py` while
  strategy semantics stay in `src/cilly_trading/strategies/config_schema.py`.
- Consolidate process-wide runtime defaults under `src/cilly_trading/config`
  without changing existing runtime behavior.
- Update related docs to reference this file instead of defining duplicate
  ownership rules.

## Manual Validation Performed

Manual validation for issue `#697` consisted of source review of:

- `src/api/main.py`
- `src/cilly_trading/strategies/config_schema.py`
- `src/api/config.py`
- `src/cilly_trading/config/external_data.py`
- existing config-related architecture and strategy docs under `docs/architecture`

That review confirmed that configuration responsibilities are presently
distributed across API defaults, schema defaults, normalization helpers, and
documentation, which is why this ownership contract is required.
