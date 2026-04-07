# Paper Deployment Operator Acceptance Checklist

## Instructions
1. Fill every required item with `YES`, `NO`, or permitted `N/A`.
2. Provide concrete evidence references (command output, artifact path, run id).
3. If any required readiness item is `NO` (or blank), final decision is `NOT ACCEPTED: REMAIN STAGING`.

## Historical Status Note (Informational)
For prior bounded staging and first non-empty paper evidence-cycle closure (OPS-P59), see:
- `docs/operations/runtime/staging-paper-progress-2026-04-03.md`

This historical note is informational only and does not replace a fully completed gate run.

## OPS-P54 Bounded Gate Run (2026-04-07 UTC)
This checklist records one full bounded gate execution for issue #907 using the current local staging/paper runtime path.

### Evidence Register

#### EVIDENCE_STAGING_VALIDATION_LOG
- Command: `python scripts/validate_staging_deployment.py`
- Observed output: `STAGING_VALIDATE:FAILED:docker compose config failed`
- Command: `python scripts/validate_staging_deployment.py --env-file .env.example`
- Observed output: `STAGING_VALIDATE:CONFIG_OK` followed by `STAGING_VALIDATE:FAILED:docker compose up failed`
- Supporting command: `docker compose --env-file .env.example -f docker/staging/docker-compose.staging.yml up -d --build`
- Supporting output: `failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine`.

#### EVIDENCE_STAGING_HEALTH_SNAPSHOTS
- Command: `curl.exe -sS --max-time 10 -H "X-Cilly-Role: read_only" http://127.0.0.1:18000/health/engine`
- Command: `curl.exe -sS --max-time 10 -H "X-Cilly-Role: read_only" http://127.0.0.1:18000/health/data`
- Command: `curl.exe -sS --max-time 10 -H "X-Cilly-Role: read_only" http://127.0.0.1:18000/health/guards`
- Observed output for each: `curl: (7) Failed to connect to 127.0.0.1 port 18000 ... Could not connect to server`.

#### EVIDENCE_PAPER_CONSISTENCY_TEST_OUTPUT
- Command: `python -m pytest tests/test_paper_trading_simulator.py tests/test_api_paper_inspection_read.py`
- Observed output: `11 passed`.
- Command: `python -m pytest tests/cilly_trading/engine/test_non_live_risk_boundaries.py`
- Observed output: `3 passed`.

#### EVIDENCE_FULL_PYTEST_OUTPUT
- Command: `python -m pytest`
- Observed output: `973 passed, 4 warnings`.

#### EVIDENCE_COMPLETED_OPERATOR_CHECKLIST
- Artifact: `docs/operations/runtime/paper-deployment-operator-checklist.md`
- Run section: `OPS-P54 Bounded Gate Run (2026-04-07 UTC)`
- Final gate decision section: `Final Operator Decision`.

## Required Evidence Output Names
Use these exact evidence identifiers in the checklist references:
- `EVIDENCE_STAGING_VALIDATION_LOG`
- `EVIDENCE_STAGING_HEALTH_SNAPSHOTS`
- `EVIDENCE_PAPER_CONSISTENCY_TEST_OUTPUT`
- `EVIDENCE_FULL_PYTEST_OUTPUT`
- `EVIDENCE_COMPLETED_OPERATOR_CHECKLIST`

## A) Staging Install Prerequisite

| # | Item | Evidence reference | Answer (YES/NO/N/A) |
| --- | --- | --- | --- |
| A1 | Staging deployment validation command completed: `python scripts/validate_staging_deployment.py` | `EVIDENCE_STAGING_VALIDATION_LOG` | NO |
| A2 | Validation output includes all mandatory markers: `STAGING_VALIDATE:CONFIG_OK`, `STAGING_VALIDATE:UP_OK`, `STAGING_VALIDATE:HEALTH_OK`, `STAGING_VALIDATE:RESTART_OK`, `STAGING_VALIDATE:POST_RESTART_HEALTH_OK`, `STAGING_VALIDATE:SUCCESS` | `EVIDENCE_STAGING_VALIDATION_LOG` | NO |
| A3 | Restart validation passed and post-restart health remained ready | `EVIDENCE_STAGING_VALIDATION_LOG` | NO |

