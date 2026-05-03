# Definition of Ready and Definition of Done

## Purpose

This document defines when an issue is ready for AI-assisted implementation and when it is done. It prevents vague issues from becoming vague code and prevents incomplete pull requests from being merged.

## Definition of Ready

An issue is ready only when it contains the following information:

- Goal: what must be achieved.
- Why now / context: why the work matters.
- Scope: what is included.
- Out of scope: what must not be changed.
- Acceptance criteria: objective checks for completion.
- Suggested affected areas or allowed paths.
- Test or evidence requirement.
- Risk or governance note.

If goal, acceptance criteria, or allowed paths are missing or unclear, AI coding agents must stop and ask for clarification.

## Ready checklist

```text
[ ] Goal is clear
[ ] Context explains why the issue exists
[ ] Scope is bounded
[ ] Out of scope is explicit
[ ] Acceptance criteria are testable
[ ] Suggested affected areas / allowed paths are listed
[ ] Test or evidence requirement is stated
[ ] Risk / governance note is present
[ ] Lane is clear: fast, standard, or critical
[ ] Labels are set: type + area + ai
[ ] Gate labels are set when needed
```

## Additional readiness for critical lane

Critical lane issues also need:

```text
[ ] Human review requirement is explicit
[ ] Auto-merge is forbidden
[ ] Risk notes are required
[ ] Rollback/recovery expectation is stated when runtime behavior may change
[ ] No unsupported readiness, profitability, live-trading, broker-readiness, trader-validation, or production-readiness claims are allowed
```

## Definition of Done

An issue is done only when all relevant conditions are true:

- Implementation satisfies the acceptance criteria.
- The change remains within issue scope.
- Tests passed or test limitation is documented and accepted.
- Review package is complete.
- Draft PR review is complete for standard and critical lane work.
- CI is green or failure is unrelated and accepted by owner.
- Documentation is updated when behavior, operation, or contracts change.
- No unresolved blocking review comment remains.
- Follow-up issues are created for intentionally deferred work.
- The pull request is merged.

## Done checklist

```text
[ ] Acceptance criteria satisfied
[ ] Scope respected
[ ] Tests run and documented
[ ] Review package complete
[ ] Draft PR reviewed where required
[ ] CI result acceptable
[ ] Documentation updated where needed
[ ] Risk notes included where needed
[ ] Rollback/recovery notes included where needed
[ ] No unsupported claims introduced
[ ] Follow-up issues created for deferred work
[ ] PR merged
```

## Review package requirement

The coding agent must provide:

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

## Not done examples

The issue is not done if:

- The implementation works but lacks tests required by the issue.
- The PR contains unrelated refactors.
- Documentation makes stronger claims than the code or evidence supports.
- A critical lane change has no human approval.
- A deployment-affecting change has no rollback or recovery note.
- CI failure is ignored instead of explained.
