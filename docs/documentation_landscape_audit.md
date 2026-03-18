# Documentation Landscape Audit

## Scope

Issue: `#683`  
Goal: create a complete inventory of in-scope documentation and identify duplication, inconsistencies, and unclear ownership without editing existing documents.

In-scope files reviewed:

- `README.md`
- every file under `docs/`

Inventory totals:

- 128 in-scope documentation files
- 127 Markdown files
- 1 non-Markdown documentation asset: `docs/strategy_packs/reference_pack/metadata.yaml`

## Purpose Taxonomy

Each file below is assigned one primary purpose so the inventory is unambiguous.
Assignments are closest-fit labels, not exclusivity claims.

- `setup`: onboarding, local install, first-run navigation
- `runtime`: operator workflows, API/CLI/UI usage, live local-operation references
- `testing`: smoke runs, determinism, snapshots, backtesting contracts, verification guidance
- `architecture`: design boundaries, governance, roadmap, versioning, repository structure, audits
- `strategy/config`: strategy lifecycle, packs, registry, validation, risk/config contracts

## Inventory

### Setup

- `README.md`
- `docs/GETTING_STARTED.md`
- `docs/index.md`
- `docs/local_run.md`
- `docs/OWNER_RUNBOOK.md`
- `docs/quickstart.md`
- `docs/repo-snapshot.md`

### Runtime

- `docs/access-policy.md`
- `docs/access-smoke-check.md`
- `docs/analyst-workflow.md`
- `docs/api/alerts.md`
- `docs/api/api_guarantees.md`
- `docs/api/external_api_happy_path.md`
- `docs/api/public_api_boundary.md`
- `docs/api/runtime_chart_data_contract.md`
- `docs/api/usage.md`
- `docs/api/usage_contract.md`
- `docs/api/usage_examples.md`
- `docs/api_cookbook.md`
- `docs/cli/usage.md`
- `docs/deterministic-analysis.md`
- `docs/engine/runtime-ownership.md`
- `docs/exploration/exploration-guide.md`
- `docs/external/change_policy.md`
- `docs/external/client_types.md`
- `docs/external/contract_surface.md`
- `docs/external/error_semantics.md`
- `docs/external/integration_assumptions.md`
- `docs/health.md`
- `docs/interfaces/batch_execution.md`
- `docs/interfaces/cli_contract.md`
- `docs/interfaces/usage_patterns.md`
- `docs/paper_trading.md`
- `docs/phase-13/runtime-observability-scope.md`
- `docs/phase-14/runtime-observability-extension-points.md`
- `docs/phase-6/PHASE_6_OPERATIONAL_OVERVIEW.md`
- `docs/phases/phase-18-status.md`
- `docs/phases/phase-23-status.md`
- `docs/phases/phase-37-issue-01-watchlist-persistence.md`
- `docs/phases/phase-37-issue-02-watchlist-crud-api.md`
- `docs/phases/phase-37-issue-03-watchlist-execution-ranking.md`
- `docs/phases/phase-37-issue-04-runtime-ui-watchlists.md`
- `docs/phases/phase-37-issue-05-phase-37-doc-alignment.md`
- `docs/phases/phase-37-status.md`
- `docs/phases/phase-37-watchlist-engine-milestones.md`
- `docs/phases/phase-37-watchlist-engine-package.md`
- `docs/phases/phase-41-alerts.md`
- `docs/release/checklist.md`
- `docs/RUNBOOK.md`
- `docs/runtime/snapshot_runtime.md`
- `docs/runtime_extension_model.md`
- `docs/runtime_status_and_health.md`
- `docs/standards/breaking-change-regeln.md`
- `docs/ui/owner_dashboard.md`
- `docs/ui/phase-36-web-activation-contract.md`
- `docs/ui/phase-39-charting-contract.md`
- `docs/ui/phase-39-test-plan.md`

### Testing

