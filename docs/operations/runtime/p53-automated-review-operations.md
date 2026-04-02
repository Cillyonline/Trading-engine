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

### Post-Run Reconciliation

```bash
python scripts/run_post_run_reconciliation.py
python scripts/run_post_run_reconciliation.py --db-path /path/to/cilly_trading.db
python scripts/run_post_run_reconciliation.py --evidence-dir runs/reconciliation
```

Runs after each execution cycle. Loads canonical entities from the SQLite execution repository, derives positions and account state, validates cross-entity and account-equation consistency, and writes a timestamped evidence JSON file.

Evidence output directory: `runs/reconciliation/`

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
python scripts/generate_weekly_review.py
python scripts/generate_weekly_review.py --db-path /path/to/cilly_trading.db
python scripts/generate_weekly_review.py --evidence-dir runs/weekly-review
```

Produces a deterministic weekly review evidence bundle containing the R1–R7 artifacts defined in the Phase 44 operator workflow. Each artifact is captured by reading canonical state and applying the same derivation logic used by the paper inspection API.

Evidence output directory: `runs/weekly-review/`

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
python scripts/capture_restart_evidence.py --phase pre-restart

# Post-restart verification
python scripts/capture_restart_evidence.py --phase post-restart

# Post-restart with baseline comparison
python scripts/capture_restart_evidence.py --phase post-restart --baseline runs/restart-evidence/pre-restart-pass-*.json
```

Captures a deterministic evidence snapshot before or after a process restart. When a baseline file is provided, compares entity counts and reconciliation state to verify restart integrity.

Evidence output directory: `runs/restart-evidence/`

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

## Singular State Authority

All automation scripts derive state exclusively from `SqliteCanonicalExecutionRepository`. No alternative state source, in-memory cache, or legacy table is used. The formal contract is defined in `src/cilly_trading/portfolio/paper_state_authority.py`.
