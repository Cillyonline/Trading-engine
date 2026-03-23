# Strategy Registry

## Overview

The engine uses a central strategy registry as the single source of truth for strategy loading and onboarding metadata.
All strategies are registered explicitly via code and loaded through registry APIs.

Location: `src/cilly_trading/strategies/registry.py`.

## Registration API

Use the explicit API:

- `register_strategy(strategy_key, factory, metadata)`
- `get_registered_strategies()`
- `get_registered_strategy_metadata()`
- `create_strategy(strategy_key)`
- `create_registered_strategies()`

Built-in strategies are initialized by `initialize_default_registry()`.

## Deterministic ordering rule

Deterministic ordering is guaranteed by returning registrations sorted by stable strategy key in `get_registered_strategies()`.

## Metadata persistence rule

Validated onboarding metadata is stored per registry entry and returned deterministically for comparison-oriented consumers.
Metadata is validated before registry mutation; invalid onboarding definitions never enter the registry.

## Duplicate registration rule

If the same strategy key is registered twice, validation raises `StrategyValidationError` with message format:

- `strategy already registered: <KEY>`

## Scope boundaries

Out of scope (intentionally unsupported):

- dynamic plugin loading
- reflection-based auto-discovery
- external strategy packages
