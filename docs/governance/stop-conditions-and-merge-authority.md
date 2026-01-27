# Title and Scope

This document applies to Test-Gated Execution Mode.
This document is the authoritative matrix for stop conditions and merge authority.

# Hard Stop Conditions (Work Must Halt)

- CI status is red. STOP WORK.
- Guard/MVP violation is detected. STOP WORK.
- Issue linkage is missing or invalid. STOP WORK.

# Merge Blockers

- CI status is red. NON-OVERRIDABLE.
- PR body lacks `Closes #<IssueID>`. NON-OVERRIDABLE.
- Codex A Review Gate is failed. NON-OVERRIDABLE.

# Merge Authority Matrix

| Decision | Authority | Deterministic outcome |
| --- | --- | --- |
| CI gate result | CI | CI green = eligible for Codex A review; CI red = merge blocked. |
| Review gate result | Codex A Review Gate | Pass = merge authorized; Fail = merge blocked. |

Codex A has final merge authority after CI is green.

# Example Scenarios (MANDATORY)

1) Scenario: CI red.
   Outcome: STOP.

2) Scenario: Guard violation detected.
   Outcome: STOP.

3) Scenario: PR body missing `Closes #<IssueID>`.
   Outcome: BLOCK MERGE.

# References
- [Test-Gated PR Review Checklist](pr-review-checklist-test-gated.md)
- [Runbook](../RUNBOOK.md)
