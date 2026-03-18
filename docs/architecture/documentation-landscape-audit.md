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
- 1 non-Markdown documentation asset: `docs/architecture/strategy_packs/reference_pack/metadata.yaml`

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
- `docs/getting-started/getting-started.md`
- `docs/index.md`
- `docs/getting-started/local-run.md`
- `docs/operations/owner-runbook.md`
- `docs/getting-started/quickstart.md`
- `docs/getting-started/repo-snapshot.md`

### Runtime

- `docs/operations/access-policy.md`
- `docs/operations/access-smoke-check.md`
- `docs/operations/analyst-workflow.md`
- `docs/operations/api/alerts.md`
- `docs/operations/api/api_guarantees.md`
- `docs/operations/api/external_api_happy_path.md`
- `docs/operations/api/public_api_boundary.md`
- `docs/operations/api/runtime_chart_data_contract.md`
- `docs/operations/api/usage.md`
- `docs/operations/api/usage_contract.md`
- `docs/operations/api/usage_examples.md`
- `docs/operations/api-cookbook.md`
- `docs/operations/cli/usage.md`
- `docs/operations/deterministic-analysis.md`
- `docs/operations/engine/runtime-ownership.md`
- `docs/operations/exploration/exploration-guide.md`
- `docs/operations/external/change_policy.md`
- `docs/operations/external/client_types.md`
- `docs/operations/external/contract_surface.md`
- `docs/operations/external/error_semantics.md`
- `docs/operations/external/integration_assumptions.md`
- `docs/operations/health.md`
- `docs/operations/interfaces/batch_execution.md`
- `docs/operations/interfaces/cli_contract.md`
- `docs/operations/interfaces/usage_patterns.md`
- `docs/operations/paper-trading.md`
- `docs/operations/phase-13/runtime-observability-scope.md`
- `docs/operations/phase-14/runtime-observability-extension-points.md`
- `docs/operations/phase-6/PHASE_6_OPERATIONAL_OVERVIEW.md`
- `docs/architecture/phases/phase-18-status.md`
- `docs/architecture/phases/phase-23-status.md`
- `docs/architecture/phases/phase-37-issue-01-watchlist-persistence.md`
- `docs/architecture/phases/phase-37-issue-02-watchlist-crud-api.md`
- `docs/architecture/phases/phase-37-issue-03-watchlist-execution-ranking.md`
- `docs/architecture/phases/phase-37-issue-04-runtime-ui-watchlists.md`
- `docs/architecture/phases/phase-37-issue-05-phase-37-doc-alignment.md`
- `docs/architecture/phases/phase-37-status.md`
- `docs/architecture/phases/phase-37-watchlist-engine-milestones.md`
- `docs/architecture/phases/phase-37-watchlist-engine-package.md`
- `docs/architecture/phases/phase-41-alerts.md`
- `docs/operations/release/checklist.md`
- `docs/operations/runbook.md`
- `docs/operations/runtime/snapshot_runtime.md`
- `docs/architecture/runtime-extension-model.md`
- `docs/operations/runtime-status-and-health.md`
- `docs/architecture/standards/breaking-change-regeln.md`
- `docs/operations/ui/owner_dashboard.md`
- `docs/operations/ui/phase-36-web-activation-contract.md`
- `docs/operations/ui/phase-39-charting-contract.md`
- `docs/operations/ui/phase-39-test-plan.md`

### Testing

