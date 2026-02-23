# Batch Execution Workflow – Cilly Trading Engine

> Governance Note  
> Snapshot scheduling status and ownership boundary  
> are explicitly documented in:  
> docs/runtime/snapshot_runtime.md

## 1. Purpose
- This document defines a deterministic, bounded batch execution workflow contract for automation usage in this repository.
- Scope is limited to invocation pattern, input/output contract boundaries, and logging expectations for batch usage.
- Non-goals:
  - No scheduler implementation.
  - No runtime behavior changes.
  - No external integration definition.

## 2. Supported Batch Invocation Pattern
- Supported batch execution is the non-interactive repetition of already documented CLI/API usage patterns.
- The authoritative command-line contract for batch invocation is defined by `docs/interfaces/cli_contract.md`.
- Batch automation MUST use only invocation forms and arguments explicitly documented as supported.
- Interactive execution is unsupported for automation unless explicitly documented elsewhere.

## 3. Input Contract

### 3.1 Invocation Input
- Only explicitly documented CLI/API parameters are supported.
- Undocumented flags, arguments, request fields, or parameters are unsupported.
- Any default values not explicitly documented are not guaranteed.

### 3.2 Data Inputs
- Data inputs are only those artifacts and payloads explicitly documented by existing repository contracts.
- This document does not define new file names, file formats, payload schemas, or artifact locations.
- Determinism requirement: same documented invocation inputs plus same documented data inputs MUST produce deterministic behavior within documented bounds.
- Validation expectations are only guaranteed where explicitly documented; otherwise validation behavior is unspecified and not guaranteed.

### 3.3 Configuration Resolution
- Configuration resolution order is guaranteed only if explicitly documented in repository contracts.
- If not explicitly documented, configuration precedence is unspecified and not guaranteed.

## 4. Output Contract

### 4.1 Primary Output
- A successful batch result is completion of the documented operation without validation/runtime failure.
- Primary output artifacts are guaranteed only when explicitly documented in existing contracts.
- If artifact shape, naming, or persistence behavior is not explicitly documented, it is not guaranteed.

### 4.2 Exit Code Contract
- `0` means success.
- Non-zero means failure.
- Failure categorization for batch execution follows the CLI contract boundary:
  - Validation/usage failure for invalid invocation input.
  - Runtime failure for execution-time errors.

### 4.3 Idempotency Expectations
- Idempotency is not guaranteed unless explicitly documented for the specific operation.

## 5. Logging Behavior

### 5.1 Human-Readable Logs
- Logs are intended for operators and troubleshooting.
- Human-readable log content, wording, and formatting are not machine-stable unless explicitly documented.

### 5.2 Machine-Stable Logging (if any)
- Machine-stable logging is guaranteed only when explicitly documented as a contract.
- If no explicit machine-stable logging contract exists, machine parsing of logs is unsupported and not guaranteed.

## 6. Determinism Requirements
- Within documented contract scope, execution MUST avoid implicit randomness.
- Batch determinism MUST NOT assume network dependency unless such dependency is explicitly documented.
- Environment-dependent behavior (for example host settings, locale, filesystem ordering, clock, or process environment) is not guaranteed unless explicitly documented.

## 7. Unsupported Batch Usage
- Interactive execution flows.
- Reliance on undocumented behavior, defaults, flags, parameters, or internal implementation details.
- Parsing human-readable logs as a stable interface unless explicitly documented.
- Treating external side effects as guaranteed contract behavior unless explicitly documented.

## 8. Stability Guarantees
- Stable contract surface:
  - Only behavior explicitly documented in repository interface contracts.
  - Exit status success/failure boundary defined in this document and `docs/interfaces/cli_contract.md`.
- May change without notice:
  - Undocumented invocation forms, defaults, log formats, and implementation details.
- Deprecation policy:
  - No additional deprecation policy is defined by this document.
  - Undocumented behavior has no guaranteed deprecation window.
