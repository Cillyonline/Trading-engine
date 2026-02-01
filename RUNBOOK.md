# Working SOP – Cilly Trading Engine

## Default
- MODE: EXECUTION
- Exactly one active Issue

## Workflow
1) DEFINE
   - Create/confirm Issue exists (use Issue template)
   - Acceptance Criteria are testable
   - Set Board status: Ready

2) EXECUTE
   - Codex B implements strictly per the active Issue
   - Open a PR

3) VERIFY
   - Run local tests
   - Record commands + outputs in PR ("How to Test")

4) REVIEW GATE
   - Codex B provides list of all modified/new files
   - Provide full file contents to Codex A
   - Codex A returns: APPROVED or CHANGES REQUIRED

5) CLOSE
   - PR must include: Closes #<IssueID>
   - Merge only after APPROVED + green test
   - Issue closes automatically on merge
   - Set Board status: Done

## Blocked Rule
- If blocked: fix the blocker only
- No new topics while blocked

## Error Reporting
Always provide:
- command executed
- full output
- expected vs actual

## Definition of Done (DoD)
A change is considered DONE only if:
- Acceptance Criteria are fully met
- Tests were run and results are recorded in the PR
- Required status check test is green
- PR includes Closes #<IssueID>
- Codex A review gate result is recorded (APPROVED or CHANGES REQUIRED)
- No scope creep beyond the linked Issue
- Phase 6 gilt nur als abgeschlossen, wenn die Exit-Kriterien und die Exit-Checklist vollständig erfüllt sind: [docs/phase-6-exit-criteria.md](docs/phase-6-exit-criteria.md), [docs/checklists/phase-6-exit-checklist.md](docs/checklists/phase-6-exit-checklist.md)

## Remote (Codespaces)

### Start Codespace
1) Open the repository on GitHub.
2) Select **Code → Codespaces → Create codespace on main**.
3) Wait for the devcontainer to finish provisioning and dependency install.

### Run Tests
```bash
python -m pytest
```

### Run Paper Trading (Simulation)
Not available — Blocker: no paper-trading/simulation entrypoint is documented or implemented in the repo without touching `src/**`. No live trading, broker keys, or real orders are used.
