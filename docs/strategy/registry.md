# Strategy Registry

## Overview

The engine uses a **central strategy registry** as the single source of truth for strategy loading.
All strategies are registered explicitly via code and then loaded through registry APIs.

Location: `src/cilly_trading/strategies/registry.py`.

## Registration API

Use the explicit API:

- `register_strategy(strategy_key, factory)`
- `get_registered_strategies()`
- `create_strategy(strategy_key)`
- `create_registered_strategies()`

Built-in strategies are initialized by `initialize_default_registry()`.

## Deterministic ordering rule

Deterministic ordering is guaranteed by returning registrations sorted by stable strategy key in `get_registered_strategies()`.

## Duplicate registration rule

If the same strategy key is registered twice, the registry raises:

- `DuplicateStrategyRegistrationError`

Error message format:

- `strategy already registered: <KEY>`

## Scope boundaries

Out of scope (intentionally unsupported):

- dynamic plugin loading
- reflection-based auto-discovery
- external strategy packages