- `docs/backtesting/backtest_cli.md`
- `docs/backtesting/evaluate_cli.md`
- `docs/backtesting/execution_contract.md`
- `docs/backtesting/metrics.md`
- `docs/backtesting/metrics_contract.md`
- `docs/backtesting/order_execution_model.md`
- `docs/backtesting/README.md`
- `docs/backtesting/result_artifact_schema.md`
- `docs/checklists/phase-6-exit-checklist.md`
- `docs/determinism_audit.md`
- `docs/fixtures.md`
- `docs/maintenance/ci_determinism.md`
- `docs/numeric_output_precision.md`
- `docs/smoke-run.md`
- `docs/snapshot-testing.md`
- `docs/testing.md`
- `docs/testing/determinism.md`

### Architecture

- `docs/architecture/compliance_safety_layer.md`
- `docs/architecture/configuration_boundary.md`
- `docs/architecture/engine_runtime_lifecycle_contract.md`
- `docs/architecture/non_core_directory_audit.md`
- `docs/architecture/phase6_snapshot_contract.md`
- `docs/architecture/pipeline_enforcement.md`
- `docs/architecture/repository_root_structure.md`
- `docs/architecture/risk_framework.md`
- `docs/audit/roadmap_compliance_report.md`
- `docs/governance/execution-modes.md`
- `docs/governance/explicit-test-gated-execution-mode.md`
- `docs/governance/external-readiness-checklist.md`
- `docs/governance/phase-5-exit-criteria.md`
- `docs/governance/pr-review-checklist-test-gated.md`
- `docs/governance/stop-conditions-and-merge-authority.md`
- `docs/maintenance/branch_protection.md`
- `docs/maintenance/dependencies.md`
- `docs/maintenance/security.md`
- `docs/MVP_SPEC.md`
- `docs/mvp_v1.md`
- `docs/P9_A1_repo_inventory.md`
- `docs/phase-11-kickoff.md`
- `docs/phase-12-runtime-integration-scope.md`
- `docs/phase-6-exit-criteria.md`
- `docs/phase-9-exit.md`
- `docs/phases/phase-27-status.md`
- `docs/phases/phase_27_risk_framework.md`
- `docs/phases/phase_27b_pipeline_enforcement.md`
- `docs/repo-hygiene-audit.md`
- `docs/reports/I-029a_implicit_time_inventory.md`
- `docs/reports/repo_audit_DISC-4_C2.md`
- `docs/roadmap/cilly_trading_execution_roadmap_updated.md`
- `docs/roadmap/execution_roadmap.md`
- `docs/roadmap/phase-36-web-activation-evidence.md`
- `docs/versioning/change_enforcement.md`
- `docs/versioning/compatibility_gate.md`
- `docs/versioning/declaration.md`
- `docs/versioning/model.md`
- `docs/versioning/release_boundary.md`
- `docs/versioning/scope.md`

### Strategy/Config

- `docs/phases/phase_25_strategy_lifecycle.md`
- `docs/risk/contract.md`
- `docs/risk/journal_framework.md`
- `docs/risk/portfolio_framework.md`
- `docs/risk/risk_framework.md`
- `docs/strategy/documentation_standard.md`
- `docs/strategy/governance.md`
- `docs/strategy/pack_model.md`
- `docs/strategy/registry.md`
- `docs/strategy/validation.md`
- `docs/strategy_lifecycle_model.md`
- `docs/strategy_packs/reference_pack/metadata.yaml`
- `docs/strategy_packs/reference_pack/README.md`
- `docs/strategy-configs.md`

## Duplicate Content

### 1. Local setup and run instructions are duplicated across multiple entrypoints

Primary overlap set:

- `README.md`
- `docs/quickstart.md`
- `docs/local_run.md`
- `docs/GETTING_STARTED.md`
- `docs/OWNER_RUNBOOK.md`

Observed duplication:

- virtual environment creation
- dependency installation
- `PYTHONPATH=src` startup flow
- `/health` verification
- stop/reset guidance

Impact:

- there is no single clearly maintained onboarding/run document
- setup fixes must be propagated manually across at least five files

### 2. Test-entry guidance is split across multiple docs with overlapping scopes

