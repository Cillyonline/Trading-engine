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
- Phase 6 gilt nur als abgeschlossen, wenn die Exit-Kriterien und die Exit-Checklist vollständig erfüllt sind: [phase-6-exit-criteria.md](phase-6-exit-criteria.md), [checklists/phase-6-exit-checklist.md](checklists/phase-6-exit-checklist.md)

## Deterministic Smoke Run – Local Execution

### Prerequisites
- Python 3 available in your environment.
- Run from the repository root so the default fixtures path (`fixtures/smoke-run/`) is available.
- Ensure the package is importable by setting `PYTHONPATH=src`. There is no installed top-level CLI command, so use the documented Python module command.

### Command (exact)
```bash
PYTHONPATH=src python -c 'from cilly_trading.smoke_run import run_smoke_run; raise SystemExit(run_smoke_run())'
```

### Expected stdout on success (exact, line-by-line)
```
SMOKE_RUN:START
SMOKE_RUN:FIXTURES_OK
SMOKE_RUN:CHECKS_OK
SMOKE_RUN:END
```

### Artifacts
- `artifacts/smoke-run/result.json`

### Exit code semantics
- `0` — success.
- `10` — fixtures missing (`input.json`, `expected.csv`, `config.yaml`).
- `11` — fixtures invalid (format, missing required keys/columns, or parse errors).
- `12` — constraints failed (validation errors or determinism guard triggered).
- `13` — output mismatch (artifact write/read mismatch).

### Determinism note
The smoke-run is deterministic: no time access, no randomness, and no network access are permitted during execution. Any attempt to access these will fail the run via the determinism guard.

### Reference
- [smoke-run.md](smoke-run.md)

## Quality Gate: Deterministic Smoke Run (Mandatory)

### Gate name
Deterministic Smoke Run

### Execution command (exact)
```bash
PYTHONPATH=src python -c 'from cilly_trading.smoke_run import run_smoke_run; raise SystemExit(run_smoke_run())'
```

### PASS conditions (explicit)
- Exit code == 0.
- Stdout contains EXACTLY (line-by-line, in order, no extra output):
  ```
  SMOKE_RUN:START
  SMOKE_RUN:FIXTURES_OK
  SMOKE_RUN:CHECKS_OK
  SMOKE_RUN:END
  ```

### FAIL conditions (explicit)
- Exit code != 0.
- Exit codes:
  - 10 (fixtures missing)
  - 11 (fixtures invalid)
  - 12 (constraints failed)
  - 13 (output mismatch)
- OR stdout deviates from the required success lines.
- Failure cases do NOT require specific stdout markers; failure is determined by exit code and/or deviation from the success stdout contract.

## Remote (Codespaces)

### Start Codespace
1) Open the repository on GitHub.
2) Select **Code → Codespaces → Create codespace on main**.
3) Wait for the devcontainer to finish provisioning and dependency install.

### Run Tests
```bash
python -m pytest
```

## Pull Request Testing
- Pull Requests are automatically tested in GitHub Actions.
- A green check allows merge.
- A red check blocks merge until tests pass.

### Run Paper Trading (Simulation)
No dedicated CLI endpoint is documented for paper-trading simulation in this runbook. The repository contains a simulator module (`src/cilly_trading/engine/paper_trading.py`), but no owner-facing run command is defined here. No live trading, broker keys, or real orders are used.
