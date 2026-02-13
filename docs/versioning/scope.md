# Version Scope

## 1. Authoritative Version
- This project has one single authoritative version, as defined in `docs/versioning/model.md`.
- This authoritative version governs all externally observable behavior of the project.

## 2. Versioned Surfaces (Explicit List)

### 2.1 CLI
- The CLI shares the same project version.
- The CLI is not independently versioned.

### 2.2 API
- The API shares the same project version.
- No independent API version numbering exists at this phase.

### 2.3 Artifacts
- Build artifacts, including distributions, packages, and generated artifacts, inherit the project version.
- No artifact-level independent versioning is used.

### 2.4 Contracts
- Contracts inherit the project version, aligned with `docs/versioning/model.md`.
- No independent contract-level version numbers are used.

## 3. Documentation Versioning
- Documentation is version-aligned with the project version.
- No independent documentation version stream is used.

## 4. Non-Versioned Surfaces (Explicit Exclusions)
- Internal modules are not independently versioned.
- Experimental code paths are not independently versioned.
- Test utilities are not independently versioned.
- CI configuration is not independently versioned.
- Development-only scripts are not independently versioned.
- Internal refactoring does not trigger version increments unless externally observable behavior changes.

## 5. Non-Goals
- No implementation of version reporting.
- No CLI `--version` behavior is defined here.
- No runtime version checks.
- No release automation.
