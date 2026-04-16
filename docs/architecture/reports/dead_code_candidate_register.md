# Dead-Code Candidate Register

## Document Status
- Class: Derived
- Canonical Source(s): Issue #945, Issue #948
- Rationale: Register and evidence surface for bounded dead-code candidate handling.

## Scope

This register is intentionally bounded to one isolated cleanup cluster for issue
`#948`: tracked temporary review artifacts that are not part of runtime,
package, API, CLI, UI, or test contracts.

## Candidate Register (Pre-Removal)

| Candidate path | Classification | Confidence | Rationale | Status before wave |
| --- | --- | --- | --- | --- |
| `pr_issue_935.md` | probable dead | high | One-off PR drafting artifact at repository root; not part of canonical docs, runtime, or tests. | registered |
| `tests/.tmp_issue955_broader_output.txt` | probable dead | high | Temporary pytest output artifact; non-authoritative transient log content. | registered |
| `tests/.tmp_issue955_targeted_output.txt` | probable dead | high | Temporary targeted pytest output artifact; non-authoritative transient log content. | registered |
| `tests/issue955_review_package.txt` | probable dead | high | Generated review package dump for a prior issue; not imported, executed, or contract-bound. | registered |

## Reference Check Result

Reference checks were executed before removal with:

```powershell
git grep -n "pr_issue_935.md|\.tmp_issue955_broader_output\.txt|\.tmp_issue955_targeted_output\.txt|issue955_review_package\.txt" -- .
```

Result: no references found.

## Per-Candidate Verification Dimensions

1. Imports/Usages
- All four candidates: no code imports/usages found (`git grep` result empty).

2. Tests
- No test module references to any candidate path by name.
- Candidates under `tests/` are artifact files, not pytest modules (`test_*.py`).

3. Runtime mounts
- No candidate is mounted or loaded by runtime bootstrap (`src/api/main.py` mounts only `/ui` static directory).

4. Documented API/CLI/UI contracts
- No candidate path appears in `docs/operations/api/**`, `docs/operations/cli/**`, `docs/operations/ui/**`, or `docs/index.md`.

5. Relevant documentation references
- No cross-document links to any candidate path were found by repository path search.

## Wave #948 Execution

Removed candidates in this bounded first wave:
- `pr_issue_935.md`
- `tests/.tmp_issue955_broader_output.txt`
- `tests/.tmp_issue955_targeted_output.txt`
- `tests/issue955_review_package.txt`

## Boundary Confirmation
- One isolated cluster only (temporary/review artifacts).
- No runtime code path, subsystem boundary, or public contract surface changed.
