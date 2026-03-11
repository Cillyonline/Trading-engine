# Strategy Configuration Boundary

## Purpose

This document defines the strategy-specific portion of the canonical runtime
configuration boundary documented in
`docs/architecture/configuration_boundary.md`.

It does not create a separate configuration system. It assigns ownership for
strategy defaults, validation, alias handling, and per-request overrides so
follow-up implementation work can centralize those decisions without changing
feature scope.

## Included Strategy Inputs

The canonical strategy-configuration boundary includes these raw inputs:

- Schema artifacts in `src/cilly_trading/strategies/config_schema.py`
  (`ConfigKeySpec`, per-strategy schema definitions, and normalization helpers).
- Inline strategy default dictionaries that currently live in
  `src/api/main.py` (`default_strategy_configs`).
- Explicit request payloads that carry strategy parameters, including
  `strategy_config` and resolved preset parameters.

Everything above is in scope for validation and precedence decisions even when
the current implementation still reads those inputs from different places.

## Validation Ownership

Strategy-specific validation is owned by the strategy schema layer, not by API
request models and not by engine consumers.

The boundary is responsible for:

- resolving aliases to canonical strategy keys
- coercing values only through documented schema conversions
- applying strategy defaults for missing known keys
- enforcing per-key constraints and cross-field invariants
- rejecting unknown keys and conflicting alias/canonical pairs

Consumers outside the boundary may read only already-resolved strategy config.
They must not apply additional defaults, silently drop invalid keys, or invent
fallback behavior.

## Defaulting Expectations

Strategy defaulting happens in exactly two places and in this order:

1. Schema defaults defined by the strategy schema layer.
2. Explicit override payloads supplied by a preset or request.

Current inline API defaults are treated as temporary raw inputs, not as the
long-term owner of defaults. Follow-up implementation should move that ownership
behind the canonical boundary while preserving the same effective precedence:

- schema defaults provide the baseline
- boundary-owned default strategy bundles may override the baseline
- request-level strategy overrides win last

If a provided value fails validation, the boundary must report that failure. It
must not silently replace an invalid explicit value with a default.

## Request-Scoped Strategy Resolution

When an API request supplies strategy-related input, the request layer may
collect the raw payload, but it is not the authority for final strategy config.

The intended flow is:

1. request models accept raw strategy payloads
2. the canonical boundary resolves defaults and validates the payload
3. engine execution receives an immutable, validated strategy configuration

This keeps strategy precedence decisions out of `src/api/main.py` and prevents
the API layer from becoming a second configuration owner.

## Current Artifact Review

Manual design review for issue `#605` should account for these current artifacts:

- `src/cilly_trading/strategies/config_schema.py` contains the current
  per-strategy schema and normalization helpers.
- `src/api/main.py` contains inline `default_strategy_configs` that currently
  act as request-time defaults.
- API request models in `src/api/main.py` expose `strategy_config` and preset
  payloads as raw strategy inputs.

The follow-up implementer should treat those artifacts as sources to be absorbed
into the canonical boundary, not as competing authorities.
