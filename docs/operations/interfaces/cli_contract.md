# CLI Contract – Cilly Trading Engine

## 1. Purpose
- This document defines a deterministic, bounded command-line interface contract for this repository.
- This contract is documentation-only and does not introduce runtime behavior changes.
- Non-goals:
  - No new features.
  - No changes to engine logic.
  - No expansion of public API surface.

## 2. Authoritative CLI Entrypoint
- The authoritative CLI entrypoint is only the one explicitly documented as supported elsewhere in this repository.
- If no authoritative CLI entrypoint is explicitly documented, the entrypoint is unspecified and not guaranteed by this contract.
- No alternative entrypoints are supported as part of this contract.
- Invocation context (module invocation, script invocation, installed command) is unspecified unless explicitly documented.

## 3. Command Structure

### 3.1 Base Command
- Canonical invocation syntax is only what is explicitly documented as supported elsewhere in this repository.
- If exact command syntax is not explicitly documented, it is unspecified and not guaranteed by this contract.
- Deterministic invocation requirement:
  - Callers MUST use only the documented supported invocation form and documented arguments.

### 3.2 Subcommands (if applicable)
- Subcommand behavior is only guaranteed if explicitly documented.
- If subcommands are not explicitly documented as supported, subcommand usage is unsupported.

### 3.3 Arguments
- Positional arguments:
  - Only explicitly documented positional arguments are supported.
  - Undocumented positional arguments are unsupported.
- Named arguments:
  - Only explicitly documented named arguments are supported.
  - Undocumented named arguments are unsupported.
- Mutually exclusive flags:
  - Mutually exclusive behavior is guaranteed only when explicitly documented.
  - If not explicitly documented, no mutual-exclusion guarantees are provided.
- Unsupported patterns:
  - Undocumented flags or arguments.
  - Invocation shapes not explicitly documented as supported.
  - Ambiguous argument forms that rely on undocumented parsing behavior.

## 4. Argument Validation Rules
- Required vs optional:
  - Required/optional status is guaranteed only for arguments explicitly documented as such.
  - If requirement level is not explicitly documented, it is unspecified and not guaranteed.
- Type validation:
  - Argument type expectations are guaranteed only when explicitly documented.
- Invalid input handling:
  - Invalid syntax or unsupported arguments MUST be treated as validation/usage errors.
  - Inputs that pass parsing but fail during execution MUST be treated as runtime failures.
- Parsing determinism:
  - Parsing MUST be deterministic and must not rely on ambiguous interpretation.

## 5. Exit Code Contract
- `0` → success.
- Non-zero → failure.
- Failure categories:
  - Validation / usage error.
  - Runtime failure (unexpected execution error).
- Configuration-error category is not separately guaranteed unless explicitly documented.
- Rule: no undocumented success codes (`0` is the only success code).
- stdout/stderr expectations:
  - stdout/stderr formatting is not guaranteed unless explicitly documented as machine-stable.

## 6. Determinism Requirements
- CLI behavior covered by this contract MUST be deterministic for the same documented inputs.
- No implicit randomness is guaranteed.
- Environment-dependent behavior is not guaranteed unless explicitly documented.
- Configuration resolution order is not specified unless explicitly documented.
- Time, locale, and filesystem-ordering behavior are not guaranteed unless explicitly documented.

## 7. Unsupported CLI Usage
- Treating direct internal module execution as a supported interface unless explicitly documented as supported.
- Any undocumented flags, arguments, or invocation shapes.
- Interactive prompts; interactive behavior is unsupported unless explicitly documented.
- Assuming side effects or internal implementation behavior as stable contract.

## 8. Stability Guarantees
- Stable:
  - The documented authoritative entrypoint concept.
  - Documented arguments and documented invocation forms only.
  - Documented exit-code success/failure category behavior.
- May change without contract guarantee:
  - Undocumented behavior.
  - Internal implementation details.
  - Failure-message wording/format.
- Deprecation policy:
  - No formal deprecation window is guaranteed for undocumented behavior.
