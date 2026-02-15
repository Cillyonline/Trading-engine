# Strategy Pack Model

## Purpose

This document defines the formal, deterministic, and governance-aligned structure for strategy packs.

## Scope

### IN SCOPE

- Define directory structure for strategy packs
- Define required metadata file
- Define naming conventions
- Define deterministic constraints
- Define allowed dependencies
- Define public vs internal boundaries

### OUT OF SCOPE

- Implementing new strategies
- Backtesting redesign
- Performance optimization
- Plugin architecture

## Directory Structure

The canonical strategy pack structure is:

```text
strategy_packs/
  <pack_name>/
    metadata.yaml
    strategies/
      <strategy_id>/
        definition.yaml
        rules.yaml
    internal/
      ...
```

Rules:

- `strategy_packs/` is the canonical root namespace.
- `<pack_name>/` is the immutable pack directory identifier.
- `metadata.yaml` is REQUIRED and is the only REQUIRED metadata file.
- `strategies/` contains strategy definitions; each strategy is a directory `<strategy_id>/`.
- `definition.yaml` and `rules.yaml` are part of the public contract for a strategy.
- `internal/` is OPTIONAL and pack-private; engine MUST NOT treat it as public contract.
- Only files and directories defined in this model are part of the pack contract; all other files MUST be ignored by the engine.

## Naming Conventions

- `<pack_name>` MUST be snake_case.
- `<strategy_id>` MUST be kebab-case.
- Required file names MUST be lowercase and fixed: `metadata.yaml`, `definition.yaml`, `rules.yaml`.
- Names MUST NOT contain spaces.
- Names MUST NOT contain uppercase characters.

## Required Metadata File

`metadata.yaml` is REQUIRED for every strategy pack.

| Field | Type | Required | Constraints |
|---|---|---|---|
| `pack_id` | string | Yes | MUST be immutable once published; MUST match directory `<pack_name>`. |
| `version` | string | Yes | MUST follow SemVer (`MAJOR.MINOR.PATCH`). |
| `description` | string | Yes | REQUIRED human-readable description. |
| `author` | string | Yes | REQUIRED pack author identifier. |
| `created_at` | string | Yes | MUST be ISO-8601 timestamp string. |
| `deterministic_hash` | string | Yes | REQUIRED; MUST change when pack logic changes. |
| `engine_compatibility` | string | Yes | MUST be a single SemVer (for exact compatibility) or SemVer range expression (for bounded compatibility). |
| `dependencies` | array | Yes | REQUIRED explicit list; MAY be empty; each entry MUST declare dependency identifier and version constraint in deterministic order. |
| `license` | string | No | OPTIONAL license identifier or expression. |
| `tags` | array[string] | No | OPTIONAL descriptive tags. |
| `homepage` | string | No | OPTIONAL canonical URL. |

Metadata constraints:

- Metadata MUST be fully explicit and MUST NOT be generated at runtime.
- Metadata MUST be parseable deterministically.
- Metadata MUST NOT use YAML anchors or YAML merge keys.
- Dependency resolution MUST be deterministic and order-stable.

## Determinism Constraints

- Strategy packs MUST NOT use system time as an implicit input.
- Strategy packs MUST NOT use randomness.
- Strategy packs MUST NOT access network resources.
- Strategy packs MUST NOT access filesystem paths outside the pack boundary.
- Strategy packs MUST NOT branch on environment variables or host-specific properties.
- Strategy packs MUST NOT use runtime reflection, dynamic imports, or plugin loading.
- Strategy packs MUST produce identical outputs for identical inputs across environments.

A strategy pack MUST produce identical outputs for identical inputs across environments.

## Allowed Dependencies

- Strategy packs MUST depend ONLY on deterministic internal engine interfaces.
- Strategy packs MUST NOT use cross-pack imports or cross-pack file references.
- Strategy packs MUST NOT declare or invoke executable hooks.
- Strategy packs MUST NOT use runtime reflection or runtime imports.
- Strategy packs MUST NOT use plugin loading.

## Public vs Internal Boundaries

Public contract elements:

- `metadata.yaml`
- `strategies/<strategy_id>/definition.yaml`
- `strategies/<strategy_id>/rules.yaml`

Internal elements:

- Everything under `internal/`
- Any other non-contract files

Boundary rules:

- External packs MUST NOT reference another pack’s internal files.
- Internal structure MAY change without breaking public contract, as long as public files remain valid.

## Versioning Rules

SemVer policy:

- MAJOR: REQUIRED for breaking changes to public contract, including directory structure, required metadata fields, determinism rules, or naming rules.
- MINOR: REQUIRED for backward-compatible additions, including new optional metadata fields and additive rule extensions that do not break compatibility.
- PATCH: REQUIRED for documentation, typo fixes, or clarifications ONLY.

Additional versioning rules:

- `pack_id` is immutable once published.
- `version` MUST be bumped on any public contract change.
- `deterministic_hash` MUST change when strategy logic changes.

## Governance Requirements

- Changes to the pack model or to a pack MUST be submitted via pull request.
- A pull request completing this issue MUST include `Closes #368` in the PR body.
- Governance-relevant changes (required fields, boundaries, determinism, naming) MUST trigger a MAJOR bump per Versioning Rules.

## Non-Goals

- Implementing new strategies
- Backtesting redesign
- Performance optimization
- Plugin architecture

FILES CHANGED: docs/strategy/pack_model.md

Acceptance Criteria Mapping:

- File `docs/strategy/pack_model.md` exists. → Satisfied by this file.
- Directory structure is explicitly defined. → `## Directory Structure`
- Required metadata fields are documented. → `## Required Metadata File`
- Determinism constraints are explicitly stated. → `## Determinism Constraints`
- No runtime changes. → Documentation-only change in this file.