- `docs/testing/backtesting/backtest_cli.md`
- `docs/testing/backtesting/evaluate_cli.md`
- `docs/testing/backtesting/execution_contract.md`
- `docs/testing/backtesting/metrics.md`
- `docs/testing/backtesting/metrics_contract.md`
- `docs/testing/backtesting/order_execution_model.md`
- `docs/testing/backtesting/README.md`
- `docs/testing/backtesting/result_artifact_schema.md`
- `docs/testing/checklists/phase-6-exit-checklist.md`
- `docs/testing/determinism-audit.md`
- `docs/testing/fixtures.md`
- `docs/architecture/maintenance/ci_determinism.md`
- `docs/testing/numeric-output-precision.md`
- `docs/testing/smoke-run.md`
- `docs/testing/snapshot-testing.md`
- `docs/testing/index.md`
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
- `docs/architecture/audit/roadmap_compliance_report.md`
- `docs/architecture/governance/execution-modes.md`
- `docs/architecture/governance/explicit-test-gated-execution-mode.md`
- `docs/architecture/governance/external-readiness-checklist.md`
- `docs/architecture/governance/phase-5-exit-criteria.md`
- `docs/architecture/governance/pr-review-checklist-test-gated.md`
- `docs/architecture/governance/stop-conditions-and-merge-authority.md`
- `docs/architecture/maintenance/branch_protection.md`
- `docs/architecture/maintenance/dependencies.md`
- `docs/architecture/maintenance/security.md`
- `docs/architecture/mvp-spec.md`
- `docs/architecture/mvp-v1.md`
- `docs/architecture/p9-a1-repo-inventory.md`
- `docs/architecture/phase-11-kickoff.md`
- `docs/architecture/phase-12-runtime-integration-scope.md`
- `docs/architecture/phase-6-exit-criteria.md`
- `docs/architecture/phase-9-exit.md`
- `docs/architecture/phases/phase-27-status.md`
- `docs/architecture/phases/phase_27_risk_framework.md`
- `docs/architecture/phases/phase_27b_pipeline_enforcement.md`
- `docs/architecture/repo-hygiene-audit.md`
- `docs/architecture/reports/I-029a_implicit_time_inventory.md`
- `docs/architecture/reports/repo_audit_DISC-4_C2.md`
- `docs/architecture/roadmap/cilly_trading_execution_roadmap_updated.md`
- `docs/architecture/roadmap/execution_roadmap.md`
- `docs/architecture/roadmap/phase-36-web-activation-evidence.md`
- `docs/architecture/versioning/change_enforcement.md`
- `docs/architecture/versioning/compatibility_gate.md`
- `docs/architecture/versioning/declaration.md`
- `docs/architecture/versioning/model.md`
- `docs/architecture/versioning/release_boundary.md`
- `docs/architecture/versioning/scope.md`

### Strategy/Config

- `docs/architecture/phases/phase_25_strategy_lifecycle.md`
- `docs/architecture/risk/contract.md`
- `docs/architecture/risk/journal_framework.md`
- `docs/architecture/risk/portfolio_framework.md`
- `docs/architecture/risk/risk_framework.md`
- `docs/architecture/strategy/documentation_standard.md`
- `docs/architecture/strategy/governance.md`
- `docs/architecture/strategy/pack_model.md`
- `docs/architecture/strategy/registry.md`
- `docs/architecture/strategy/validation.md`
- `docs/architecture/strategy-lifecycle-model.md`
- `docs/architecture/strategy_packs/reference_pack/metadata.yaml`
- `docs/architecture/strategy_packs/reference_pack/README.md`
- `docs/architecture/strategy-configs.md`

## Duplicate Content

### 1. Local setup and run instructions are duplicated across multiple entrypoints

Primary overlap set:

- `README.md`
- `docs/getting-started/quickstart.md`
- `docs/getting-started/local-run.md`
- `docs/getting-started/getting-started.md`
- `docs/operations/owner-runbook.md`

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
- `docs/testing/index.md`
- `docs/operations/runbook.md`
- `docs/testing/smoke-run.md`
- `docs/testing/determinism.md`
- `docs/testing/snapshot-testing.md`
- `docs/architecture/maintenance/ci_determinism.md`

Observed duplication:

- test command entrypoints
- determinism expectations
- smoke-run contract references
- quality-gate wording

Impact:

- readers have to infer which document is the canonical test entrypoint versus a narrow contract or policy doc

### 3. API example docs include explicit moved/redirect duplicates

