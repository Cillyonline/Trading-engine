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

## Output expectations (for agent responses)

- list all modified files
- list all new files
- provide full contents of changed files
- short explanation only (no out-of-scope suggestions)
