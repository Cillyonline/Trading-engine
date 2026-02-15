# Strategy Pack Model (Phase 21)

## Purpose

This document defines the formal and deterministic structure for strategy packs.
It is the canonical reference for pack layout, metadata, naming, and boundaries in Phase 21.

## Pack Directory Structure

A strategy pack MUST follow this directory layout:

```text
strategy/packs/
  <pack_id>/
    pack.yaml
    README.md
    strategies/
      <strategy_id>.yaml
    internal/
      ...
```

### Structure Rules

- `strategy/packs/` is the root namespace for all packs.
- `<pack_id>/` is the immutable pack folder identifier.
- `pack.yaml` is required and is the only required metadata file.
- `README.md` is optional and informational only.
- `strategies/` contains public strategy definitions consumed by deterministic expansion.
- `internal/` is optional and reserved for pack-private assets.

## Required Metadata File

Each pack MUST include `pack.yaml` with these required fields:

- `pack_id` (string)
- `version` (string, SemVer `MAJOR.MINOR.PATCH`)
- `api_version` (string, strategy-pack model version)
- `owner` (string)
- `description` (string)
- `strategies` (array of strategy entries)

Each entry in `strategies` MUST include:

- `id` (string)
- `path` (string, relative path under `strategies/`)
- `enabled` (boolean)

### Metadata Constraints

- `pack_id` in `pack.yaml` MUST exactly match `<pack_id>` directory name.
- `version` MUST be explicit; implicit or generated versions are forbidden.
- `path` MUST reference a file under `strategies/` and MUST NOT traverse directories (`..` forbidden).
- Strategy `id` values MUST be unique within one pack.

## Naming Conventions

### Pack IDs

- Lowercase snake_case: `^[a-z][a-z0-9_]*$`
- Stable and immutable once published.

### Strategy IDs

- Lowercase snake_case: `^[a-z][a-z0-9_]*$`
- Unique within the pack.

### File Names

- Strategy files: `<strategy_id>.yaml`
- Metadata file name is fixed: `pack.yaml`

## Deterministic Constraints

Strategy packs MUST satisfy all constraints below:

1. **No implicit discovery**: only strategies listed in `pack.yaml` are considered.
2. **Stable ordering**: strategy expansion order is the declared order in `pack.yaml`.
3. **No runtime mutation**: pack metadata and strategy definitions are read-only at runtime.
4. **No time-dependent values**: timestamps, random values, and environment-derived defaults are forbidden in pack definitions.
5. **Pure references**: each strategy entry points to a static file path; dynamic path construction is forbidden.
6. **Version pinning**: `version` and `api_version` MUST be explicitly declared.

## Allowed Dependencies

Within a pack, allowed dependencies are limited to:

- `pack.yaml`
- Files under `strategies/`
- Files under `internal/` referenced by strategies in the same pack

Forbidden dependencies:

- Cross-pack file references
- Network or remote resources
- Runtime environment variables as structural inputs
- Python module imports or executable hooks declared by pack metadata

## Public vs Internal Boundaries

### Public Surface

Only the following elements are public and integration-relevant:

- `pack.yaml`
- Files under `strategies/` referenced by `pack.yaml`

### Internal Surface

- `internal/` and any non-referenced files are pack-internal implementation details.
- Internal files MUST NOT be referenced by external packs.
- Internal structure MAY evolve without changing pack public contract, as long as referenced public strategy paths remain valid.

## Governance Notes

- Any change to `pack.yaml` required fields, naming rules, deterministic constraints, or public boundary rules is governance-relevant.
- Backward-incompatible changes require a `version` major bump.
