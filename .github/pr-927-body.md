Closes #927

## Summary
- strengthened bounded run-evidence interpretation rules for post-active server-test review
- clarified decision-support review semantics: pass, pass-with-note, fail
- added explicit follow-up issue triggers for reproducible bounded defects
- aligned staging deployment runbook and operator checklist references to the new interpretation section

## Scope
- docs-only update
- no automation changes
- no production-readiness or live-trading claims
- no architecture/runtime behavior changes

## Files changed
- docs/operations/runtime/p53-automated-review-operations.md
- docs/operations/runtime/staging-server-deployment.md
- docs/operations/runtime/paper-deployment-operator-checklist.md

## Validation
- Ran: python -m uv run -- python -m pytest --import-mode=importlib
- Result: 1013 passed, 4 warnings
