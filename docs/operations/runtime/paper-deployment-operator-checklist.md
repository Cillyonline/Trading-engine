# Paper Deployment Operator Acceptance Checklist

## Instructions
1. Fill every item with `YES` or `NO`.
2. Provide concrete evidence references (command output, artifact path, run id).
3. If any item is `NO` or blank, the deployment is not paper-install-ready.

## Current Session Status Note (2026-04-05)
For the bounded staging and first non-empty paper evidence cycle closure
captured for OPS-P59, see:
- `docs/operations/runtime/staging-paper-progress-2026-04-03.md`

This note is informational only and does not replace a fully completed
checklist.

## OPS-P59 Verified Runtime/Operator Snapshot (2026-04-05)
The runtime/operator status for bounded staging paper evidence is:

Validated and completed:
- bounded staging deployment
- localhost-only binding (`127.0.0.1:18000:8000`)
- successful staging validation output including `STAGING_VALIDATE:SUCCESS`
- health readiness (`/health/engine`, `/health/data`, `/health/guards`) with
  healthy engine runtime (`runtime_running_fresh`)
- read-only paper inspection validation (`/paper/workflow` with
  `validation.ok: true`, `/paper/reconciliation` with `ok: true`,
  `mismatches: 0`)
- consistent bounded read-only inspection across `/trading-core/*` and
  `/paper/*`
- persisted staging DB file at `/srv/cilly/staging/db/cilly_trading.db`
- first non-empty bounded paper evidence cycle completed
- P53 automation via authoritative bounded staging container path completed:
  - `docker compose --env-file .env -f docker/staging/docker-compose.staging.yml exec api python /app/scripts/run_post_run_reconciliation.py --db-path /data/db/cilly_trading.db --evidence-dir /data/artifacts/reconciliation`
  - `docker compose --env-file .env -f docker/staging/docker-compose.staging.yml exec api python /app/scripts/generate_weekly_review.py --db-path /data/db/cilly_trading.db --evidence-dir /data/artifacts/weekly-review`
  - `docker compose --env-file .env -f docker/staging/docker-compose.staging.yml exec api python /app/scripts/capture_restart_evidence.py --phase pre-restart --db-path /data/db/cilly_trading.db --evidence-dir /data/artifacts/restart-evidence`
  - `docker compose --env-file .env -f docker/staging/docker-compose.staging.yml exec api python /app/scripts/capture_restart_evidence.py --phase post-restart --db-path /data/db/cilly_trading.db --evidence-dir /data/artifacts/restart-evidence --baseline /data/artifacts/restart-evidence/pre-restart-pass-YYYYMMDDTHHMMSSZ.json`
- automation outcomes verified: post-run reconciliation `PASS`, weekly review
  `PASS`, pre-restart evidence `PASS`, post-restart evidence `PASS`,
  `baseline_match: true`, weekly review `all_valid: true`
- evidence artifacts persisted under `/srv/cilly/staging/artifacts/...`
- observed persisted artifact patterns:
  - `reconciliation-pass-*.json`
  - `weekly-review-pass-*.json`
  - `pre-restart-pass-*.json`
  - `post-restart-pass-*.json`
- additional rerun validation command passed:
  `python3 scripts/validate_staging_deployment.py` (`STAGING_VALIDATE:SUCCESS`)

Bounded acceptance status for this issue scope:
- `ACCEPTED (BOUNDED_STAGING_PAPER_EVIDENCE_COMPLETE)`
- no live-trading, broker, or production-readiness claim

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

## E) Long-Run Paper Review Evidence

| # | Item | Evidence reference | Answer (YES/NO) |
| --- | --- | --- | --- |
| E1 | Long-run review workflow executed: `GET /paper/workflow` returned `validation.ok: true` | `EVIDENCE_PAPER_CONSISTENCY_TEST_OUTPUT` | |
| E2 | All R1–R7 review artifacts captured in sequence per Phase 44 workflow doc | `EVIDENCE_PAPER_CONSISTENCY_TEST_OUTPUT` | |
| E3 | Strategy-change comparison baseline captured (required if any strategy change applied during this session; `N/A` if no strategy change) | `EVIDENCE_PAPER_CONSISTENCY_TEST_OUTPUT` | |
| E4 | Post-restart recovery verification completed: `GET /paper/reconciliation` returned `ok: true`, `mismatches: 0` after most recent restart | `EVIDENCE_PAPER_CONSISTENCY_TEST_OUTPUT` | |

### Automated Review Evidence Commands

The following scripts automate evidence capture for Section E items:

- **Post-run reconciliation**: `docker compose --env-file .env -f docker/staging/docker-compose.staging.yml exec api python /app/scripts/run_post_run_reconciliation.py --db-path /data/db/cilly_trading.db --evidence-dir /data/artifacts/reconciliation` (supports E1, E4)
- **Weekly review artifacts (R1-R7)**: `docker compose --env-file .env -f docker/staging/docker-compose.staging.yml exec api python /app/scripts/generate_weekly_review.py --db-path /data/db/cilly_trading.db --evidence-dir /data/artifacts/weekly-review` (supports E2)
- **Pre-restart baseline**: `docker compose --env-file .env -f docker/staging/docker-compose.staging.yml exec api python /app/scripts/capture_restart_evidence.py --phase pre-restart --db-path /data/db/cilly_trading.db --evidence-dir /data/artifacts/restart-evidence` (supports E3)
- **Post-restart verification**: `docker compose --env-file .env -f docker/staging/docker-compose.staging.yml exec api python /app/scripts/capture_restart_evidence.py --phase post-restart --db-path /data/db/cilly_trading.db --evidence-dir /data/artifacts/restart-evidence --baseline /data/artifacts/restart-evidence/pre-restart-pass-YYYYMMDDTHHMMSSZ.json` (supports E4)

Evidence output directories in bounded staging: `/data/artifacts/reconciliation`, `/data/artifacts/weekly-review`, `/data/artifacts/restart-evidence`
Bound host persistence path: `/srv/cilly/staging/artifacts/...`

See `docs/operations/runtime/p53-automated-review-operations.md` for the full automation contract.

## F) Checklist Completion Evidence

| # | Item | Evidence reference | Answer (YES/NO) |
| --- | --- | --- | --- |
| F1 | This checklist is fully completed and every required section is `YES` (or `N/A` where explicitly permitted) | `EVIDENCE_COMPLETED_OPERATOR_CHECKLIST` | |

## Final Operator Decision
Decision rule:
- Any `NO` or blank -> `NOT ACCEPTED: REMAIN STAGING`
- All `YES` -> `ACCEPTED: PAPER_INSTALL_READY`

OPS-P59 bounded evidence status:
`ACCEPTED (BOUNDED_STAGING_PAPER_EVIDENCE_COMPLETE)`

Final decision (`ACCEPTED: PAPER_INSTALL_READY` or `NOT ACCEPTED: REMAIN STAGING`) if this checklist is executed as a full gate run:

Operator name:

Date (UTC):
