# Cilly Trading Engine - Documentation

## Start Here
The Cilly Trading Engine is a deterministic execution and analysis engine for teams that need reproducible workflows, stable interfaces, and controlled change management. This index is intended for new consumers who need a fixed, step-by-step path to start using documented capabilities.

Use this order:
1. Quickstart
2. Run deterministic smoke test
3. Explore API
4. Explore CLI
5. Understand versioning model

## Quickstart
- [Quickstart](getting-started/quickstart.md)
- [Run deterministic smoke test](testing/smoke-run.md)

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
- [Staging-first deployment topology and runtime contract](operations/runtime/staging-first-deployment-topology.md)

## UI Surfaces
- [Phase 36 /ui web activation contract](operations/ui/phase-36-web-activation-contract.md)
- [Phase 39 /ui charting contract](operations/ui/phase-39-charting-contract.md)
- [Phase 39 runtime charting test plan](operations/ui/phase-39-test-plan.md)
- Legacy compatibility alias: `docs/ui/phase-39-test-plan.md`
- [Operator dashboard runtime surface](operations/ui/owner_dashboard.md)
  - Runtime-served operator UI is `/ui`.
  - The current Phase 36 browser workflow uses `/system/state`, `POST /analysis/run`, `/strategies`, `/signals`, `/journal/artifacts`, `/journal/decision-trace`, and `/execution/orders`.
  - The current Phase 37 browser workflow on the same `/ui` surface uses `/watchlists`, `/watchlists/{watchlist_id}`, and `POST /watchlists/{watchlist_id}/execute`.
  - The current Phase 39 browser workflow on the same `/ui` surface adds a bounded read-only chart panel fed by `POST /analysis/run`, `POST /watchlists/{watchlist_id}/execute`, and `GET /signals?limit=20&sort=created_at_desc`.
  - The chart payload boundary for those existing routes is defined in `docs/operations/api/runtime_chart_data_contract.md`.
  - The minimum verification gate for Phase 39 runtime charting is defined in `docs/operations/ui/phase-39-test-plan.md`.
  - The Phase 39 charting contract and roadmap status remain bounded to read-only visual analysis on `/ui` and do not imply Phase 40 desk scope.
  - `/owner` is not a canonical runtime entrypoint.
- [Phase 36 web activation evidence](architecture/roadmap/phase-36-web-activation-evidence.md)
- [Phase 37 watchlist engine status](architecture/phases/phase-37-status.md)

## Versioning & Governance
- [Versioning model](architecture/versioning/model.md)
- [Versioning scope](architecture/versioning/scope.md)
- [Change enforcement](architecture/versioning/change_enforcement.md)
- [Release boundary](architecture/versioning/release_boundary.md)
- [Version declaration](architecture/versioning/declaration.md)
- [Compatibility gate](architecture/versioning/compatibility_gate.md)

## Authoritative Phase Taxonomy
The authoritative in-repo source for audited phase-number meanings is [Execution Roadmap](architecture/roadmap/execution_roadmap.md).
The authoritative in-repo source for phase maturity/status is the broader [Complete Master Roadmap](architecture/roadmap/cilly_trading_execution_roadmap_updated.md).
The execution roadmap governs audited phase meaning and taxonomy only, while the master roadmap governs canonical phase maturity/status.
Per-phase status files, audit artifacts, and the index are derived navigation or evidence surfaces and must defer to those two authorities.
Status changes therefore follow one update path: update supporting evidence as needed, then update the master roadmap to change the canonical phase maturity/status.

