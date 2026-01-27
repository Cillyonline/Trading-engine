# Test-Gated Execution Mode

## Title and Purpose

Test-Gated Execution Mode is an explicit, mandatory execution mode for applicable work in this repository.

## When This Mode Is Mandatory

This mode is mandatory for:
- Contract-facing work.
- Schema or public-output related work.
- Consumer-facing integrations.

## Core Invariants (Non-Negotiable)

The following invariants apply:
- CI is green.
- No guard violations.
- PRs are issue-linked using `Closes #<IssueID>`.

## Stop Conditions

Stop conditions are governed by the Stop Conditions & Merge Authority Matrix. This mode follows the established stop condition categories and enforcement defined in that document.

## Merge Authority

CI is a hard gate. Codex A Review Gate is the final authority. Merge authority is defined by the Stop Conditions & Merge Authority Matrix.

## Operational Flow (High-Level)

1. Issue created.
2. Work executed under Test-Gated Execution Mode.
3. CI run.
4. Codex A Review Gate.
5. Merge or Stop.

## References

- [Test-Gated PR Review Checklist](pr-review-checklist-test-gated.md)
- [Stop Conditions & Merge Authority Matrix](stop-conditions-and-merge-authority.md)
- [Runbook](../RUNBOOK.md)
