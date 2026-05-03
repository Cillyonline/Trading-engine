# AGENTS.md

Codex and other AI coding agents must follow these repository rules.

## Scope and authority

AI agents are implementation assistants. They MUST NOT:
- change repository architecture or boundaries
- introduce new subsystems
- expand feature scope beyond the active task/issue
- perform refactors outside the current task
- "improve" unrelated code

Architecture decisions belong to the repository owner.

## Authoritative repository content

Files committed to governance, source, configuration, test, runtime, or documentation paths are authoritative repository content.

Helper or drafting artifacts (for example scratch notes, exported issue text, prompt drafts, or temporary working files) are NON-authoritative by default.

Unless the active issue explicitly requires them, helper or drafting artifacts MUST NOT be committed in the repository root or in authoritative tracked paths; keep them outside the repository or in ignored local-only workspace locations.

## Governance documents

AI-assisted work must follow these governance documents when they apply:

- `docs/governance/ai-workflow.md` — project lanes, AI autonomy levels, draft PR workflow, and review package rules
- `docs/governance/review-gates.md` — approval, request-changes, blocked, and critical-lane review gates
- `docs/governance/definition-of-ready-done.md` — readiness and completion criteria for issues and pull requests

If these documents conflict with a task prompt, the governance documents win unless the repository owner explicitly decides otherwise.

## Issue governance

If a GitHub issue is referenced (e.g. `#521`), the agent MUST implement strictly within that issue.

Required in the issue context before writing code:
- Goal
- Acceptance Criteria
- Allowed files / allowed paths

Issue title/type may be inferred from the issue context.
If Goal / Acceptance Criteria / Allowed files are missing or unclear → STOP and ask for clarification.

If NO issue is referenced, agents may only do:
- debugging
- test fixes
- code analysis
- small bug fixes

No feature work without an issue.

## Change policy

- Make minimal, localized changes.
- Modify only files required by the task scope.
- Avoid formatting-only diffs.
- Preserve public interfaces unless explicitly required.

If multiple files must change:
1) present a file list first
2) then implement

## Test policy

After code changes:
- run existing tests OR
- add tests for new behavior

Do not knowingly break the test suite.

## Pull request and review policy

Standard-lane and critical-lane work must use a draft pull request as the review container before merge.

Critical-lane work includes changes to trading strategy behavior, risk framework behavior, backtesting assumptions, execution/order lifecycle, persistence semantics, deployment, security, secrets, paid APIs, or operational runtime behavior.

Critical-lane work requires human approval and MUST NOT be auto-merged.

## Output expectations (for agent responses)

Agents must provide a review package after implementation:

- SUMMARY
- MODIFIED FILES
- NEW FILES
- DELETED FILES
- TEST COMMAND
- FULL TEST OUTPUT
- RISK NOTES
- OUT OF SCOPE
- FOLLOW-UP ISSUES

Responses should be short and scope-focused. Do not add out-of-scope suggestions unless they are listed as optional follow-up issues.
