# Compatibility Review Gate

## 1. Purpose
This gate SHALL ensure backward compatibility is reviewed and explicitly confirmed before every release.

This review is **mandatory** and MUST be completed before tagging any release, as defined in `docs/versioning/release_boundary.md`.

## 2. Mandatory Compatibility Checklist (Manual)

This checklist MUST be completed manually for each release candidate. Every item requires an explicit **YES/NO** answer. Any **NO** SHALL block release tagging until resolved or versioning is corrected.

### 2.1 Contract Compatibility
- [ ] **YES / NO** — No breaking schema changes were introduced without a **MAJOR** version bump.
- [ ] **YES / NO** — No public fields were removed without a **MAJOR** version bump.
- [ ] **YES / NO** — No public field semantics were changed without a **MAJOR** version bump.

### 2.2 API Compatibility
- [ ] **YES / NO** — No public functions were removed.
- [ ] **YES / NO** — No public function signatures were changed.
- [ ] **YES / NO** — No externally observable behavior changed without the correct version increment.

### 2.3 CLI Compatibility
- [ ] **YES / NO** — No CLI flags were removed.
- [ ] **YES / NO** — No CLI output format changed without the correct version increment.

### 2.4 Artifact Compatibility
- [ ] **YES / NO** — Artifact structure is unchanged unless intentionally and properly versioned.
- [ ] **YES / NO** — No incompatible artifact format changes were introduced without a **MAJOR** version bump.

## 3. Contract Change Review Step
Any change touching external contracts MUST receive explicit review before release.

The reviewer MUST classify each contract-affecting change as **MAJOR / MINOR / PATCH**.

The classification MUST align with `docs/versioning/change_enforcement.md`.

If the classification is **MAJOR** (breaking):
- Breaking change documentation is REQUIRED before release tagging.
- Documentation MUST include:
  - What changed
  - Why it changed
  - Migration impact (if applicable)

## 4. Governance Approval Requirement
Release tagging MUST NOT proceed without a documented compatibility review record.

Codex A approval is mandatory before release tagging.

Approval MUST be recorded (for example, PR review comment or release checklist entry) for the release candidate/version.

## 5. Review Outcome and Release Gate Decision
- The compatibility review gate is considered **passed** only when all checklist items are marked **YES**.
- Any **NO** result means the release must not be tagged until:
  - compatibility is restored, or
  - the release version is updated to match the breaking-change policy.

## 6. Required Confirmation Record
For every release candidate, capture and retain a manual confirmation record containing:
- Release candidate identifier/version.
- Reviewer name.
- Review date.
- Final gate outcome: **PASS** or **BLOCKED**.
- Notes for any **NO** item and the remediation decision.

## 7. Non-Goals
- No automated diff tooling defined.
- No CI-based enforcement.
- No runtime compatibility checks.
