# Versioning Model

## 1. Chosen Model
This project adopts Semantic Versioning 2.0.0 (SemVer) as its official versioning model.

SemVer is chosen to provide clear stability expectations and explicit contract signaling for all consumers. The version number communicates compatibility impact in a consistent, auditable, and project-wide manner.

## 2. Version Format
The version format is strictly:

MAJOR.MINOR.PATCH

No additional numeric segments are part of the core version format.

## 3. MAJOR
A MAJOR version increment is required when any backward-incompatible change is introduced, including:

- Breaking API changes.
- Breaking contract changes.
- Removal of public interfaces.
- Backward-incompatible behavior changes.

## 4. MINOR
A MINOR version increment is required for backward-compatible evolution, including:

- Backward-compatible feature additions.
- New optional contract fields.
- Non-breaking interface extensions.

## 5. PATCH
A PATCH version increment is required for backward-compatible corrections and non-contract-impacting updates, including:

- Bug fixes.
- Documentation-only changes.
- Internal refactoring without contract impact.

## 6. Scope of Applicability
The scope of this model is project-wide and authoritative:

- The project has one single authoritative version.
- All contracts inherit the project version.
- Independent contract-level version numbers are not used.

## 7. Non-Goals
This phase explicitly does not introduce:

- Release automation.
- Runtime version enforcement.
- A dedicated version file.
