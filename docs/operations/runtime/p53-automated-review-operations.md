# P53 Automated Review Operations

## Purpose

Automate the bounded long-run paper review workflow so that reconciliation, weekly evaluation artifacts, and restart/recovery evidence are captured deterministically without manual assembly.

This document defines the automation scripts, evidence outputs, and integration with the Phase 44 operator workflow.

## Scope Boundary

In scope:
- Post-run reconciliation automation
- Weekly review artifact generation (R1–R7)
- Restart/recovery evidence capture
- Deterministic evidence output files

Out of scope:
- Public dashboards
- Live trading
- Unrelated decision-layer work
- Broad analytics platform expansion

## Automated Scripts

### Authoritative Bounded Staging Execution Path

For bounded staging server operation, the authoritative execution path is to run
the scripts inside the staging runtime container:

`docker compose --env-file .env -f docker/staging/docker-compose.staging.yml exec api ...`

Use runtime paths:
- DB path: `/data/db/cilly_trading.db`
- Evidence output base: `/data/artifacts`

This avoids host Python dependency drift and uses the packaged runtime
dependencies and packaged script files at `/app/scripts`.

### Post-Run Reconciliation

```bash
docker compose --env-file .env -f docker/staging/docker-compose.staging.yml exec api \
  python /app/scripts/run_post_run_reconciliation.py \
  --db-path /data/db/cilly_trading.db \
  --evidence-dir /data/artifacts/reconciliation
```

Runs after each execution cycle. Loads canonical entities from the SQLite execution repository, derives positions and account state, validates cross-entity and account-equation consistency, and writes a timestamped evidence JSON file.

Evidence output directory (bounded staging runtime): `/data/artifacts/reconciliation`

Local repository default output (non-staging usage): `runs/reconciliation/`

Evidence markers:
- `RECONCILIATION:PASS` — zero mismatches, reconciliation clean
- `RECONCILIATION:FAIL` — mismatches detected
- `RECONCILIATION:ERROR:<ExceptionType>` — runtime error prevented completion

Exit codes:
- `0` — reconciliation passed
- `1` — reconciliation failed (mismatches)
- `2` — runtime error

### Weekly Review Artifact Generation

```bash
docker compose --env-file .env -f docker/staging/docker-compose.staging.yml exec api \
  python /app/scripts/generate_weekly_review.py \
  --db-path /data/db/cilly_trading.db \
  --evidence-dir /data/artifacts/weekly-review
```

Produces a deterministic weekly review evidence bundle containing the R1–R7 artifacts defined in the Phase 44 operator workflow. Each artifact is captured by reading canonical state and applying the same derivation logic used by the paper inspection API.

Evidence output directory (bounded staging runtime): `/data/artifacts/weekly-review`

Local repository default output (non-staging usage): `runs/weekly-review/`

Evidence markers:
- `WEEKLY_REVIEW:PASS` — all R1–R7 artifacts valid
- `WEEKLY_REVIEW:FAIL` — one or more artifacts failed validation
- `WEEKLY_REVIEW:ERROR:<ExceptionType>` — runtime error

Exit codes:
- `0` — all artifacts valid
- `1` — artifact validation failure
- `2` — runtime error

### Restart/Recovery Evidence Capture

```bash
# Pre-restart baseline
docker compose --env-file .env -f docker/staging/docker-compose.staging.yml exec api \
  python /app/scripts/capture_restart_evidence.py \
  --phase pre-restart \
  --db-path /data/db/cilly_trading.db \
  --evidence-dir /data/artifacts/restart-evidence

# Post-restart verification
docker compose --env-file .env -f docker/staging/docker-compose.staging.yml exec api \
  python /app/scripts/capture_restart_evidence.py \
  --phase post-restart \
  --db-path /data/db/cilly_trading.db \
  --evidence-dir /data/artifacts/restart-evidence \
  --baseline /data/artifacts/restart-evidence/pre-restart-pass-YYYYMMDDTHHMMSSZ.json
```

Captures a deterministic evidence snapshot before or after a process restart. When a baseline file is provided, compares entity counts and reconciliation state to verify restart integrity.

Evidence output directory (bounded staging runtime): `/data/artifacts/restart-evidence`

Local repository default output (non-staging usage): `runs/restart-evidence/`

Evidence markers:
- `RESTART_EVIDENCE:PRE_RESTART:PASS` — pre-restart baseline captured clean
- `RESTART_EVIDENCE:POST_RESTART:PASS` — post-restart verification passed
- `RESTART_EVIDENCE:POST_RESTART:FAIL` — post-restart verification failed

Exit codes:
- `0` — evidence captured and reconciliation passed
- `1` — evidence captured but reconciliation failed or baseline mismatch
- `2` — runtime error

## Evidence File Format

All evidence files are deterministic JSON with the following common fields:

```json
{
  "ran_at": "2026-01-15T10:30:00+00:00",
  "db_path": "/path/to/cilly_trading.db",
  "status": "pass",
  "evidence_file": "/path/to/evidence-file.json",
  "summary": {
    "orders": 0,
    "execution_events": 0,
    "trades": 0,
    "positions": 0,
    "open_trades": 0,
    "closed_trades": 0,
    "open_positions": 0,
    "mismatches": 0
  }
}
```

Evidence files are written to `runs/` subdirectories which are excluded from version control via `.gitignore`.

## Bounded Run-Evidence Interpretation and Review Rules

These rules apply after an active server-testing period is complete and evidence
comparison is being used for decision-support review. They do not change how
evidence is captured during the active run period.

Interpretation boundary:
- Treat evidence as bounded to the evaluated server run window only.
- Do not extrapolate bounded outcomes into production-readiness, broker-readiness,
  or live-trading claims.
