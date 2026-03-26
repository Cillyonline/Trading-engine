# Rollback Discipline

## 1. Purpose
Define an operationally usable rollback path for staged and GA releases.
Rollback is tag-based, auditable, and state-aware.

## 2. Rollback triggers
Start rollback when any of the following occurs after release:

- compatibility regression against declared contracts
- failed health/readiness checks
- high-severity runtime regression not resolved by bounded flag disablement

## 3. Required inputs before rollback
- current release tag
- last-known-good tag
- release state (`alpha`, `beta`, `rc`, or `ga`)
- rollback owner and decision timestamp

## 4. Rollback procedure

1. Freeze further promotion for the affected release.
2. Disable flagged capability gates first when regression is flag-scoped.
3. If issue persists, redeploy from last-known-good tag.
4. Run post-rollback verification checks.
5. Record rollback outcome and next action.

## 5. Post-rollback verification
Minimum required checks:

- version check:
  ```bash
  PYTHONPATH=src python -m cilly_trading --version
  ```

- smoke run:
  ```bash
  PYTHONPATH=src python -c 'from cilly_trading.smoke_run import run_smoke_run; raise SystemExit(run_smoke_run())'
  ```

- staging validation when server deployment is in scope:
  ```bash
  python scripts/validate_staging_deployment.py
  ```

## 6. Release-state rollback expectations
- `alpha`: rollback may target prior alpha, or nearest stable pre-release if needed.
- `beta`: rollback should target prior beta or a last-known-good rc/ga as approved.
- `rc`: rollback should target prior rc or last-known-good ga.
- `ga`: rollback target must be a prior ga tag unless emergency approval states otherwise.

## 7. Tag integrity rules
- Do not delete release tags.
- Do not move existing tags to new commits.
- Rollback always deploys an existing tag or a new corrective tag.

## 8. Recordkeeping
Each rollback record must include:

- incident reference (issue or incident ID)
- from-tag and to-tag
- rollback decision owner
- executed verification evidence
- follow-up fix plan