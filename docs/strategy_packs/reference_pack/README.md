## Overview
This reference pack defines a single canonical strategy implementation used as a deterministic baseline.

## Strategy Objective
Provide a harmless strategy entry that exercises registry and pack wiring without emitting actionable signals.

## Strategy Logic Summary
The strategy is registered with the stable name `REFERENCE` and always returns an empty signal list from `generate_signals`.

## Parameter Definitions
This strategy accepts a config object to match the engine strategy contract but does not read or mutate any parameters.

## Deterministic Behavior
This strategy produces identical outputs for identical inputs across environments.

## Risk Disclosure
This strategy does not provide trading recommendations and emits no signals.

## Version & Compatibility
Pack version: `1.0.0`.
Engine compatibility: `>=1.0.0`.

## Change Log Reference
See repository history for changes affecting `docs/strategy_packs/reference_pack/` and strategy registration.
