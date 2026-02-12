## 1) Purpose
Maintenance mode requires deterministic CI validation so that repeat workflow executions on the same revision produce consistent pass/fail outcomes and can be trusted for release safety checks.

## 2) Reproduction Steps
1. Open GitHub and navigate to **Actions**.
2. Open the **Smoke-Run Contract** workflow.
3. Set/filter the branch to **main**.
4. Select a single commit and trigger the workflow **3 times** against that same commit.
5. Confirm all three runs complete successfully.

## 3) Validation Evidence
Observed validation runs on `main`:
- Run #561 – Commit dba2001
- Run #559 – Commit 4d1195c
- Run #557 – Commit 0af7bde

All listed runs passed successfully without variance.

## 4) Determinism Conclusion
- No flaky behavior reproducible.
- `pytest` execution unchanged.
- No runtime behavior change introduced.
- No workflow modification required.
