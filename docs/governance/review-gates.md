# Review Gates

## Purpose

This document defines merge gates for AI-assisted work. A pull request is not approved because code was generated or tests passed. It is approved only when the change is scoped, evidenced, and safe for its lane.

## Pull request states

| State | Meaning |
| --- | --- |
| Draft PR | Work and review container; not merge-ready |
| Ready for review | Candidate has passed local review expectations and is ready for final approval |
| Merged | Change was approved and integrated |

Draft pull requests are mandatory for standard and critical lane work.

## Approval gate

A pull request may be approved only when all relevant conditions are true:

- The linked issue is clear and matches the implementation.
- Acceptance criteria are satisfied or explicitly deferred with owner approval.
- The diff stays within scope.
- Required tests passed or a test limitation is documented and acceptable.
- The review package is complete.
- No secrets, credentials, or sensitive runtime values are introduced.
- No unsupported readiness, profitability, live-trading, broker-readiness, trader-validation, or production-readiness claim is introduced.
- Documentation is updated when behavior, operations, or user-facing contracts change.
- Critical lane requirements are satisfied when applicable.

## Request changes gate

Request changes when any of the following is true:

- The implementation expands scope beyond the issue.
- Acceptance criteria are missing or only partially satisfied.
- Tests are missing for new behavior.
- Existing behavior changes without being called out in the issue.
- Architecture boundaries are changed without an explicit decision.
- Risk notes are missing for critical changes.
- Rollback or recovery notes are missing for runtime/deployment changes.
- Documentation contradicts code behavior.
- The review package is incomplete.

## Blocked gate

Block the work when any of the following is true:

- The issue lacks goal, acceptance criteria, or allowed paths.
- The change requires an architecture decision that has not been made.
- Required credentials, environments, or data are missing.
- CI/test failures are unexplained.
- Security, cost, or deployment risk is unresolved.
- The owner must decide between competing implementation options.

## Critical lane gate

Critical lane work requires stricter review.

The reviewer must verify:

- Human approval is required and documented.
- Auto-merge is not used.
- Risk notes explain what can go wrong.
- Rollback/recovery notes exist when runtime behavior is affected.
- No unrelated refactor is included.
- Tests cover representative success and failure paths.
- Trading, risk, backtesting, or execution changes avoid unsupported claims.

## Gate labels

Use these labels only when they create an actual merge condition:

| Label | Required behavior |
| --- | --- |
| `gate:human-review` | Owner or human reviewer must approve before merge |
| `gate:no-automerge` | Auto-merge is forbidden |
| `gate:security-review` | Security-sensitive diff must be explicitly reviewed |
| `gate:rollback-required` | Rollback/recovery note is required |
| `gate:cost-review` | Paid API or runtime cost impact must be reviewed |

## Reviewer output

Reviewer output should be decisive:

```text
DECISION: APPROVE | REQUEST_CHANGES | BLOCKED

SUMMARY

ACCEPTANCE CRITERIA CHECK

SCOPE CHECK

TEST EVIDENCE

RISK / GOVERNANCE FINDINGS

REQUIRED FIXES

OPTIONAL FOLLOW-UPS
```

Optional follow-ups must not block merge unless they are required by the issue or gate labels.
