# Compatibility Review Gate

## 1. Purpose
This gate ensures backward compatibility is reviewed and explicitly confirmed before every release.

This review is **mandatory** and must be completed before tagging any release, as defined in `docs/versioning/release_boundary.md`.

## 2. Mandatory Compatibility Checklist (Manual)

Complete this checklist manually for each release candidate. Every item requires an explicit **YES/NO** answer. Any **NO** blocks release tagging until resolved or versioning is corrected.

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

## 3. Review Outcome and Release Gate Decision
- The compatibility review gate is considered **passed** only when all checklist items are marked **YES**.
- Any **NO** result means the release must not be tagged until:
  - compatibility is restored, or
  - the release version is updated to match the breaking-change policy.

## 4. Required Confirmation Record
For every release candidate, capture and retain a manual confirmation record containing:
- Release candidate identifier/version.
- Reviewer name.
- Review date.
- Final gate outcome: **PASS** or **BLOCKED**.
- Notes for any **NO** item and the remediation decision.