| Phase | Meaning in the authoritative taxonomy | Primary trace |
|-------|---------------------------------------|---------------|
| Phase 5 | External Ready exit gate | `docs/architecture/governance/phase-5-exit-criteria.md` |
| Phase 16 | No authoritative in-repo meaning located | `docs/architecture/roadmap/execution_roadmap.md` |
| Phase 17 | Consumer Interfaces and Usage Patterns umbrella phase | `docs/architecture/roadmap/execution_roadmap.md` |
| Phase 17b | Owner Dashboard sub-phase | `docs/architecture/roadmap/execution_roadmap.md` |
| Phase 23 | `Research Dashboard`: one dedicated research-only dashboard surface; it remains `NOT IMPLEMENTED` until one coherent minimum evidence set exists for that surface: a bounded dashboard contract, a runtime or UI implementation artifact, and a verification artifact | `docs/architecture/phases/phase-23-status.md` |
| Phase 25 | Strategy Lifecycle Management | `docs/architecture/phases/phase_25_strategy_lifecycle.md` |
| Phase 26 | No authoritative in-repo meaning located | `docs/architecture/roadmap/execution_roadmap.md` |
| Phase 27 | Risk Framework | `docs/architecture/phases/phase-27-status.md` |
| Phase 37 | Watchlist Engine | `docs/architecture/phases/phase-37-status.md` |

## Reference Navigation
The links below are navigation aids only. They do not redefine the authoritative phase taxonomy or the canonical phase maturity/status in the master roadmap.

### Phase 17 Reference Materials
Phase 17 is the Consumer Interfaces and Usage Patterns umbrella phase. Phase 17b remains the distinct Owner Dashboard sub-phase in the authoritative roadmap. Any status wording in the links below is derived and must defer to the master roadmap.
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

### Phase 23 Boundary Note
Phase 23 means `Research Dashboard`: one dedicated research-only dashboard surface as defined in [Phase 23 status](architecture/phases/phase-23-status.md). It remains `NOT IMPLEMENTED` until one coherent minimum evidence set exists for that surface: a bounded dashboard contract, a runtime or UI implementation artifact, and a verification artifact. Current operator `/ui` surfaces, analytics artifacts, Phase 39 charting docs, and Phase 40 trading-desk wording are adjacent references only and are insufficient on their own to claim Phase 23 implementation.

### Phase 24 Reference Materials
Phase 24 reference links remain navigational and do not override the authoritative audited taxonomy above or the canonical phase maturity/status in the master roadmap.
- [Paper trading boundary](operations/paper-trading.md)
- [Runbook](operations/runbook.md)

### Phase 44 Reference Materials
Phase 44 reference links remain navigational and do not override the authoritative audited taxonomy above or the canonical phase maturity/status in the master roadmap.
- [Phase 44 bounded paper operator workflow](operations/runtime/phase-44-paper-operator-workflow.md)
- [Paper inspection and reconciliation API](api/paper_inspection.md)
- [Paper deployment acceptance gate](operations/runtime/paper-deployment-acceptance-gate.md)

### Phase 37 Reference Materials
Phase 37 reference links remain navigational and do not override the authoritative audited taxonomy above or the canonical phase maturity/status in the master roadmap.
- [Phase 37 watchlist engine status](architecture/phases/phase-37-status.md)
- [Operator dashboard runtime surface](operations/ui/owner_dashboard.md)
- [API usage contract](operations/api/usage_contract.md)

### Phase 18 Reference Materials
Phase 18 reference links remain navigational and do not override the authoritative audited taxonomy above or the canonical phase maturity/status in the master roadmap.
- [Change policy](operations/external/change_policy.md)
- [Client types](operations/external/client_types.md)
- [Contract surface](operations/external/contract_surface.md)
- [Error semantics](operations/external/error_semantics.md)
- [Integration assumptions](operations/external/integration_assumptions.md)

### Phase 19 Reference Materials
Phase 19 reference links remain navigational and do not override the authoritative audited taxonomy above or the canonical phase maturity/status in the master roadmap.
- [Compatibility gate](architecture/versioning/compatibility_gate.md)
- [Change enforcement](architecture/versioning/change_enforcement.md)
- [Version declaration](architecture/versioning/declaration.md)
- [Versioning model](architecture/versioning/model.md)
- [Release boundary](architecture/versioning/release_boundary.md)
- [Versioning scope](architecture/versioning/scope.md)
