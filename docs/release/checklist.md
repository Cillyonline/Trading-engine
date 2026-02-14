# Release Checklist – Operational Governance

## 1. Purpose
This checklist governs manual release preparation and manual tagging under Phase 19 governance to ensure that each release is approved, versioned, and published using the defined repository controls.

## 2. Pre-Release Preconditions
- [ ] All Issues included in the release are **APPROVED**.
- [ ] Required status check **"test"** is green.
- [ ] No open blocker issues exist.
- [ ] Release scope is frozen.

## 3. Version Determination
Reference documents:
- [ ] `../versioning/change_enforcement.md`
- [ ] `../versioning/model.md`

Execution checklist:
- [ ] Classify all included changes as **MAJOR**, **MINOR**, or **PATCH**.
- [ ] Apply the highest precedence rule across all included changes.
- [ ] Confirm the selected version increment aligns with enforcement rules.

## 4. Compatibility Review Gate
Reference document:
- [ ] `../versioning/compatibility_gate.md`

Gate checklist:
- [ ] Compatibility gate checklist is completed.
- [ ] All compatibility gate items are marked **YES**.
- [ ] If the release is **MAJOR**, breaking changes are documented.

## 5. Release Boundary Confirmation
Reference document:
- [ ] `../versioning/release_boundary.md`

Boundary checklist:
- [ ] Confirm there is a single release commit.
- [ ] Confirm the version tag format is `vX.Y.Z`.
- [ ] Confirm there are no post-tag modifications.

## 6. Manual Approval Requirement
- [ ] Codex A approval is required before tagging.
- [ ] Approval is recorded in a PR review or in a release note.
- [ ] No tag is created without documented approval.

## 7. Tagging Step (Manual)
- [ ] Create tag `vX.Y.Z` on the release commit.
- [ ] Push tag `vX.Y.Z` to the repository.

## 8. Post-Release Verification
- [ ] Tag is visible in the repository.
- [ ] Version command reflects the released version.
- [ ] Smoke run passes.