## B) Explicit Staging Health Evidence

| # | Item | Evidence reference | Answer (YES/NO/N/A) |
| --- | --- | --- | --- |
| B1 | `/health/engine` shows `ready: true` | `EVIDENCE_STAGING_HEALTH_SNAPSHOTS` | NO |
| B2 | `/health/data` shows `ready: true` | `EVIDENCE_STAGING_HEALTH_SNAPSHOTS` | NO |
| B3 | `/health/guards` shows `ready: true` and allowing decision under bounded staging defaults | `EVIDENCE_STAGING_HEALTH_SNAPSHOTS` | NO |

## C) Paper-Consistency Test Evidence

| # | Item | Evidence reference | Answer (YES/NO/N/A) |
| --- | --- | --- | --- |
| C1 | `tests/test_paper_trading_simulator.py` passed | `EVIDENCE_PAPER_CONSISTENCY_TEST_OUTPUT` | YES |
| C2 | `tests/test_api_paper_inspection_read.py` passed | `EVIDENCE_PAPER_CONSISTENCY_TEST_OUTPUT` | YES |
| C3 | Paper path remains non-live and non-broker in validated outputs | `EVIDENCE_PAPER_CONSISTENCY_TEST_OUTPUT` | YES |

## D) Full Repository Regression Evidence

| # | Item | Evidence reference | Answer (YES/NO/N/A) |
| --- | --- | --- | --- |
| D1 | Full repository test suite passed with `python -m pytest` | `EVIDENCE_FULL_PYTEST_OUTPUT` | YES |

## E) Long-Run Paper Review Evidence

| # | Item | Evidence reference | Answer (YES/NO/N/A) |
| --- | --- | --- | --- |
| E1 | Long-run review workflow executed: `GET /paper/workflow` returned `validation.ok: true` | `EVIDENCE_PAPER_CONSISTENCY_TEST_OUTPUT` | NO |
| E2 | All R1–R7 review artifacts captured in sequence per Phase 44 workflow doc | `EVIDENCE_PAPER_CONSISTENCY_TEST_OUTPUT` | NO |
| E3 | Strategy-change comparison baseline captured (required if any strategy change applied during this session; `N/A` if no strategy change) | `EVIDENCE_PAPER_CONSISTENCY_TEST_OUTPUT` | N/A |
| E4 | Post-restart recovery verification completed: `GET /paper/reconciliation` returned `ok: true`, `mismatches: 0` after most recent restart | `EVIDENCE_PAPER_CONSISTENCY_TEST_OUTPUT` | NO |

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

| # | Item | Evidence reference | Answer (YES/NO/N/A) |
| --- | --- | --- | --- |
| F1 | This checklist is fully completed and every required section is explicitly marked `YES`, `NO`, or permitted `N/A` | `EVIDENCE_COMPLETED_OPERATOR_CHECKLIST` | YES |

## Final Operator Decision
Decision rule:
- Any required readiness item marked `NO` (or blank) -> `NOT ACCEPTED: REMAIN STAGING`
- All required readiness items marked `YES` (with only explicitly permitted `N/A`) -> `ACCEPTED: PAPER_INSTALL_READY`

OPS-P54 bounded gate result:
`NOT ACCEPTED: REMAIN STAGING`

Remaining bounded gaps for this run:
- Docker daemon for `desktop-linux` was not available (`npipe:////./pipe/dockerDesktopLinuxEngine` missing), preventing compose startup.
- No active bounded staging runtime on `127.0.0.1:18000`, so `/health/*` readiness evidence could not be captured as ready.
- No current-session long-run paper workflow/reconciliation evidence (`/paper/workflow`, `/paper/reconciliation`, and R1–R7 artifact capture) because staging runtime startup failed.

Non-goal claim boundary for this run:
- This checklist does not claim live trading readiness.
- This checklist does not claim broker integration readiness.
- This checklist does not claim production readiness.

Operator name: Codex B

Date (UTC): 2026-04-07
