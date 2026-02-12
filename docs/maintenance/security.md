## 1) Purpose

During maintenance mode, security patch handling must remain deterministic so that every vulnerability report is handled with the same repeatable process. A deterministic process prevents ad hoc decisions, reduces the chance of missed remediation steps, and preserves auditability for compliance and incident review. All participants must follow this runbook exactly whenever a security advisory is received.

## 2) Security Triage Procedure

Use the following procedure for every incoming security report.

### 2.1 Collect vulnerability source data
1. Record the source type in the tracking issue:
   - Dependency advisory (package registry advisory)
   - CVE notice
   - GHSA notice
2. Record all identifiers exactly as published (for example: `CVE-YYYY-NNNN`, `GHSA-xxxx-xxxx-xxxx`).
3. Record affected package/component name and affected version range.
4. Record currently used version in this repository.

### 2.2 Classify severity
1. Use the source advisory severity when available.
2. Normalize the classification to one of the following values only:
   - low
   - medium
   - high
   - critical
3. If multiple sources disagree, select the highest reported severity and document the discrepancy.

### 2.3 Apply decision matrix
Apply this matrix exactly:

| Condition | Decision | Required action |
|---|---|---|
| Severity is `critical` or `high`, and repository version is affected | Patch immediately (emergency) | Start patch workflow now; do not wait for monthly review |
| Severity is `medium` or `low`, and repository version is affected | Defer to monthly dependency review | Open tracking issue, schedule for next monthly dependency cycle |
| Repository version is not affected, advisory is withdrawn, or component is not used | Reject (not applicable) | Close issue with explicit rationale and evidence |

No other decision outcomes are allowed.

## 3) Patch Workflow

Execute the following steps in order. Do not skip or reorder.

1. Create a dedicated GitHub Issue for the security patch.
2. In the Issue description, explicitly reference the advisory identifier(s) (`CVE` and/or `GHSA`).
3. Create a dedicated branch for this patch only.
4. Apply the minimal required patch only (for example, smallest dependency bump that remediates the advisory). No refactor is allowed.
5. Open a pull request from the dedicated branch and include `Closes #<IssueID>` in the PR body.
6. Do not batch unrelated fixes, refactors, or feature work with the patch.

## 4) Verification Requirements

Before merge, all checks below must pass and be reproducible from a clean checkout of the patch branch.

1. Project compiles successfully, if the project has a compile/build step.
2. `pytest` passes fully.
3. No new test warnings are introduced compared with the current maintenance baseline.
4. CI status is fully green for the pull request.
5. Confirm no public API surface changes are present in the patch.

Merge is blocked until every requirement above is satisfied.

## 5) Rollback Guidance

If a failure is detected after merge, use this rollback process exactly:

1. Open the merged patch PR in GitHub.
2. Use GitHub's **Revert** action to create a dedicated revert commit.
3. Merge the revert PR.
4. Do not amend commit history, do not force-push, and do not rewrite history.
5. Open a follow-up GitHub Issue for root cause analysis.
6. In the follow-up Issue, link:
   - Original security patch Issue
   - Original security patch PR
   - Revert PR
7. Re-run triage using this runbook before attempting a replacement patch.

## 6) Governance Constraints

The following constraints are mandatory during maintenance mode:

- Each security patch requires its own GitHub Issue and its own PR.
- Major dependency upgrades require a separate explicit approval Issue before implementation.
- Architectural expansion and runtime scope expansion are not allowed under this runbook.
- Feature additions are not allowed under the pretext of security patching.
