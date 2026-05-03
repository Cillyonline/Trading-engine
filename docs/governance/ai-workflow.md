# AI-Assisted Project Workflow

## Purpose

This document defines the standard workflow for AI-assisted project delivery in this repository. It is intended to keep AI-assisted implementation fast, reviewable, and bounded by repository governance.

The core rule is:

> GitHub is the source of truth. AI agents assist with planning, implementation, and review. The repository owner remains responsible for scope, architecture, risk, and merge decisions.

## Roles

| Role | Primary responsibility |
| --- | --- |
| Repository owner | Prioritization, architecture decisions, risk decisions, final approval |
| Planner AI | Issue shaping, roadmap support, acceptance criteria, risk framing |
| Coding AI | Scoped implementation on a branch, tests, documentation updates, review package |
| Reviewer AI | Diff review against issue scope, acceptance criteria, repository rules, and risk gates |
| GitHub | Issues, branches, pull requests, CI evidence, review history, release history |

A single AI may assist in multiple steps, but planning, implementation, and review should remain logically separated. Critical changes should be reviewed by a different model/session/tool than the one that implemented them when feasible.

## Work lanes

Every issue or change belongs to one lane.

### Fast lane

Use only for low-risk changes such as typos, harmless documentation edits, formatting, or comments without logic impact.

Minimum requirements:

- Scope must be obvious.
- Tests are optional when clearly irrelevant.
- Pull request is optional for trivial local maintenance only.

Fast lane is forbidden for strategy logic, risk logic, backtesting, execution, API behavior, data persistence, deployment, security, secrets, or cost-impacting integrations.

### Standard lane

Use for normal feature work, bug fixes, tests, documentation with technical impact, and scoped refactors.

Requirements:

- GitHub issue with goal, scope, out of scope, and acceptance criteria.
- Branch per issue.
- Review package from the coding agent.
- Draft pull request as the review container.
- CI/test evidence before merge.
- Approval before merge.

### Critical lane

Use for changes that can affect correctness, safety, money, data, deployment, or operational behavior.

Examples:

- Trading strategy behavior
- Risk framework behavior
- Backtest execution assumptions
- Order/execution lifecycle
- Broker or exchange integration
- Authentication, authorization, secrets, or credentials
- Database migrations or persistence semantics
- Deployment, rollback, monitoring, or production runtime behavior
- Paid API usage or cost-impacting automation

Additional requirements:

- Human review is mandatory.
- Auto-merge is forbidden.
- Risk notes are mandatory.
- Rollback or recovery notes are mandatory when runtime behavior is affected.
- A second review pass is recommended.

## Labels

Labels should remain operational, not decorative. Use project fields for priority and status where possible.

Minimum issue labels:

- `type:*` — what kind of work this is
- `area:*` — which part of the repository is affected
- `ai:*` — how much autonomy is allowed

Optional gate labels:

- `gate:human-review`
- `gate:no-automerge`
- `gate:security-review`
- `gate:rollback-required`
- `gate:cost-review`

Optional exception label:

- `status:blocked`

## AI autonomy levels

### `ai:auto`

Allowed only for harmless routine changes such as docs-only corrections, formatting, lint-only changes, small test maintenance, or non-behavioral chores.

Rules:

- No product logic changes.
- No API/schema/database changes.
- No deployment or security changes.
- CI must pass if applicable.

### `ai:review`

AI may implement the change, but review and approval are required before merge.

Use for normal issues in the standard lane.

### `ai:manual`

AI may assist, but the owner controls decisions and approval. Use for critical lane changes.

Rules:

- Human approval required.
- Auto-merge forbidden.
- Risk notes required.
- Rollback/recovery notes required when runtime behavior changes.

## Standard issue-to-merge workflow

1. Select or create an issue.
2. Confirm the issue is ready.
3. Assign lane and labels.
4. Create a scoped branch.
5. Coding AI implements only the issue scope.
6. Coding AI runs tests or provides a test limitation note.
7. Coding AI produces a review package.
8. Open a draft pull request.
9. Reviewer checks the PR against the issue, acceptance criteria, `AGENTS.md`, and governance docs.
10. If changes are requested, send a bounded fix prompt to the coding AI.
11. Repeat review until accepted.
12. Mark PR ready only when review and CI evidence are acceptable.
13. Merge only after required approvals.
14. Update changelog, release notes, or operations docs when applicable.

## Review package

The coding agent must provide this after implementation:

```text
SUMMARY

MODIFIED FILES

NEW FILES

DELETED FILES

TEST COMMAND

FULL TEST OUTPUT

RISK NOTES

OUT OF SCOPE

FOLLOW-UP ISSUES
```

## Fix loop

When review finds problems, the fix prompt must be bounded:

```text
Fix only the listed review findings.
Do not expand scope.
Do not refactor unrelated code.
Follow AGENTS.md and the active issue acceptance criteria.
Update tests and documentation only where required by the findings.
Return an updated review package.
```

## Non-negotiable boundaries

AI agents must not:

- Change repository architecture without an explicit architecture decision.
- Expand scope beyond the issue.
- Introduce readiness, profitability, live-trading, broker-readiness, or production-readiness claims without evidence and owner approval.
- Commit secrets or credentials.
- Merge critical lane changes without human approval.
