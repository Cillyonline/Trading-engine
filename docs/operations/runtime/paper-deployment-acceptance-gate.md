# Paper Deployment Acceptance Gate (Staging -> Paper-Install-Ready)

## Purpose
Define the explicit, bounded acceptance gate that separates:
- `repository-runs-locally`, and
- `server-ready (staging) + paper-install-ready (non-live)`.

The gate is binary and evidence-oriented. A deployment is either accepted or not
accepted based on explicit required outputs.

## Scope
In scope:
- bounded server acceptance gate definition
- exact validation sequence for staging server readiness
- required evidence outputs for acceptance
- explicit pass/fail criteria
- wording alignment with deployment documentation
- bounded operator trust model and exposure wording for staging paper operation

Out of scope:
- live-trading approval
- broker integrations
- strategy redesign
- broad runtime redesign

## Readiness States and Boundary
- `repository-runs-locally`: local commands and tests can be executed.
- `server-ready (staging)`: canonical staging deployment validation succeeds.
- `paper-install-ready`: server-ready plus bounded paper evidence gate passes.

Boundary rule:
- Local run success alone must never be interpreted as server-ready.
- Server-ready alone must never be interpreted as paper-install-ready.
- Paper-install-ready requires all steps in the acceptance sequence below.

## Operator Access and Exposure Boundary
- Localhost-only is the default staging paper access posture.
- `X-Cilly-Role` headers are bounded trust inputs for local/operator-controlled
  staging use and are not a public authentication model.
- Remote access is outside default staging scope and must be treated as an
  operator-owned trust-boundary decision or unsupported.
- Public exposure without an external trust boundary is not allowed.

## Bounded Acceptance Sequence (Canonical and Reproducible)
Run steps in order from repository root.

### Step 1 - Staging deployment validation
Command:
- `python scripts/validate_staging_deployment.py`

Required output markers:
- `STAGING_VALIDATE:CONFIG_OK`
- `STAGING_VALIDATE:UP_OK`
- `STAGING_VALIDATE:HEALTH_OK`
- `STAGING_VALIDATE:RESTART_OK`
- `STAGING_VALIDATE:POST_RESTART_HEALTH_OK`
- `STAGING_VALIDATE:SUCCESS`

Evidence output name:
- `EVIDENCE_STAGING_VALIDATION_LOG`

### Step 2 - Explicit health/readiness evidence capture
Commands:
- `curl -sS -H "X-Cilly-Role: read_only" http://127.0.0.1:18000/health/engine`
- `curl -sS -H "X-Cilly-Role: read_only" http://127.0.0.1:18000/health/data`
- `curl -sS -H "X-Cilly-Role: read_only" http://127.0.0.1:18000/health/guards`

Required response conditions:
- `/health/engine` -> `ready: true`
- `/health/data` -> `ready: true`
- `/health/guards` -> `ready: true` and allowing decision

Evidence output name:
- `EVIDENCE_STAGING_HEALTH_SNAPSHOTS`

### Step 3 - Paper consistency contract tests
Command:
- `python -m pytest tests/test_paper_trading_simulator.py tests/test_api_paper_inspection_read.py`

Required result:
- all selected tests pass

Evidence output name:
- `EVIDENCE_PAPER_CONSISTENCY_TEST_OUTPUT`

### Step 4 - Full repository regression gate
Command:
- `python -m pytest`

Required result:
- full suite passes

Evidence output name:
- `EVIDENCE_FULL_PYTEST_OUTPUT`

### Step 5 - Operator checklist completion
Document:
- `docs/operations/runtime/paper-deployment-operator-checklist.md`

Required result:
- every checklist item is `YES`

Evidence output name:
- `EVIDENCE_COMPLETED_OPERATOR_CHECKLIST`

## Required Evidence Outputs (Exact Set)
The gate review package is complete only when all outputs below exist:
1. `EVIDENCE_STAGING_VALIDATION_LOG`
2. `EVIDENCE_STAGING_HEALTH_SNAPSHOTS`
3. `EVIDENCE_PAPER_CONSISTENCY_TEST_OUTPUT`
4. `EVIDENCE_FULL_PYTEST_OUTPUT`
5. `EVIDENCE_COMPLETED_OPERATOR_CHECKLIST`

## Pass/Fail Criteria (Binary)
PASS (`ACCEPTED: PAPER_INSTALL_READY`) requires all conditions:
- every sequence step executed in order
- every required marker/condition satisfied
- every required evidence output present
- checklist contains only `YES`

FAIL (`NOT ACCEPTED: REMAIN STAGING`) if any condition is true:
- any sequence step skipped
- any required marker missing
- any command exits non-zero
- any evidence output missing
- any checklist item is `NO` or blank

## Wording Alignment Contract
This acceptance gate and deployment runbook use the same boundary terms:
- `server-ready (staging)` = deployment and health validation passed
- `paper-install-ready` = server-ready plus this full acceptance gate passed

Deployment reference:
- `docs/operations/runtime/staging-server-deployment.md`

## Explicit Non-Goals Relative to Live Trading
Passing this gate does not imply:
- live-trading readiness
- broker connectivity approval
- capital-at-risk authorization
- production incident/SRE maturity for live execution
