# CLI Contract – Cilly Trading Engine

## 1. Purpose
- This document defines the deterministic command-line contract for the engine’s documented offline analysis CLI surface.
- This contract is documentation-only and does not introduce runtime behavior changes.
- Non-goals:
  - No new features.
  - No changes to engine logic.
  - No expansion of public API surface.

## 2. Authoritative CLI Entrypoint
- The single authoritative CLI entrypoint for deterministic engine execution is:
  - `python -m cilly_trading.engine.deterministic_run`
- No alternative entrypoints are supported as part of this CLI contract.
- Invocation context:
  - Module invocation (`python -m ...`) is required by this contract.
  - Script-path invocation support is not guaranteed.

## 3. Command Structure

### 3.1 Base Command
- Canonical form:
  - `python -m cilly_trading.engine.deterministic_run [--fixtures-dir <path>] [--output <path>] [--db-path <path>]`
- Deterministic invocation requirement:
  - Callers MUST use the canonical module entrypoint and documented arguments only.

### 3.2 Subcommands (if applicable)
- This CLI defines no subcommands.
- Any subcommand-style usage is unsupported.

### 3.3 Arguments
- Positional arguments:
  - No positional arguments are defined.
- Named arguments:
  - `--fixtures-dir <path>`: optional path to deterministic fixtures directory.
  - `--output <path>`: optional JSON output artifact path.
  - `--db-path <path>`: optional SQLite database path.
- Mutually exclusive flags:
  - None are documented; no mutually exclusive flag behavior is guaranteed.
- Unsupported patterns:
  - Undocumented flags.
  - Positional-only invocation patterns.
  - Subcommand syntax.

## 4. Argument Validation Rules
- Required vs optional:
  - All documented flags are optional at parse time.
  - If omitted, implementation defaults are used.
- Type validation:
  - CLI values are parsed as strings and interpreted as filesystem paths.
- Invalid input handling:
  - Invalid CLI syntax/unknown arguments MUST be treated as usage/validation errors.
  - Syntactically valid arguments that fail at runtime (for example, missing fixture files or invalid fixture content) MUST be treated as runtime failures.
- Parsing determinism:
  - Parsing MUST be deterministic and must not rely on ambiguous argument interpretation.

## 5. Exit Code Contract
- `0` → success.
- Non-zero → failure.
- Failure categories:
  - Validation / usage error (argument parsing or unsupported CLI usage).
  - Runtime failure (unexpected execution error, configuration/fixture/data failures during execution).
- Configuration-specific exit code categories beyond the above are not guaranteed.
- No undocumented success code is allowed (`0` is the only success code).
- Stdout/stderr behavior:
  - On success, printing the output artifact path to stdout is expected.
  - Detailed formatting of stderr/stdout for failure cases is not guaranteed.

## 6. Determinism Requirements
- The deterministic CLI run MUST execute without implicit randomness.
- The deterministic CLI run MUST NOT depend on network access.
- Environment-dependent behavior is not guaranteed unless explicitly documented.
- Config resolution order beyond explicit CLI flags and in-fixture configuration is not specified.
- Time, locale, and filesystem ordering guarantees are limited to documented deterministic behavior only; additional guarantees are not specified.

## 7. Unsupported CLI Usage
- Direct execution of internal modules as a supported interface (other than the authoritative entrypoint above).
- Any undocumented flags or invocation shapes.
- Interactive prompts; interactive CLI behavior is not supported.
- Treating side effects or internal implementation details as stable contract.

## 8. Stability Guarantees
- Stable:
  - The documented authoritative entrypoint.
  - The documented named arguments in this file.
  - The documented success/failure exit code contract categories.
- May change without contract guarantee:
  - Undocumented behavior.
  - Internal implementation details.
  - Failure-message wording/format.
- Deprecation policy:
  - No formal deprecation window is guaranteed for undocumented behavior.
