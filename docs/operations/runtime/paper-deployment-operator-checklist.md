# Paper Deployment Operator Acceptance Checklist

## Instructions
1. Fill every item with `YES` or `NO`.
2. Provide concrete evidence references (command output, artifact path, run id).
3. If any item is `NO`, the deployment is not paper-operational.

## A) Staging Install Prerequisite

| # | Item | Evidence reference | Answer (YES/NO) |
| --- | --- | --- | --- |
| A1 | Staging deployment validation command completed: `python scripts/validate_staging_deployment.py` | | |
| A2 | Validation output includes `STAGING_VALIDATE:SUCCESS` | | |
| A3 | Restart validation passed and post-restart health remained ready | | |

## B) Backtesting Evidence

| # | Item | Evidence reference | Answer (YES/NO) |
| --- | --- | --- | --- |
| B1 | Backtest evidence set exists for the same strategy/config scope intended for paper usage | | |
| B2 | Evidence includes bounded run context (symbol/time window/config identity) | | |
| B3 | Repeated runs for identical inputs are reproducible without unexplained drift | | |
| B4 | No unresolved blocking risk findings remain for candidates entering paper operation | | |

## C) Decision-Card Behavior Evidence

| # | Item | Evidence reference | Answer (YES/NO) |
| --- | --- | --- | --- |
| C1 | Decision cards are available and reviewable for in-scope candidates | | |
| C2 | Blocking hard-gate failures resolve to `reject` per contract | | |
| C3 | Paper candidates use explicit qualification states (`paper_candidate` or `paper_approved`) | | |
| C4 | Rationale fields are present and complete (gate explanations, score explanations, final explanation) | | |

## D) Runtime Health Evidence

| # | Item | Evidence reference | Answer (YES/NO) |
| --- | --- | --- | --- |
| D1 | `/health/engine` shows `ready: true` | | |
| D2 | `/health/data` shows `ready: true` | | |
| D3 | `/health/guards` shows `ready: true` and allowing decision under bounded staging defaults | | |
| D4 | Runtime remained healthy after restart check | | |

## E) Paper-Trading Consistency Evidence

| # | Item | Evidence reference | Answer (YES/NO) |
| --- | --- | --- | --- |
| E1 | Paper-trading simulator behavior remains deterministic for repeated identical inputs | | |
| E2 | Paper-trading simulator tests pass (`tests/test_paper_trading_simulator.py`) | | |
| E3 | Paper inspection outputs align with canonical order/event/trade semantics | | |
| E4 | No live routing or broker side effects are present in the validated path | | |

## F) Repository Test Gate (Mandatory)

| # | Item | Evidence reference | Answer (YES/NO) |
| --- | --- | --- | --- |
| F1 | Full repository test suite passed with `python -m pytest` | | |

## Final Operator Decision
Decision rule:
- Any `NO` -> `NOT ACCEPTED` (status remains `staging`)
- All `YES` -> `ACCEPTED` (status may be declared `paper-operational`)

Final decision (`ACCEPTED` or `NOT ACCEPTED`):

Operator name:

Date (UTC):

