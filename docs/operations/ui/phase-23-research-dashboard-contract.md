# Phase 23 /ui Website-Facing Workflow Consolidation Contract

## Purpose
Define the bounded website-facing information architecture (IA) contract after Option 2 ratification:
one canonical `/ui` workflow shell with explicit non-live boundaries.

## Canonical Surface
- Surface name: `Canonical /ui Workflow Shell`
- Runtime entrypoint: `/ui`
- Runtime artifact: `src/ui/index.html`
- Runtime mount: `src/api/main.py`
- Non-authoritative parallel surface: `frontend/` remains non-authoritative unless later promoted by governance

`/ui` is the only canonical website-facing workflow entrypoint in this contract.

## Primary Navigation Contract
The canonical `/ui` shell owns one bounded workflow navigation contract:

1. `Workflow: Run Analysis` (`#analysis-entry`)
2. `Workflow: Manage Watchlists` (`#watchlist-workflow`)
3. `Workflow: Review Ranked Watchlist Results` (`#watchlist-results`)
4. `Workflow: Inspect Runtime Data` (`#runtime-data`)
5. `Workflow: Review Run Evidence` (`#run-evidence`)

These navigation labels and anchors are the website-facing IA ownership markers for this issue slice.

## Explicit Non-Live Boundary
IA consolidation in `/ui` does not introduce:
- live trading
- broker execution
- trader validation
- operational-readiness claims
- production-readiness claims

`No Phase 39 or Phase 40 features` wording in the `/ui` shell remains an explicit non-inference marker.

## Bounded Workflow Ownership
The `/ui` shell consolidates bounded website-facing workflow entrypoints through existing backend routes:
- `POST /analysis/run`
- `GET/POST/PUT/DELETE /watchlists`
- `POST /watchlists/{watchlist_id}/execute`
- `GET /system/state`
- `GET /strategies`
- `GET /signals`
- `GET /alerts/history`
- `GET /journal/artifacts`
- `GET /journal/decision-trace`
- `GET /execution/orders`

Consolidation of IA does not widen route scope and does not imply trader validation or operational readiness.

## Minimum Evidence Set
1. Bounded contract documentation  
   This file defines canonical `/ui` ownership, navigation contract, and explicit non-live boundary.
2. Runtime/UI implementation artifact  
   `src/ui/index.html` includes canonical shell and navigation markers:
   - `id="ui-primary-navigation-contract"`
   - `id="ui-workflow-boundary-marker"`
3. Verification artifact  
   - `src/api/test_research_dashboard_surface.py`
   - `src/api/test_operator_workbench_surface.py`
   - `tests/test_ui_runtime_browser_flow.py`
   - `tests/test_phase23_research_dashboard_contract.py`

## Verification Procedure
1. Open `/ui`.
2. Confirm canonical marker text: `Bounded Website-Facing Workflow Shell`.
3. Confirm navigation contract marker `id="ui-primary-navigation-contract"` is present.
4. Confirm non-live marker `id="ui-workflow-boundary-marker"` is present.
5. Confirm non-live boundary text includes no live trading, no broker execution controls, and no operational-readiness inference.
6. Run `pytest src/api/test_research_dashboard_surface.py src/api/test_operator_workbench_surface.py tests/test_ui_runtime_browser_flow.py tests/test_phase23_research_dashboard_contract.py`.

## OPS-P56 and #914 Non-Interference
This IA consolidation contract does not redefine operational run logging and does not replace OPS-P56 issue #914.

`OPS-P56: Start bounded staged paper-trading runbook and evidence log #914` remains the single operational run log issue.