Primary overlap set:

- `docs/operations/api-cookbook.md`
- `docs/operations/api/external_api_happy_path.md`
- `docs/operations/api/usage_examples.md`

Observed duplication:

- the first two files are retained redirect stubs that point to the third file

Impact:

- inventory/navigation noise remains even though the content owner effectively moved to `docs/operations/api/usage_examples.md`

### 4. Runtime health/status concepts are duplicated across two partially overlapping documents

Primary overlap set:

- `docs/operations/health.md`
- `docs/operations/runtime-status-and-health.md`

Observed duplication:

- both describe runtime state/health semantics
- both present payload-level expectations
- only one makes the `/health` endpoint contract explicit

Impact:

- readers can treat both as authoritative for runtime health even though they describe different shapes and scopes

### 5. Strategy lifecycle facts are repeated in both a model document and a phase-status document

Primary overlap set:

- `docs/architecture/strategy-lifecycle-model.md`
- `docs/architecture/phases/phase_25_strategy_lifecycle.md`

Observed duplication:

- state list
- allowed transitions
- production-only execution eligibility/enforcement framing

Impact:

- core lifecycle rules are repeated in multiple places rather than referenced from one source

### 6. Risk framework description is split across multiple architecture/status surfaces

Primary overlap set:

- `docs/architecture/risk_framework.md`
- `docs/architecture/risk/risk_framework.md`
- `docs/architecture/phases/phase-27-status.md`
- `docs/architecture/phases/phase_27_risk_framework.md`

Observed duplication:

- purpose/boundary statements
- deterministic risk-evaluation framing
- execution-gating language

Impact:

- the risk boundary exists in several near-adjacent forms, which increases the chance of future drift

### 7. Roadmap and phase-status navigation is heavily duplicated by design

Primary overlap set:

- `docs/index.md`
- `docs/architecture/roadmap/execution_roadmap.md`
- `docs/architecture/roadmap/cilly_trading_execution_roadmap_updated.md`
- `docs/architecture/audit/roadmap_compliance_report.md`
- `docs/phases/*.md`

Observed duplication:

- phase meaning summaries
- phase maturity/status statements
- repeated “authoritative vs derived” explanations

Impact:

- the docs try to control the duplication by repeatedly deferring to the roadmap, but the overall landscape is still high-friction to maintain

## Conflicting Instructions or Inconsistent Signals

### 1. `docs/operations/owner-runbook.md` conflicts with the current canonical install path

Conflict:

- `docs/operations/owner-runbook.md` instructs `pip install -r requirements.txt`
- `docs/getting-started/quickstart.md`, `docs/getting-started/local-run.md`, and `docs/getting-started/getting-started.md` instruct `python -m pip install -e ".[test]"`
- repository review shows no `requirements.txt` at the root

Why it matters:

- this is an actionable setup conflict, not only a wording difference
- a reader following `docs/operations/owner-runbook.md` exactly will hit a missing-file path

### 2. Runtime health payload expectations are inconsistent

Conflict:

- `docs/operations/health.md` defines `GET /health` as a read-only endpoint with payload keys `status`, `mode`, `reason`, and `checked_at`
- `docs/operations/runtime-status-and-health.md` presents health/status examples using different fields such as `engine_id`, `runtime_state`, `level`, `summary`, and `checks`

Why it matters:

- the relationship between endpoint contract and explanatory examples is not made explicit
- a reader can reasonably misread both documents as describing the same runtime response surface

### 3. Shell/platform guidance is inconsistent across setup/runtime docs

Conflict:

- `docs/getting-started/quickstart.md`, `docs/getting-started/local-run.md`, and `docs/getting-started/getting-started.md` provide PowerShell and Bash paths
- `docs/operations/owner-runbook.md` is Bash-only
- `docs/operations/api/usage_examples.md` presents Windows-style activation syntax inside a Bash fenced block

Why it matters:

- the repository README explicitly points Windows users to these operator docs
- inconsistent shell targeting weakens the claim that there is one canonical local run path for both PowerShell and Bash

### 4. “Canonical” ownership signals are diffuse in roadmap/runtime clusters

Conflict:

- multiple docs declare themselves canonical or authoritative for adjacent concerns
- examples include `README.md`, `docs/getting-started/local-run.md`, `docs/architecture/roadmap/execution_roadmap.md`, `docs/architecture/roadmap/cilly_trading_execution_roadmap_updated.md`, `docs/operations/ui/phase-36-web-activation-contract.md`, and `docs/operations/ui/phase-39-charting-contract.md`

Why it matters:

- the wording is often internally careful, but the aggregate effect is still ambiguous for a new reader deciding which document actually owns a given topic

## Unclear Ownership

### Repository-wide metadata gap

Only two in-scope documents explicitly declare an `Owner:` field during review:

- `docs/architecture/roadmap/execution_roadmap.md`
- `docs/architecture/phases/phase-37-status.md`

Most other documents do not identify a named steward, team, or maintenance owner.

### Highest-risk ownership gaps

#### 1. Onboarding and local-run cluster

Files:

- `README.md`
- `docs/getting-started/quickstart.md`
- `docs/getting-started/local-run.md`
- `docs/getting-started/getting-started.md`
- `docs/operations/owner-runbook.md`

Why ownership is unclear:

- all five act like entrypoints
- none names a maintainer
- at least one file has already drifted from the currently used install path

#### 2. Test and determinism cluster

Files:

- `docs/testing/index.md`
- `docs/operations/runbook.md`
- `docs/testing/smoke-run.md`
- `docs/testing/determinism.md`
- `docs/testing/snapshot-testing.md`
- `docs/architecture/maintenance/ci_determinism.md`

Why ownership is unclear:

- operational testing guidance, deterministic contracts, and CI policy are spread across multiple areas
- no single document declares itself the maintained test-entry owner for contributors

#### 3. Roadmap, phase, and audit cluster

Files:

- `docs/index.md`
- `docs/architecture/roadmap/execution_roadmap.md`
- `docs/architecture/roadmap/cilly_trading_execution_roadmap_updated.md`
- `docs/architecture/audit/roadmap_compliance_report.md`
- `docs/phases/*.md`

Why ownership is unclear:

- this cluster contains the most explicit “authoritative” wording
- despite that, responsibility is fragmented across roadmap, phase, index, and audit files

#### 4. Strategy/config and risk cluster

Files:

- `docs/architecture/strategy-configs.md`
- `docs/architecture/configuration_boundary.md`
- `docs/strategy/*.md`
- `docs/risk/*.md`
- `docs/architecture/phases/phase_25_strategy_lifecycle.md`
- `docs/architecture/phases/phase-27-status.md`

Why ownership is unclear:

- architecture, lifecycle, registry, validation, and risk boundary docs are all present
- none of the cluster documents clearly names the owner of strategy/configuration documentation as a maintained surface

## Summary Findings

- The documentation inventory is complete for the requested scope: 128 files.
- The largest duplication cluster is local setup/runtime onboarding.
- The clearest hard conflict is `docs/operations/owner-runbook.md` still pointing to `requirements.txt` while the rest of the active setup docs use the `pyproject.toml` editable install path.
- Runtime health semantics are not cleanly separated between endpoint contract and explanatory health/status narrative.
- Ownership metadata is largely absent, which makes future consolidation risky because drift cannot be assigned cleanly.

## Recommended Consolidation Priorities

These are audit priorities only, not change proposals for this issue.

1. Resolve the setup/runtime entrypoint cluster first.
2. Assign explicit stewardship for onboarding, testing, roadmap/status, and strategy/config docs.
3. Separate endpoint contracts from narrative/explainer docs where both currently describe “health” or “status”.
4. Decide which roadmap/status surfaces are canonical and which are navigation-only derivatives.
