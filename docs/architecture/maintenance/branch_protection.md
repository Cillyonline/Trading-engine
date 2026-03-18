# Branch Protection and Required CI Checks (Maintenance Mode)

## 1) Purpose
This document records the currently observed branch protection and merge-gating configuration for maintenance mode, while separating:
- settings that are directly verifiable via read-only API/ruleset data, and
- settings that require explicit manual confirmation in the GitHub Settings UI.

Evidence sources used for this snapshot:
- GitHub REST API (read-only):
  - `GET /repos/Cillyonline/Trading-engine`
  - `GET /repos/Cillyonline/Trading-engine/rules/branches/main`
  - `GET /repos/Cillyonline/Trading-engine/rulesets`
  - `GET /repos/Cillyonline/Trading-engine/rulesets/11431120`
- Repository workflow inventory: `.github/workflows/ci.yml`

## 2) Protected branch
- Default branch: `main`
- Active branch ruleset name: `main-required-checks`
- Ruleset target include condition: `~DEFAULT_BRANCH` (applies to `main`)
- Ruleset enforcement: `active`

## 3) Required status checks
Required status check contexts (exact values from active ruleset):
- `smoke-run-contract`

Related required-check setting (exact value from ruleset parameters):
- `strict_required_status_checks_policy: false`
  - Interpretation: branch does **not** need to be up to date with base before merge.

## 4) Merge policy (verified vs. UI verification needed)
### A) Verified via active ruleset/API
- Branch scope pattern: `~DEFAULT_BRANCH` (effective branch: `main`)
- Require status checks: **Enabled**
  - Required contexts: `smoke-run-contract`
  - Strict policy (`up to date before merging`): **Disabled** (`false`)
- Force pushes: **Blocked** (ruleset contains `non_fast_forward`)
- Branch deletions: **Blocked** (ruleset contains `deletion`)

### B) Requires manual confirmation in GitHub Settings UI
The following values are not asserted from the current public ruleset payload alone and must be confirmed manually:
- Pull request requirement before merging
- Required reviews / approvals count
- Code owner review requirement
- Dismiss stale approvals
- Require conversation resolution
- Include administrators enforcement
- Push restrictions / actor allowlists (if configured in classic branch protection)

Exact UI path to verify:
1. Open repository: `https://github.com/Cillyonline/Trading-engine`.
2. Go to `Settings` → `Branches`.
3. In **Branch protection rules**, open the rule that matches `main`.
4. Confirm and record:
   - “Require a pull request before merging” (enabled/disabled)
   - Required approving review count (exact number)
   - “Require review from Code Owners” (enabled/disabled)
   - “Dismiss stale pull request approvals when new commits are pushed” (enabled/disabled)
   - “Require conversation resolution before merging” (enabled/disabled)
   - “Require status checks to pass before merging” and exact check names
   - “Require branches to be up to date before merging” (enabled/disabled)
   - “Include administrators” (enabled/disabled)
   - Push restrictions (who can push), if present

## 5) Expected CI behavior
Workflow inventory in repository:
- `ci.yml`

Workflow/job mapping for required checks (from `.github/workflows/ci.yml`):
- Workflow name: `Smoke-Run Contract`
- Job id: `smoke-run-contract`
- Required status check context: `smoke-run-contract`

PR-time behavior statement:
- If the workflow file defines `on: pull_request`, then the required status check context `smoke-run-contract` will run during PR evaluation.
- Merge to `main` is blocked until required check context `smoke-run-contract` reports success.

## 6) Enhanced manual verification checklist
1. Open `Settings` → `Branches` in the repository.
2. Open the branch protection rule for `main`.
3. Verify PR and review gating values exactly:
   - PR requirement enabled/disabled
   - Required approvals count
   - Code owner review requirement
   - Dismiss stale reviews setting
   - Conversation resolution requirement
4. Verify required checks exactly:
   - “Require status checks to pass before merging” enabled
   - Required check list contains exactly `smoke-run-contract` (spelling and hyphenation must match)
   - “Require branches to be up to date before merging” setting value
5. Verify governance enforcement and access controls:
   - “Include administrators” enabled/disabled
   - Force pushes allowed/blocked
   - Deletions allowed/blocked
   - Push restrictions (if present)
6. Cross-check workflow file `.github/workflows/ci.yml` still contains:
   - `on: pull_request`
   - job id `smoke-run-contract`
7. Record verification timestamp and reviewer.

---
Last verified snapshot (API + repository file inspection): 2026-02-12 (UTC).
