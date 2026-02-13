# Usage Patterns – Cilly Trading Engine

## 1. Purpose
- This document defines the supported usage patterns for this repository at a high level: CLI, API, and batch/automation usage.
- This document also defines explicit unsupported usage patterns and bounded stability guarantees.
- Non-goals:
  - Defining new features, new entrypoints, or new runtime behavior.
  - Expanding public API surface beyond what is already documented.
  - Specifying architecture, implementation details, or roadmap commitments.

## 2. Supported Usage Patterns

### 2.1 CLI Usage (Supported)
- Intended consumers:
  - Engineers and operators running repository-provided command-line entrypoints.
- Supported invocation patterns (high-level, non-expansive):
  - Running documented CLI commands from repository documentation.
  - Using documented command arguments and defaults only.
- Stability guarantee level:
  - See Section 4.1.
- Automation expectations (non-interactive rules):
  - CLI usage for automation is supported only in non-interactive mode.
  - Automation must rely on documented arguments and exit status behavior only.

### 2.2 API Usage (Supported)
- Definition of “public API” in this project context:
  - The HTTP API behavior documented in `docs/api/usage_contract.md`.
  - The supported Python import boundary documented in `docs/api/public_api_boundary.md` (`from api import app`).
- Backwards-compatibility contract (bounded and realistic):
  - Compatibility is only expected for documented API contracts.
  - Undocumented request/response shapes or internal symbols are not part of the compatibility contract.
- Versioning assumptions:
  - No separate semantic versioning policy is defined in this document.
  - Stability is governed by documented contracts and repository change control.
- Behavioral guarantees:
  - Guaranteed and non-guaranteed API behavior is limited to what is explicitly documented in `docs/api/api_guarantees.md` and `docs/api/usage_contract.md`.
  - Any behavior not explicitly documented there is not guaranteed.

### 2.3 Batch / Automation Usage (Supported)
- Supported batch execution modes:
  - Repeated execution of documented CLI/API flows by external schedulers or CI jobs.
  - Non-interactive execution that uses only documented entrypoints, arguments, and payloads.
- Idempotency expectations:
  - Idempotency is not guaranteed unless explicitly documented for a specific endpoint or operation.
- Scheduling and retry assumptions:
  - Scheduling strategy is owned by the caller/operator.
  - Retry behavior must be designed by callers based on documented success/error behavior; global retry guarantees are not provided by this document.

## 3. Unsupported Usage Patterns
- Importing or relying on internal modules or undocumented behavior.
- Runtime patching, monkey-patching, or reflection into internals as a contract.
- Depending on log output formats for automation where no explicit machine-stable log contract is documented.
- Using undocumented flags, fields, aliases, or defaults as stable contracts.
- Any undocumented entrypoints (CLI, API, script, module, or environment toggle).
- Treating internal implementation details as public compatibility commitments.

## 4. Stability Guarantees

### 4.1 CLI Stability
- Considered stable:
  - Documented CLI usage patterns and documented command interfaces.
- May change without notice:
  - Undocumented flags, undocumented command behavior, internal script wiring, and internal output wording/format.
- Deprecation expectations:
  - No universal deprecation window is guaranteed by this document.

### 4.2 API Stability
- Considered stable:
  - Documented API contracts in `docs/api/usage_contract.md`.
  - Public API boundary in `docs/api/public_api_boundary.md`.
- Compatibility expectations:
  - Backwards compatibility applies only to documented API contracts.
- Not guaranteed:
  - Behavior outside documented contracts.
  - Internal module structure, undocumented fields, or undocumented side effects.

### 4.3 Configuration Stability
- Stable vs experimental configuration:
  - Configuration behavior explicitly documented as supported is treated as stable for that documented scope.
  - Experimental, internal, or undocumented configuration is not stable.
- Compatibility expectations across releases:
  - Only documented configuration keys and documented semantics are candidates for compatibility.
  - Undocumented configuration compatibility is not guaranteed.

## 5. Automation Rules
- Non-interactive execution expectations:
  - Automation must run without prompts and without manual intervention.
  - Automation must use only documented entrypoints and documented parameters.
- Exit codes as automation contract:
  - Exit-code expectations are only guaranteed where explicitly documented.
  - If not explicitly documented, precise exit-code mapping is not guaranteed.
- Logging guarantees:
  - Logs are primarily human-oriented unless a machine-stable logging contract is explicitly documented.
  - Automation must not parse logs as a stable interface unless explicitly documented.
- CI expectations:
  - Documentation-only changes must not require CI behavior changes.
  - This document defines usage boundaries only and does not alter CI/runtime behavior.

## 6. Explicit Boundaries
- Experimental features policy:
  - Experimental or undocumented capabilities are out of scope for stability guarantees.
  - Use of experimental behavior is at caller risk and is not a supported contract.
- Changes requiring a new Issue:
  - Introducing a new usage pattern.
  - Adding new stability guarantees.
  - Promoting undocumented behavior to supported contract.
  - Expanding automation guarantees beyond documented scope.
