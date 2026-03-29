# Paper Deployment Operator Acceptance Checklist

## Instructions
1. Fill every item with `YES` or `NO`.
2. Provide concrete evidence references (command output, artifact path, run id).
3. If any item is `NO` or blank, the deployment is not paper-install-ready.

## Required Evidence Output Names
Use these exact evidence identifiers in the checklist references:
- `EVIDENCE_STAGING_VALIDATION_LOG`
- `EVIDENCE_STAGING_HEALTH_SNAPSHOTS`
- `EVIDENCE_PAPER_CONSISTENCY_TEST_OUTPUT`
- `EVIDENCE_FULL_PYTEST_OUTPUT`
- `EVIDENCE_COMPLETED_OPERATOR_CHECKLIST`

## A) Staging Install Prerequisite

| # | Item | Evidence reference | Answer (YES/NO) |
| --- | --- | --- | --- |
| A1 | Staging deployment validation command completed: `python scripts/validate_staging_deployment.py` | `EVIDENCE_STAGING_VALIDATION_LOG` | |
| A2 | Validation output includes all mandatory markers: `STAGING_VALIDATE:CONFIG_OK`, `STAGING_VALIDATE:UP_OK`, `STAGING_VALIDATE:HEALTH_OK`, `STAGING_VALIDATE:RESTART_OK`, `STAGING_VALIDATE:POST_RESTART_HEALTH_OK`, `STAGING_VALIDATE:SUCCESS` | `EVIDENCE_STAGING_VALIDATION_LOG` | |
| A3 | Restart validation passed and post-restart health remained ready | `EVIDENCE_STAGING_VALIDATION_LOG` | |

## B) Explicit Staging Health Evidence

| # | Item | Evidence reference | Answer (YES/NO) |
| --- | --- | --- | --- |
| B1 | `/health/engine` shows `ready: true` | `EVIDENCE_STAGING_HEALTH_SNAPSHOTS` | |
| B2 | `/health/data` shows `ready: true` | `EVIDENCE_STAGING_HEALTH_SNAPSHOTS` | |
| B3 | `/health/guards` shows `ready: true` and allowing decision under bounded staging defaults | `EVIDENCE_STAGING_HEALTH_SNAPSHOTS` | |

## C) Paper-Consistency Test Evidence

| # | Item | Evidence reference | Answer (YES/NO) |
| --- | --- | --- | --- |
| C1 | `tests/test_paper_trading_simulator.py` passed | `EVIDENCE_PAPER_CONSISTENCY_TEST_OUTPUT` | |
| C2 | `tests/test_api_paper_inspection_read.py` passed | `EVIDENCE_PAPER_CONSISTENCY_TEST_OUTPUT` | |
| C3 | Paper path remains non-live and non-broker in validated outputs | `EVIDENCE_PAPER_CONSISTENCY_TEST_OUTPUT` | |

## D) Full Repository Regression Evidence

| # | Item | Evidence reference | Answer (YES/NO) |
| --- | --- | --- | --- |
| D1 | Full repository test suite passed with `python -m pytest` | `EVIDENCE_FULL_PYTEST_OUTPUT` | |

## E) Checklist Completion Evidence

| # | Item | Evidence reference | Answer (YES/NO) |
| --- | --- | --- | --- |
| E1 | This checklist is fully completed and every required section is `YES` | `EVIDENCE_COMPLETED_OPERATOR_CHECKLIST` | |

## Final Operator Decision
Decision rule:
- Any `NO` or blank -> `NOT ACCEPTED: REMAIN STAGING`
- All `YES` -> `ACCEPTED: PAPER_INSTALL_READY`

Final decision (`ACCEPTED: PAPER_INSTALL_READY` or `NOT ACCEPTED: REMAIN STAGING`):

Operator name:

Date (UTC):
