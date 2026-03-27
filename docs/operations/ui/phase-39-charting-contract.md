# Phase 39 /ui Charting Evidence Boundary

## Purpose
This document defines how Phase 39 charting claims relate to the shared runtime `/ui` surface.

Phase 39 remains bounded to deterministic chart-data contract behavior and explicit non-inference rules.

## Contract Scope
- Runtime route context: `/ui` shared shell
- Primary contract authority: `docs/operations/api/runtime_chart_data_contract.md`
- Projection/validation module: `src/api/chart_contract.py`

Phase 39 does not require dedicated chart-panel markers on the current `/ui` page to assert the chart-data contract boundary.

## What /ui Evidence Proves for Phase 39
- `/ui` provides shared analysis/watchlist/signal inputs whose payloads can be projected into the Phase 39 chart-data contract.
- `/ui` remains the runtime context where those existing API responses are operator-visible.

## What /ui Evidence Does Not Prove for Phase 39
- Dedicated chart widget implementation
- Dedicated chart-panel markers
- Broad trading-desk or notification workflow completion

Those claims require separate bounded evidence and must not be inferred from section adjacency.

## In-Scope Phase 39 Capabilities
| Capability | Evidence anchor |
| --- | --- |
| Deterministic chart-data projection from existing runtime APIs | `docs/operations/api/runtime_chart_data_contract.md`, `src/api/chart_contract.py`, `tests/test_api_phase39_chart_contract.py` |
| Snapshot-first and non-live guardrails for chart-data payloads | `tests/test_api_phase39_chart_contract.py` |
| Explicit fallback-only treatment of `GET /signals` for chart projection | `docs/operations/api/runtime_chart_data_contract.md`, `tests/test_api_phase39_chart_contract.py` |

## Explicitly Out of Scope
Phase 39 does not include:
- Introducing new backend routes solely for charting
- Claiming chart-panel UI completion from shared-shell adjacency
- Phase 40 trading-desk completion claims
- Phase 41 notification-delivery claims
- Strategy Lab, paper-trading product workflow, live-trading workflow, or broker controls

## Evidence Pointers
| Evidence area | Repository basis |
| --- | --- |
| Shared runtime route boundary | `src/api/main.py` mounts `/ui` |
| Runtime chart-data contract | `docs/operations/api/runtime_chart_data_contract.md` |
| Contract implementation | `src/api/chart_contract.py` |
| Contract tests | `tests/test_api_phase39_chart_contract.py` |
| Shared-shell marker tests | `src/api/test_operator_workbench_surface.py`, `tests/test_ui_runtime_browser_flow.py` |
| Cross-phase ownership boundary | `docs/architecture/ui-runtime-phase-ownership-boundary.md` |

## Outcome
For Phase 39, the canonical claim is:
- deterministic chart-data contract behavior over existing runtime API payloads
- no inference that `/ui` section adjacency proves chart-panel UI completion or later-phase completion

