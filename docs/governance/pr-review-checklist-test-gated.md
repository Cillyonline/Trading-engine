# PR Review Checklist – Test-Gated Execution Mode

> **Rule:** Block merge if **any** item is **NO**.

## Mandatory PR Body
- [ ] PR body includes `Closes #<IssueID>` (exact format)
- [ ] Exactly **one** Issue is referenced and matches the work scope

## Test-Gated Requirements
- [ ] CI status is **green** (all required checks passed)
- [ ] All tests required by the Issue Acceptance Criteria are present and passing

## Governance & Scope
- [ ] Changes are **strictly within** the Active Issue scope
- [ ] No files outside **docs/** are modified
- [ ] No engine/runtime, tests, CI, schemas, or contracts changed

## Codex & Runbook Compliance
- [ ] PR body explicitly states: MODE: EXECUTION
- [ ] Review Gate inputs provided (file list + full contents where applicable)
- [ ] MVP guardrails respected (no out-of-scope features)

## Decision
- [ ] All items above are **YES**

## References
- [Runbook](../RUNBOOK.md)
