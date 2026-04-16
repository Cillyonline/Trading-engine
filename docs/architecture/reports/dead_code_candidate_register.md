# Dead-Code Candidate Register

## Document Status
- Class: Derived
- Canonical Source(s): Issue #945
- Rationale: Register and evidence surface for bounded dead-code candidate classification without deletion.

## Scope

This register is intentionally bounded to one isolated candidate cluster for
issue `#945`: tracked temporary review artifacts that are not part of runtime,
package, API, CLI, UI, or test contracts.

## Candidate Register

| Candidate path | Classification | Confidence | Rationale | Reference-check evidence | Remediation eligibility |
| --- | --- | --- | --- | --- | --- |
| `pr_issue_935.md` | probable dead | high | One-off PR drafting artifact at repository root; not part of canonical docs, runtime, or tests. | No repo references by name (`git grep` check), no contract docs reference. | Eligible for future bounded remediation wave (#948), not removed in #945. |
| `tests/.tmp_issue955_broader_output.txt` | probable dead | high | Temporary pytest output artifact; non-authoritative transient log content. | No repo references by name (`git grep` check), not a pytest module (`test_*.py`). | Eligible for future bounded remediation wave (#948), not removed in #945. |
| `tests/.tmp_issue955_targeted_output.txt` | probable dead | high | Temporary targeted pytest output artifact; non-authoritative transient log content. | No repo references by name (`git grep` check), not a pytest module (`test_*.py`). | Eligible for future bounded remediation wave (#948), not removed in #945. |
| `tests/issue955_review_package.txt` | probable dead | high | Generated review package dump for a prior issue; not imported, executed, or contract-bound. | No repo references by name (`git grep` check), no runtime/API/CLI/UI contract references. | Eligible for future bounded remediation wave (#948), not removed in #945. |

## Reference Check Evidence

Reference checks were executed with:

~~~powershell
git grep -n "pr_issue_935.md|\.tmp_issue955_broader_output\.txt|\.tmp_issue955_targeted_output\.txt|issue955_review_package\.txt" -- .
~~~

Result: no references found.

## Per-Candidate Verification Dimensions

### Imports/Usages
All four candidates: no code imports/usages found.

### Tests
No test module references to any candidate path by name.
Candidates under `tests/` are artifact files, not pytest modules.

### Runtime Mounts
No candidate is mounted or loaded by runtime bootstrap.

### Documented API/CLI/UI Contracts
No candidate path appears in documented API, CLI, UI, or index contracts.

### Relevant Documentation References
No cross-document links to any candidate path were found by repository path search.

## Remediation Eligibility Summary

All listed candidates are classified probable dead with high confidence.
Eligibility is explicitly conditional on a separate remediation issue, such as #948.
No deletion or functional code change is performed by this register issue #945.
