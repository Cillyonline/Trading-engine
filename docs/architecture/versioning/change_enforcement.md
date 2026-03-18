# Version Bump Enforcement Rules

## 1. Purpose
This document defines binding rules that map change classification to required version increments.
These rules are normative and must be applied consistently for every release.
This document is aligned with `model.md` and `scope.md`.

## 2. Change Classification → Version Increment Mapping

### 2.1 MAJOR (Mandatory Increment)
A MAJOR increment is required when any of the following applies:
- Breaking API changes.
- Breaking contract changes.
- Removal of public interfaces.
- Backward-incompatible behavior changes.
- Any externally observable incompatibility.

A MAJOR increment is mandatory and cannot be downgraded.

### 2.2 MINOR (Mandatory Increment)
A MINOR increment is required when all MAJOR conditions are false and any of the following applies:
- Backward-compatible feature additions.
- New optional contract fields.
- Backward-compatible interface extensions.
- New externally visible capabilities without breaking changes.

A MINOR increment is mandatory if no MAJOR condition applies.

### 2.3 PATCH (Mandatory Increment)
A PATCH increment is required when neither MAJOR nor MINOR conditions apply and the release contains one or more of the following:
- Bug fixes.
- Documentation-only changes.
- Internal refactoring without externally observable impact.
- Test-only changes.

A PATCH increment is mandatory if neither MAJOR nor MINOR conditions apply.

## 3. Precedence Rules
If multiple change types exist within a release, the highest required increment wins: MAJOR > MINOR > PATCH.
Version increments are determined per release, not per commit.

## 4. Breaking Change Documentation Requirement
Any MAJOR increment requires explicit documentation.
The breaking change must be described in release documentation.
The description must include:
- What changed.
- Why it changed.
- Migration impact (if applicable).

A MAJOR bump without documented breaking change description violates governance.

## 5. Non-Goals
This document defines no automation or CI enforcement.
This document defines no runtime checks.
This document defines no git hook requirements.
This document defines no implementation details.
