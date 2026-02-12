# Branch Protection and Required CI Checks (Maintenance Mode)

## 1) Purpose (maintenance mode governance)
This document records the **current, observed governance controls** for the default branch so maintainers can verify merge-gating behavior during maintenance mode.

Source of truth used for this snapshot:
- GitHub REST API (public, read-only):
  - `GET /repos/Cillyonline/Trading-engine`
  - `GET /repos/Cillyonline/Trading-engine/rules/branches/main`
  - `GET /repos/Cillyonline/Trading-engine/rulesets`
  - `GET /repos/Cillyonline/Trading-engine/rulesets/11431120`
- Workflow inventory from this repository: `.github/workflows/`

> Note: Classic branch-protection endpoint (`/branches/main/protection`) requires authenticated admin access and was not used as the primary source. The active **repository ruleset** for the default branch is used here.

## 2) Protected branch: `main` (exact)
- Default branch: `main`
- Ruleset target condition: `~DEFAULT_BRANCH` (therefore applies to `main`)
- Active ruleset name: `main-required-checks`
- Ruleset enforcement: `active`

## 3) Required status checks (exact list of names)
Required status check contexts from active ruleset:
- `smoke-run-contract`

Additional setting for required checks:
- Require branches to be up to date before merging: **No** (`strict_required_status_checks_policy: false`)

## 4) Merge policy
Observed policy from the active branch ruleset:

- Branch name pattern / scope: **Default branch only** (`~DEFAULT_BRANCH` → `main`)
- PRs required before merging: **No explicit rule configured** (no `pull_request` rule present)
- Required approving review count: **Not configured**
- Code owner reviews required: **Not configured**
- Dismiss stale reviews: **Not configured**
- Require conversation resolution: **Not configured**
- Require linear history: **No** (no `required_linear_history` rule present)
- Require signed commits: **No** (no `required_signatures` rule present)
- Require status checks: **Yes** (`required_status_checks` rule present)
- Include administrators: **Not explicitly discoverable from public ruleset payload**
- Allow force pushes: **No** (`non_fast_forward` rule present = block force pushes)
- Allow deletions: **No** (`deletion` rule present = restrict deletions)
- Push restrictions (who can push): **No explicit restrict-updates / push-allowlist rule present**

## 5) Expected CI behavior (what must pass before merge)
Workflow files currently present:
- `ci.yml`

Best-effort mapping of required status checks to workflows/jobs:
- Required check context `smoke-run-contract` maps to workflow file `ci.yml`, job id `smoke-run-contract`.
- Workflow name is `Smoke-Run Contract`; required merge gate uses the check context listed above.

Expected PR-time behavior:
- On pull requests, the CI workflow runs.
- Merge to `main` is blocked until required check context `smoke-run-contract` reports success.
- Branch up-to-date with base is **not** required by ruleset (`strict_required_status_checks_policy: false`).

## 6) Verification checklist (manual steps to confirm settings)
1. Open repository settings: `Settings` → `Rules` (or `Branches` if using classic view).
2. Open active ruleset `main-required-checks` targeting `~DEFAULT_BRANCH`.
3. Confirm these active rules are present:
   - `Require status checks to pass` with `smoke-run-contract`
   - `Block force pushes`
   - `Restrict deletions`
4. Confirm no additional merge-gating rules are enabled (PR review/conversation/signature/linear-history), unless intentionally changed.
5. Cross-check workflow inventory in `.github/workflows/` and ensure required check context still maps to an existing CI job.

---
Last verified snapshot: 2026-02-12 (UTC), via read-only GitHub API and repository workflow inspection.
