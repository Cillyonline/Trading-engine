# Cilly Trading Engine - Documentation Index

`docs/index.md` is a navigation surface.

For role boundaries and canonical topic ownership rules, see
`docs/architecture/documentation_structure.md`.

## Start Path

Use this order:

1. [Quickstart](getting-started/quickstart.md)
2. [Run deterministic smoke test](testing/smoke-run.md)
3. [Getting started guide](getting-started/getting-started.md)
4. [Local run guide](getting-started/local-run.md)
5. Continue with API, CLI, UI, and governance links below

Canonical first-clean-server install contract:
- `docs/operations/runtime/staging-server-deployment.md`
- Docker/Compose (`docker compose -f docker/staging/docker-compose.staging.yml up -d --build`) is the only canonical first-clean-server startup path.
- Local development setup guides are non-canonical for first-clean-server installation.

## Runtime Deployment

- [Staging server deployment](operations/runtime/staging-server-deployment.md)

## API Usage

- [API usage](operations/api/usage.md)
- [Trading core inspection API](api/trading_core_inspection.md)
- [Paper inspection and reconciliation API](api/paper_inspection.md)
- [Decision card inspection API](api/decision_card_inspection.md)
- [Phase 39 runtime chart data contract](operations/api/runtime_chart_data_contract.md)
- Legacy compatibility alias: `docs/api/runtime_chart_data_contract.md`

## CLI Usage

- [CLI usage](operations/cli/usage.md)
- [Paper trading boundary](operations/paper-trading.md)
- [Phase 44 bounded paper operator workflow](operations/runtime/phase-44-paper-operator-workflow.md)
- [OPS-P63 daily bounded paper runtime workflow](operations/runtime/p63-daily-bounded-paper-runtime-workflow.md)
- [Staging-first deployment topology and runtime contract](operations/runtime/staging-first-deployment-topology.md)

## UI Surfaces

- [Phase 36 /ui web activation contract](operations/ui/phase-36-web-activation-contract.md)
- [Phase 39 /ui charting contract](operations/ui/phase-39-charting-contract.md)
- [Phase 39 runtime charting test plan](operations/ui/phase-39-test-plan.md)
- Legacy compatibility alias: `docs/ui/phase-39-test-plan.md`
- [Operator dashboard runtime surface](operations/ui/owner_dashboard.md)
- [Shared /ui phase boundary](architecture/ui-runtime-phase-ownership-boundary.md)
- [Phase 36 web activation evidence](architecture/roadmap/phase-36-web-activation-evidence.md)
- [Phase 37 watchlist engine status](architecture/phases/phase-37-status.md)

## Versioning And Governance

- [Versioning model](architecture/versioning/model.md)
- [Versioning scope](architecture/versioning/scope.md)
- [Change enforcement](architecture/versioning/change_enforcement.md)
- [Release boundary](architecture/versioning/release_boundary.md)
- [Version declaration](architecture/versioning/declaration.md)
- [Compatibility gate](architecture/versioning/compatibility_gate.md)
- [Document status model](architecture/governance/document-status-model.md)
- [Qualification claim evidence discipline](governance/qualification-claim-evidence-discipline.md)

## Roadmap Navigation

- [Execution roadmap](architecture/roadmap/execution_roadmap.md)
- `ROADMAP_MASTER.md`

## Phase Reference Navigation

### Phase 17 Reference Materials

- [Operator dashboard runtime surface](operations/ui/owner_dashboard.md)
- [Phase 36 /ui web activation contract](operations/ui/phase-36-web-activation-contract.md)
- [API guarantees](operations/api/api_guarantees.md)
- [External API happy path](operations/api/external_api_happy_path.md)
- [Public API boundary](operations/api/public_api_boundary.md)
- [API usage contract](operations/api/usage_contract.md)
- [API usage examples](operations/api/usage_examples.md)
- [Batch execution interface](operations/interfaces/batch_execution.md)
- [CLI contract](operations/interfaces/cli_contract.md)
- [Interface usage patterns](operations/interfaces/usage_patterns.md)

### Phase 23 Reference Materials

- [Phase 23 status](architecture/phases/phase-23-status.md)
- [Phase 23 /ui workflow consolidation contract](operations/ui/phase-23-research-dashboard-contract.md)
- Phase 23 | `Canonical /ui Workflow Shell` | PARTIALLY IMPLEMENTED

### Phase 24 Reference Materials

- [Paper trading boundary](operations/paper-trading.md)
- [Runbook](operations/runbook.md)

### Phase 44 Reference Materials

- [Phase 44 bounded paper operator workflow](operations/runtime/phase-44-paper-operator-workflow.md)
- [Paper inspection and reconciliation API](api/paper_inspection.md)
- [Paper deployment acceptance gate](operations/runtime/paper-deployment-acceptance-gate.md)

### P53 Reference Materials

- [P53 automated review operations](operations/runtime/p53-automated-review-operations.md)

### OPS-P63 Reference Materials

- [OPS-P63 daily bounded paper runtime workflow](operations/runtime/p63-daily-bounded-paper-runtime-workflow.md)

### OPS-P61 Reference Materials

- [OPS-P61 Practice and Analysis Article standards](phases/ops-p61-practice-analysis-article-standards.md)

### P56-RISK Reference Materials

- [P56 bounded adverse scenario matrix](architecture/risk/p56-bounded-adverse-scenario-matrix.md)

### DEC-P47 Reference Materials

- [DEC-P47 qualification claim boundary](phases/dec-p47-qualification-claim-boundary.md)

### Phase 37 Reference Materials

- [Phase 37 watchlist engine status](architecture/phases/phase-37-status.md)
- [Operator dashboard runtime surface](operations/ui/owner_dashboard.md)
- [API usage contract](operations/api/usage_contract.md)

### Phase 18 Reference Materials

- [Change policy](operations/external/change_policy.md)
- [Client types](operations/external/client_types.md)
- [Contract surface](operations/external/contract_surface.md)
- [Error semantics](operations/external/error_semantics.md)
- [Integration assumptions](operations/external/integration_assumptions.md)

### Phase 19 Reference Materials

- [Compatibility gate](architecture/versioning/compatibility_gate.md)
- [Change enforcement](architecture/versioning/change_enforcement.md)
- [Version declaration](architecture/versioning/declaration.md)
- [Versioning model](architecture/versioning/model.md)
- [Release boundary](architecture/versioning/release_boundary.md)
- [Versioning scope](architecture/versioning/scope.md)
