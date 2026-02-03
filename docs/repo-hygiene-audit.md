# Non-Code Repository Hygiene Audit (Issue #238)

## Scope
- Included: all repository paths except src/**, api/**, tests/**, .github/**.
- Excluded: any paths under src/**, api/**, tests/**, .github/**.

## Inventory (Table)
| path | type | purpose (<=12 words) | status | notes |
| --- | --- | --- | --- | --- |
| requirements.txt | file | Python dependencies list. | keep |  |
| README.md | file | Project overview and usage instructions. | keep |  |
| scripts/ | dir | Local helper scripts for repo operations. | keep |  |
| scripts/create_demo_snapshot.py | file | Generates demo snapshot data. | keep |  |
| .devcontainer/ | dir | Devcontainer configuration assets. | keep |  |
| .devcontainer/devcontainer.json | file | Devcontainer setup configuration. | keep |  |
| schemas/ | dir | JSON schemas for outputs. | keep |  |
| schemas/signal-output.schema.json | file | Signal output schema definition. | keep |  |
| schemas/signal-output.schema.v0.json | file | Legacy signal output schema. | keep |  |
| docs/ | dir | Documentation hub. | keep |  |
| docs/api_cookbook.md | file | API usage cookbook. | keep |  |
| docs/numeric_output_precision.md | file | Numeric output precision guidance. | keep |  |
| docs/deterministic-analysis.md | file | Deterministic analysis documentation. | keep |  |
| docs/smoke-run.md | file | Smoke run instructions. | keep |  |
| docs/local_run.md | file | Local run guide. | keep |  |
| docs/architecture/ | dir | Architecture documentation. | keep |  |
| docs/architecture/phase6_snapshot_contract.md | file | Phase 6 snapshot contract spec. | keep |  |
| docs/reports/ | dir | Historical reports and audits. | candidate-for-archive | Review retention policy. |
| docs/reports/I-029a_implicit_time_inventory.md | file | Implicit time inventory report. | candidate-for-archive | Historical report. |
| docs/reports/repo_audit_DISC-4_C2.md | file | Repository audit report. | candidate-for-archive | Historical report. |
| docs/standards/ | dir | Standards and rules documents. | keep |  |
| docs/standards/breaking-change-regeln.md | file | Breaking change rules. | keep |  |
| docs/phase-6-exit-criteria.md | file | Phase 6 exit criteria. | keep |  |
| docs/snapshot-testing.md | file | Snapshot testing guidance. | keep |  |
| docs/mvp_v1.md | file | MVP v1 specification. | keep |  |
| docs/RUNBOOK.md | file | Operational runbook. | keep |  |
| docs/governance/ | dir | Governance and process documentation. | keep |  |
| docs/governance/stop-conditions-and-merge-authority.md | file | Stop conditions and merge authority. | keep |  |
| docs/governance/external-readiness-checklist.md | file | External readiness checklist. | keep |  |
| docs/governance/pr-review-checklist-test-gated.md | file | PR review checklist. | keep |  |
| docs/governance/phase-5-exit-criteria.md | file | Phase 5 exit criteria. | keep |  |
| docs/governance/explicit-test-gated-execution-mode.md | file | Explicit test-gated mode details. | keep |  |
| docs/governance/execution-modes.md | file | Execution modes description. | keep |  |
| docs/testing/ | dir | Testing guidance documents. | keep |  |
| docs/testing/determinism.md | file | Determinism testing guidance. | keep |  |
| docs/analyst-workflow.md | file | Analyst workflow steps. | keep |  |
| docs/api/ | dir | API documentation. | keep |  |
| docs/api/external_api_happy_path.md | file | External API happy path. | keep |  |
| docs/api/usage_contract.md | file | API usage contract. | keep |  |
| docs/api/api_guarantees.md | file | API guarantees definition. | keep |  |
| docs/MVP_SPEC.md | file | MVP specification. | keep |  |
| docs/index.md | file | Documentation index. | keep |  |
| docs/exploration/ | dir | Exploration notes. | keep |  |
| docs/exploration/exploration-guide.md | file | Exploration guide. | keep |  |
| docs/fixtures.md | file | Fixtures documentation. | keep |  |
| docs/phase-6/ | dir | Phase 6 documentation. | keep |  |
| docs/phase-6/PHASE_6_OPERATIONAL_OVERVIEW.md | file | Phase 6 operational overview. | keep |  |
| docs/repo-snapshot.md | file | Repo snapshot documentation. | keep |  |
| docs/checklists/ | dir | Project checklists. | keep |  |
| docs/checklists/phase-6-exit-checklist.md | file | Phase 6 exit checklist. | keep |  |
| docs/strategy-configs.md | file | Strategy configuration documentation. | keep |  |
| docs/repo-hygiene-audit.md | file | Non-code repository hygiene audit. | keep | Current report. |
| fixtures/ | dir | Test and demo fixtures. | keep |  |
| fixtures/smoke-run/ | dir | Smoke run fixture set. | keep |  |
| fixtures/smoke-run/input.json | file | Smoke run input data. | keep |  |
| fixtures/smoke-run/expected.csv | file | Smoke run expected output. | keep |  |
| fixtures/smoke-run/config.yaml | file | Smoke run configuration. | keep |  |
| fixtures/deterministic-analysis/ | dir | Deterministic analysis fixtures. | keep |  |
| fixtures/deterministic-analysis/aapl_d1.csv | file | Sample AAPL daily data. | keep |  |
| fixtures/deterministic-analysis/analysis_config.json | file | Deterministic analysis config. | keep |  |
| fixtures/market_data/ | dir | Market data fixtures. | keep |  |
| fixtures/market_data/aapl_us_d1_2015-02/ | dir | AAPL daily data February 2015. | keep |  |
| fixtures/market_data/aapl_us_d1_2015-02/raw.csv | file | Raw market data CSV. | keep |  |
| fixtures/market_data/aapl_us_d1_2015-02/normalized.csv | file | Normalized market data CSV. | keep |  |
| Dockerfile | file | Container build configuration. | keep |  |
| data/ | dir | Local data storage. | keep |  |
| data/phase6_snapshots/ | dir | Phase 6 snapshot data. | keep |  |
| data/phase6_snapshots/test-snapshot-0001/ | dir | Sample snapshot data. | candidate-for-archive | Example snapshot. |
| data/phase6_snapshots/test-snapshot-0001/payload.json | file | Snapshot payload data. | candidate-for-archive | Example snapshot. |
| data/phase6_snapshots/test-snapshot-0001/metadata.json | file | Snapshot metadata. | candidate-for-archive | Example snapshot. |
| strategy/ | dir | Strategy configuration assets. | keep |  |
| strategy/presets/ | dir | Strategy preset definitions. | keep |  |
| strategy/presets/rsi2.presets.json | file | RSI2 strategy presets. | keep |  |
| strategy/presets/turtle.presets.json | file | Turtle strategy presets. | keep |  |
| docker-compose.yml | file | Multi-container orchestration config. | keep |  |
| .gitignore | file | Git ignore rules. | keep |  |

## Findings Summary
- Documentation is extensive, covering governance, architecture, and operations.
- Historical reports exist under docs/reports and may be archival material.
- Fixtures and sample data are present for smoke and deterministic analysis.
- Phase 6 snapshot sample data is stored under data/phase6_snapshots.
- Non-code configuration files include Docker, devcontainer, and schemas.
- Strategy presets are stored as JSON configurations.

## Cleanup Candidates (Not Executed)
### candidate-for-archive
- docs/reports/
- docs/reports/I-029a_implicit_time_inventory.md
- docs/reports/repo_audit_DISC-4_C2.md
- data/phase6_snapshots/test-snapshot-0001/
- data/phase6_snapshots/test-snapshot-0001/payload.json
- data/phase6_snapshots/test-snapshot-0001/metadata.json

### candidate-for-removal
- None identified.

### unclear
- None identified.

## Verification
No repository files were modified except docs/repo-hygiene-audit.md.
Command used: git status -sb.