- Use bounded evidence for decision support and follow-up prioritization only.
- Keep raw evidence markers (`PASS`, `FAIL`, `ERROR`) unchanged; apply the review
  semantics below on top of those markers.

### Daily Runtime Operator Action Boundary

When the daily bounded runtime summary is produced through OPS-P63 or OPS-P64,
record operator next-action semantics explicitly in the artifact with:

- `operator_action_contract_version`
- `operator_action_contract.action_category`
- `operator_action_contract.action_code`
- `operator_action_contract.action_summary`
- `operator_action_contract.escalation_boundary`

Bounded action categories for daily runtime use:

- `informational`: record bounded evidence and continue the next scheduled bounded run
- `review_required`: inspect bounded no-eligible evidence and confirm the outcome without retrying solely to force activity
- `retry_required`: correct a pre-execution failure and rerun only when bounded paper execution has not started
- `blocking`: stop continuation claims for the affected run and investigate before any rerun or staged-evaluation claim

Boundary reminder:

- these action categories are bounded operator guidance only
- they do not imply operational readiness
- they do not imply broker readiness
- they do not imply production readiness

### Decision-Support Review Semantics

Use one review classification per bounded review package:

| Review classification | Meaning | Minimum criteria |
| --- | --- | --- |
| `pass` | Bounded evidence supports continued staged evaluation with no unresolved defects in scope. | Required bounded checks pass, no reproducible defect observed, and no unresolved blocking note. |
| `pass-with-note` | Bounded evidence supports continued staged evaluation, but a non-blocking bounded caveat must be tracked. | Required bounded checks pass; caveat is documented with evidence path and owner; no currently reproducible defect that invalidates the run. |
| `fail` | Bounded evidence does not support continuation without corrective action. | Any required bounded check fails, evidence is insufficient/conflicting for the review decision, or a reproducible defect is observed. |

Classification boundary:
- `pass` and `pass-with-note` are bounded decision-support outcomes, not release
  or production decisions.
- `pass-with-note` must include a concrete note linked to exact evidence files.
- `fail` means corrective follow-up is required before claiming the reviewed run
  as decision-support complete.

### Follow-Up Issue Triggers for Reproducible Defects

Open or update a follow-up issue when any of the following occurs in bounded
server-run evidence:

1. The same defect is reproduced in two or more bounded runs with the same
   command path and comparable runtime inputs.
2. Any required evidence script reports `FAIL` because of a product/runtime
   defect (not operator environment setup failure).
3. A `pass-with-note` caveat repeats in two consecutive review windows without
   confirmed resolution.
4. Evidence is missing or conflicting such that the bounded review package must
   be classified as `fail`.

Minimum follow-up issue content:
- bounded defect statement and affected workflow step (`reconciliation`,
  `weekly-review`, or `restart-evidence`)
- exact evidence file paths and timestamps
- reproduction command(s) and runtime context
- observed result versus expected bounded result
- explicit non-goal reminder (no production/live-trading claim)

## Integration with Phase 44 Operator Workflow

The automation scripts implement the same logic defined in the Phase 44 operator workflow:

| Workflow Step | Automated Script |
| --- | --- |
| End-of-session reconciliation | `scripts/run_post_run_reconciliation.py` |
| Periodic weekly review (R1–R7) | `scripts/generate_weekly_review.py` |
| Pre-restart baseline capture | `scripts/capture_restart_evidence.py --phase pre-restart` |
| Post-restart recovery verification | `scripts/capture_restart_evidence.py --phase post-restart` |

All scripts use the same canonical state authority (`SqliteCanonicalExecutionRepository`) and derivation functions (`build_paper_account_state`, `build_paper_reconciliation_mismatches`, `build_trading_core_positions`) as the paper inspection API endpoints.

## Operator Checklist Integration

The automation evidence outputs map to the operator checklist sections:

| Checklist Item | Evidence Source |
| --- | --- |
| E1 — Long-run review workflow | `scripts/generate_weekly_review.py` R7 artifact |
| E2 — R1–R7 artifacts | `scripts/generate_weekly_review.py` full bundle |
| E3 — Strategy-change baseline | `scripts/capture_restart_evidence.py --phase pre-restart` |
| E4 — Post-restart verification | `scripts/capture_restart_evidence.py --phase post-restart` |

## OPS-P59 Verified Bounded Evidence-Cycle Status (2026-04-05)

Verified on the bounded staging server:
- authoritative container command path executed successfully:
  `docker compose --env-file .env -f docker/staging/docker-compose.staging.yml exec api ...`
- post-run reconciliation completed with `RECONCILIATION:PASS`
- weekly review completed with `WEEKLY_REVIEW:PASS` and `all_valid: true`
- pre-restart evidence completed with `RESTART_EVIDENCE:PRE_RESTART:PASS`
- post-restart evidence completed with `RESTART_EVIDENCE:POST_RESTART:PASS`
- restart baseline comparison completed with `baseline_match: true`

Verified persisted evidence locations:
- `/srv/cilly/staging/artifacts/reconciliation/...`
- `/srv/cilly/staging/artifacts/weekly-review/...`
- `/srv/cilly/staging/artifacts/restart-evidence/...`

Observed artifact file patterns:
- `reconciliation-pass-*.json`
- `weekly-review-pass-*.json`
- `pre-restart-pass-*.json`
- `post-restart-pass-*.json`

Boundary clarity:
- this status confirms bounded staging/paper evidence operations only
- no live-trading claim
- no broker-readiness claim
- no production-readiness claim

## Singular State Authority

All automation scripts derive state exclusively from `SqliteCanonicalExecutionRepository`. No alternative state source, in-memory cache, or legacy table is used. The formal contract is defined in `src/cilly_trading/portfolio/paper_state_authority.py`.
