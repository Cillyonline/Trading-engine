# Issue #1192 Bounded Runtime Analysis Trigger Review Data

## SUMMARY

Implemented the bounded daily runtime analysis trigger fix for issue #1192. The runtime script now resolves its default SQLite database path from `CILLY_DB_PATH` when that environment variable is set, matching the staging API container's configured persistent database path. This prevents snapshot ingestion from writing the new ingestion run to the repository-local fallback database while `/analysis/run` validates against the API's configured database.

## REPOSITORY VERIFICATION

Command sequence run before implementation:

```text
git remote -v
git branch --show-current
git rev-parse HEAD
git status --short
git fetch origin
git checkout main
git pull --ff-only origin main
git remote -v
git branch --show-current
git rev-parse HEAD
git status --short
git ls-tree -r HEAD --name-only | Select-String -Pattern 'scripts/run_daily_bounded_paper_runtime.py|tests/test_run_daily_bounded_paper_runtime_script.py|src/api/routers/analysis_router.py'
```

Output:

```text
origin	https://github.com/Cillyonline/Trading-engine.git (fetch)
origin	https://github.com/Cillyonline/Trading-engine.git (push)
codex/issue-1190-exit-signal-consumption
00ad856dd9e7dada99c9416501148429a129a94b
?? issue-1192-body.md
?? issue-paper-runtime-exit-signal-consumption.md
Your branch is behind 'origin/main' by 1 commit, and can be fast-forwarded.
  (use "git pull" to update your local branch)
Updating 3b25c7c..2cf1f2c
Fast-forward
 .../runtime/p60-signal-to-paper-operator-path.md   |  40 ++++-
 ...sue-1190-exit-signal-consumption-review-data.md | 183 +++++++++++++++++++++
 scripts/run_paper_execution_cycle.py               |   2 +-
 src/cilly_trading/engine/paper_execution_worker.py |  44 ++++-
 tests/engine/test_paper_execution_worker.py        | 117 +++++++++++++
 tests/test_run_paper_execution_cycle_script.py     |  66 ++++++++
 6 files changed, 436 insertions(+), 16 deletions(-)
 create mode 100644 docs/reviews/issue-1190-exit-signal-consumption-review-data.md
origin	https://github.com/Cillyonline/Trading-engine.git (fetch)
origin	https://github.com/Cillyonline/Trading-engine.git (push)
main
2cf1f2cc13050bc1ed2ba01c1d44e7482a374b95
?? issue-1192-body.md
?? issue-paper-runtime-exit-signal-consumption.md

scripts/run_daily_bounded_paper_runtime.py
src/api/routers/analysis_router.py
tests/test_run_daily_bounded_paper_runtime_script.py

From https://github.com/Cillyonline/Trading-engine
   3b25c7c..2cf1f2c  main       -> origin/main
Switched to branch 'main'
From https://github.com/Cillyonline/Trading-engine
 * branch            main       -> FETCH_HEAD
```

## ROOT CAUSE

`scripts/run_daily_bounded_paper_runtime.py` defaulted `--db-path` to the repository-local `cilly_trading.db`. In the staging API container, the API database contract is `CILLY_DB_PATH=/data/db/cilly_trading.db`. The daily runtime script passed its default DB path explicitly into `run_snapshot_ingestion.py`, so snapshot ingestion could create a valid ingestion run in the fallback database while the running API validated `/analysis/run` against the API database. The current `/analysis/run` service validates the referenced ingestion run and snapshot readiness; when the ingestion run is absent from the API database, it raises the domain `ValidationError`, mapped to HTTP 422.

The JSON request fields themselves match `ManualAnalysisRequest`: `ingestion_run_id`, `symbol`, `strategy`, `market_type`, and `lookback_days`.

## ACCEPTANCE CRITERIA TRACE

- Correct repository and branch verified: satisfied by the verification output above.
- Root cause explicitly identified: DB path mismatch between script default and API runtime database.
- Runtime script sends a valid `/analysis/run` request: covered by `test_daily_runner_sends_current_manual_analysis_contract_and_reaches_execution`, which validates the payload with `ManualAnalysisRequest`.
- Deterministic tests added: added DB-path env and request-contract tests.
- Runtime can proceed past `analysis_signal_generation`: covered by controlled test that reaches `bounded_paper_execution_cycle`.
- #1190 exit-stage routing behavior preserved: no paper execution worker or paper execution cycle routing code changed; existing runtime script tests still pass.
- No strategy/risk/live/broker/paper-state cleanup scope introduced: only runtime script, runtime script tests, and this review artifact changed.

## TECHNICALLY IMPLEMENTED

- Added `DEFAULT_DB_PATH_ENV_VAR = "CILLY_DB_PATH"` to the daily runtime script.
- Added `_default_db_path()` to resolve `CILLY_DB_PATH` at argument-parse time.
- Updated `--db-path` default help text to document the environment-backed default.
- Added deterministic tests for `CILLY_DB_PATH` default resolution and current `/analysis/run` request-model compatibility.

## OPERATIONALLY USABLE

Yes. In the staging API container, running the script without `--db-path` now defaults to the same DB path configured for the API when `CILLY_DB_PATH` is set. Operators may still override `--db-path` explicitly when needed.

## TRADERICALLY VALIDATED

No. This change is technical runtime/API plumbing only. It is not trader validation, not profitability evidence, and not broker/live/production readiness evidence.

## MODIFIED FILES

- `scripts/run_daily_bounded_paper_runtime.py`
- `tests/test_run_daily_bounded_paper_runtime_script.py`

## NEW FILES

- `docs/reviews/issue-1192-bounded-runtime-analysis-trigger-review-data.md`

## DELETED FILES

- None

## TEST COMMAND

```text
python -m pytest tests/test_run_daily_bounded_paper_runtime_script.py
```

## FULL TEST OUTPUT

```text
============================= test session starts =============================
platform win32 -- Python 3.13.2, pytest-8.4.1, pluggy-1.6.0
rootdir: C:\repos\Trading-engine
configfile: pytest.ini
plugins: anyio-4.9.0
collected 36 items

tests\test_run_daily_bounded_paper_runtime_script.py ................... [ 52%]
.................                                                        [100%]

============================= 36 passed in 15.17s =============================
```

## RISK NOTES

- This change only affects the default DB path for the daily runtime script. Explicit `--db-path` behavior is unchanged.
- Existing direct script defaults in other scripts were not changed because issue #1192 scope is the bounded daily runtime orchestration path.
- The default `--base-url` remains unchanged because the issue's required fix targets the post-base-url 422 blocker; the script still supports explicit `--base-url`.

## OUT OF SCOPE

- #1060 resume.
- Manual paper-state cleanup.
- Closing, resetting, or mutating COST, GS, or WMT.
- RSI2 or TURTLE strategy logic changes.
- Score, threshold, calibration, risk-default, broker/live, production/VPS paper-state changes.
- Trader validation, profitability claims, broker readiness, live readiness, or production readiness.

## FOLLOW-UP ISSUES

- None opened.
