## 1) Purpose
Dependency control is required in maintenance mode to preserve runtime stability, avoid unplanned regressions, and keep security posture current without expanding product scope. During maintenance mode, dependency changes are limited to risk-reducing maintenance actions that are deterministic, auditable, and governance-approved.

## 2) Update Cadence
- **Regular review interval:** Dependency review is performed on the first business day of each calendar month.
- **Scope of regular review:** Evaluate available PATCH and eligible MINOR updates, plus known vulnerability advisories for direct and transitive dependencies.
- **Emergency security patch process:** Outside the monthly cycle, an ad-hoc update is allowed only for security fixes with a published advisory (for example CVE/GHSA) that affects the repository.
- **Deterministic timing rule:** No dependency update work starts outside the monthly review window unless it is classified as an emergency security patch.

## 3) Allowed Update Types
- **PATCH updates:**
  - Allowed during maintenance mode.
  - Must not change public API surface.
  - Must pass all required verification checks before merge.
- **MINOR updates:**
  - Allowed only when backward compatibility is documented by upstream release notes.
  - Must include explicit verification evidence in the PR.
  - Must receive PR review approval before merge.
- **MAJOR updates:**
  - Not allowed in maintenance mode.
  - Require a new, explicit GitHub Issue approval before any implementation work.
  - Must not be performed under tracking issues.

## 4) Verification Requirements
Before merge, every dependency update PR must satisfy all of the following deterministic checks:
- Project compiles successfully (if compilation applies to the changed dependency set).
- `pytest` passes fully with no failing or skipped-required tests.
- Test output introduces no new warnings compared to the current main baseline.
- CI status is green on `main` for the update commit prior to merge.

## 5) Governance Rules
- Every dependency update must have its own GitHub Issue.
- Every dependency update must be implemented in a dedicated PR.
- The PR body must include `Closes #<IssueID>` matching the update-specific issue.
- Batch upgrades across unrelated packages are not allowed.
- Silent dependency drift is not allowed; all dependency version changes must be committed and reviewed through the issue/PR flow.

## 6) Explicitly Prohibited Actions
- Runtime refactors.
- Behavior changes.
- API changes.
- Dependency major upgrades without prior explicit approval issue.
