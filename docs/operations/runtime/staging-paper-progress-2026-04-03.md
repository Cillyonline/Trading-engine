# Staging and Paper Progress Note (2026-04-03)

## Purpose
Capture the bounded, evidence-based status verified on 2026-04-03.

This note documents observed staging and paper inspection status only. It does
not claim live trading, broker readiness, or production readiness.

## OPS-P55 Frozen Boundary Snapshot
Status is frozen as documented evidence from the 2026-04-03 server session.

### A) Bounded staging deployment (validated)
- localhost-only exposure validated: `127.0.0.1:18000:8000`
- `.env` and required host directories validated
- `python3 scripts/validate_staging_deployment.py` validated
- `/health/engine`, `/health/data`, `/health/guards` validated as ready
- staging DB file validated at `/srv/cilly/staging/db/cilly_trading.db`

### B) Read-only paper inspection (validated)
- `/paper/workflow` validated with `validation.ok: true`
- `/paper/reconciliation` validated with `ok: true`, `mismatches: 0`
- `/paper/*` and `/trading-core/*` surfaces validated as consistent in empty
  initial state

### C) Final paper-install-ready evidence (open)
- `docker compose --env-file .env -f docker/staging/docker-compose.staging.yml exec api python /app/scripts/run_post_run_reconciliation.py --db-path /data/db/cilly_trading.db --evidence-dir /data/artifacts/reconciliation`
- `docker compose --env-file .env -f docker/staging/docker-compose.staging.yml exec api python /app/scripts/generate_weekly_review.py --db-path /data/db/cilly_trading.db --evidence-dir /data/artifacts/weekly-review`
- `docker compose --env-file .env -f docker/staging/docker-compose.staging.yml exec api python /app/scripts/capture_restart_evidence.py --phase pre-restart --db-path /data/db/cilly_trading.db --evidence-dir /data/artifacts/restart-evidence`
- `docker compose --env-file .env -f docker/staging/docker-compose.staging.yml exec api python /app/scripts/capture_restart_evidence.py --phase post-restart --db-path /data/db/cilly_trading.db --evidence-dir /data/artifacts/restart-evidence --baseline /data/artifacts/restart-evidence/pre-restart-pass-YYYYMMDDTHHMMSSZ.json`

This freeze note is documentation-only and does not change runtime/API logic.

## Verified Today

### 1) Server Foundation
- Host OS verified: Debian 13.
- Host tools verified present: Docker, Docker Compose, git, curl.
- Host resources verified sufficient (RAM and disk).
- Host timezone verified correct.
- Initial staging exposure was observed on `0.0.0.0:18000`.
- Compose port binding was corrected to localhost-only:
  `127.0.0.1:18000:8000`.

### 2) Repository and Deploy State
- Repository verified on host at `/root/Trading-engine`.
- Server repository updated to current `main`.
- `.env` created at repository root on host.
- Required staging host directories created under `/srv/cilly/staging/...`.
- Compose stack started successfully with explicit `--env-file`.

### 3) Bounded Staging Runtime
- Bounded staging container started successfully.
- `docker compose ps` reported healthy status.
- `GET /health/engine` verified with `read_only` role.
- `GET /health/data` verified with `ready=true`.
- `GET /health/guards` verified with `ready=true`, `decision=allowing`,
  `blocking=false`.
- `GET /system/state` verified.
- Restart behavior verified.
- Post-fix port binding verified as localhost-only (`127.0.0.1:18000`).

### 4) Formal Staging Validation
- `python3 scripts/validate_staging_deployment.py` executed successfully.
- Observed markers:
  - `STAGING_VALIDATE:CONFIG_OK`
  - `STAGING_VALIDATE:UP_OK`
  - `STAGING_VALIDATE:HEALTH_OK`
  - `STAGING_VALIDATE:LOGS_OK`
  - `STAGING_VALIDATE:PERSISTENCE_PROBE_OK`
  - `STAGING_VALIDATE:RESTART_OK`
  - `STAGING_VALIDATE:POST_RESTART_HEALTH_OK`
  - `STAGING_VALIDATE:POST_RESTART_LOGS_OK`
  - `STAGING_VALIDATE:PERSISTENCE_OK`
  - `STAGING_VALIDATE:DOWN_OK`
  - `STAGING_VALIDATE:SUCCESS`

### 5) Paper and Workflow Inspection Surfaces (Read-Only)
- `GET /paper/workflow` verified with `validation.ok=true`.
- `GET /paper/reconciliation` verified with `ok=true` and `mismatches=0`.
- `GET /paper/account` verified.
- `GET /paper/trades` verified.
- `GET /paper/positions` verified.
- `GET /trading-core/orders` verified.
- `GET /trading-core/execution-events` verified.
- `GET /trading-core/trades` verified.
- `GET /trading-core/positions` verified.
- All inspected surfaces were in an empty initial state and remained consistent
  for bounded read-only inspection.

### 6) Persistence Paths
- Database file verified present at `/srv/cilly/staging/db/cilly_trading.db`.
- Staging directories verified present for:
  - `db`
  - `artifacts`
  - `journal`
  - `logs`
  - `runtime-state`

## Current Boundary Status
- bounded staging deployment validated
- bounded paper inspection surfaces validated in empty-state/read-only form
- final paper-install-ready evidence capture still pending

## Not Completed Yet
The following bounded staging P53 evidence automation commands were not fully executed in this session:
- `docker compose --env-file .env -f docker/staging/docker-compose.staging.yml exec api python /app/scripts/run_post_run_reconciliation.py --db-path /data/db/cilly_trading.db --evidence-dir /data/artifacts/reconciliation`
- `docker compose --env-file .env -f docker/staging/docker-compose.staging.yml exec api python /app/scripts/generate_weekly_review.py --db-path /data/db/cilly_trading.db --evidence-dir /data/artifacts/weekly-review`
- `docker compose --env-file .env -f docker/staging/docker-compose.staging.yml exec api python /app/scripts/capture_restart_evidence.py --phase pre-restart --db-path /data/db/cilly_trading.db --evidence-dir /data/artifacts/restart-evidence`
- `docker compose --env-file .env -f docker/staging/docker-compose.staging.yml exec api python /app/scripts/capture_restart_evidence.py --phase post-restart --db-path /data/db/cilly_trading.db --evidence-dir /data/artifacts/restart-evidence --baseline /data/artifacts/restart-evidence/pre-restart-pass-YYYYMMDDTHHMMSSZ.json`

Therefore, the formal full paper-install-ready checklist remains incomplete as
of 2026-04-03.

## Next Operator Step (Next Session)
Execute the pending P53 evidence capture commands above, then complete
`docs/operations/runtime/paper-deployment-operator-checklist.md` with concrete
evidence references before any paper-install-ready claim.