Primary overlap set:

- `README.md`
- `docs/testing.md`
- `docs/RUNBOOK.md`
- `docs/smoke-run.md`
- `docs/testing/determinism.md`
- `docs/snapshot-testing.md`
- `docs/maintenance/ci_determinism.md`

Observed duplication:

- test command entrypoints
- determinism expectations
- smoke-run contract references
- quality-gate wording

Impact:

- readers have to infer which document is the canonical test entrypoint versus a narrow contract or policy doc

### 3. API example docs include explicit moved/redirect duplicates

Primary overlap set:

- `docs/api_cookbook.md`
- `docs/api/external_api_happy_path.md`
- `docs/api/usage_examples.md`

Observed duplication:

- the first two files are retained redirect stubs that point to the third file

Impact:

- inventory/navigation noise remains even though the content owner effectively moved to `docs/api/usage_examples.md`

### 4. Runtime health/status concepts are duplicated across two partially overlapping documents

Primary overlap set:

- `docs/health.md`
- `docs/runtime_status_and_health.md`

Observed duplication:

- both describe runtime state/health semantics
- both present payload-level expectations
- only one makes the `/health` endpoint contract explicit

Impact:

- readers can treat both as authoritative for runtime health even though they describe different shapes and scopes

### 5. Strategy lifecycle facts are repeated in both a model document and a phase-status document

Primary overlap set:

- `docs/strategy_lifecycle_model.md`
- `docs/phases/phase_25_strategy_lifecycle.md`

Observed duplication:

- state list
- allowed transitions
- production-only execution eligibility/enforcement framing

Impact:

- core lifecycle rules are repeated in multiple places rather than referenced from one source

### 6. Risk framework description is split across multiple architecture/status surfaces

Primary overlap set:

- `docs/architecture/risk_framework.md`
- `docs/risk/risk_framework.md`
- `docs/phases/phase-27-status.md`
- `docs/phases/phase_27_risk_framework.md`

Observed duplication:

- purpose/boundary statements
- deterministic risk-evaluation framing
- execution-gating language

Impact:

- the risk boundary exists in several near-adjacent forms, which increases the chance of future drift

### 7. Roadmap and phase-status navigation is heavily duplicated by design

Primary overlap set:

- `docs/index.md`
- `docs/roadmap/execution_roadmap.md`
- `docs/roadmap/cilly_trading_execution_roadmap_updated.md`
- `docs/audit/roadmap_compliance_report.md`
- `docs/phases/*.md`

Observed duplication:

- phase meaning summaries
- phase maturity/status statements
- repeated “authoritative vs derived” explanations

Impact:

- the docs try to control the duplication by repeatedly deferring to the roadmap, but the overall landscape is still high-friction to maintain

## Conflicting Instructions or Inconsistent Signals

### 1. `docs/OWNER_RUNBOOK.md` conflicts with the current canonical install path

Conflict:

- `docs/OWNER_RUNBOOK.md` instructs `pip install -r requirements.txt`
- `docs/quickstart.md`, `docs/local_run.md`, and `docs/GETTING_STARTED.md` instruct `python -m pip install -e ".[test]"`
- repository review shows no `requirements.txt` at the root

Why it matters:

- this is an actionable setup conflict, not only a wording difference
- a reader following `docs/OWNER_RUNBOOK.md` exactly will hit a missing-file path

### 2. Runtime health payload expectations are inconsistent

Conflict:

- `docs/health.md` defines `GET /health` as a read-only endpoint with payload keys `status`, `mode`, `reason`, and `checked_at`
- `docs/runtime_status_and_health.md` presents health/status examples using different fields such as `engine_id`, `runtime_state`, `level`, `summary`, and `checks`

Why it matters:

- the relationship between endpoint contract and explanatory examples is not made explicit
- a reader can reasonably misread both documents as describing the same runtime response surface

### 3. Shell/platform guidance is inconsistent across setup/runtime docs

Conflict:

- `docs/quickstart.md`, `docs/local_run.md`, and `docs/GETTING_STARTED.md` provide PowerShell and Bash paths
- `docs/OWNER_RUNBOOK.md` is Bash-only
- `docs/api/usage_examples.md` presents Windows-style activation syntax inside a Bash fenced block

Why it matters:

- the repository README explicitly points Windows users to these operator docs
- inconsistent shell targeting weakens the claim that there is one canonical local run path for both PowerShell and Bash

### 4. “Canonical” ownership signals are diffuse in roadmap/runtime clusters

Conflict:

- multiple docs declare themselves canonical or authoritative for adjacent concerns
- examples include `README.md`, `docs/local_run.md`, `docs/roadmap/execution_roadmap.md`, `docs/roadmap/cilly_trading_execution_roadmap_updated.md`, `docs/ui/phase-36-web-activation-contract.md`, and `docs/ui/phase-39-charting-contract.md`

Why it matters:

- the wording is often internally careful, but the aggregate effect is still ambiguous for a new reader deciding which document actually owns a given topic

## Unclear Ownership

### Repository-wide metadata gap

Only two in-scope documents explicitly declare an `Owner:` field during review:

- `docs/roadmap/execution_roadmap.md`
- `docs/phases/phase-37-status.md`

Most other documents do not identify a named steward, team, or maintenance owner.

### Highest-risk ownership gaps

#### 1. Onboarding and local-run cluster

Files:

- `README.md`
- `docs/quickstart.md`
- `docs/local_run.md`
- `docs/GETTING_STARTED.md`
- `docs/OWNER_RUNBOOK.md`

Why ownership is unclear:

- all five act like entrypoints
- none names a maintainer
- at least one file has already drifted from the currently used install path

#### 2. Test and determinism cluster

Files:

- `docs/testing.md`
- `docs/RUNBOOK.md`
- `docs/smoke-run.md`
- `docs/testing/determinism.md`
- `docs/snapshot-testing.md`
- `docs/maintenance/ci_determinism.md`

Why ownership is unclear:

- operational testing guidance, deterministic contracts, and CI policy are spread across multiple areas
- no single document declares itself the maintained test-entry owner for contributors

#### 3. Roadmap, phase, and audit cluster

Files:

- `docs/index.md`
- `docs/roadmap/execution_roadmap.md`
- `docs/roadmap/cilly_trading_execution_roadmap_updated.md`
- `docs/audit/roadmap_compliance_report.md`
- `docs/phases/*.md`

Why ownership is unclear:

- this cluster contains the most explicit “authoritative” wording
- despite that, responsibility is fragmented across roadmap, phase, index, and audit files

#### 4. Strategy/config and risk cluster

Files:

- `docs/strategy-configs.md`
- `docs/architecture/configuration_boundary.md`
- `docs/strategy/*.md`
- `docs/risk/*.md`
- `docs/phases/phase_25_strategy_lifecycle.md`
- `docs/phases/phase-27-status.md`

Why ownership is unclear:

- architecture, lifecycle, registry, validation, and risk boundary docs are all present
- none of the cluster documents clearly names the owner of strategy/configuration documentation as a maintained surface

## Summary Findings

- The documentation inventory is complete for the requested scope: 128 files.
- The largest duplication cluster is local setup/runtime onboarding.
- The clearest hard conflict is `docs/OWNER_RUNBOOK.md` still pointing to `requirements.txt` while the rest of the active setup docs use the `pyproject.toml` editable install path.
- Runtime health semantics are not cleanly separated between endpoint contract and explanatory health/status narrative.
- Ownership metadata is largely absent, which makes future consolidation risky because drift cannot be assigned cleanly.

## Recommended Consolidation Priorities

These are audit priorities only, not change proposals for this issue.

1. Resolve the setup/runtime entrypoint cluster first.
2. Assign explicit stewardship for onboarding, testing, roadmap/status, and strategy/config docs.
3. Separate endpoint contracts from narrative/explainer docs where both currently describe “health” or “status”.
4. Decide which roadmap/status surfaces are canonical and which are navigation-only derivatives.
