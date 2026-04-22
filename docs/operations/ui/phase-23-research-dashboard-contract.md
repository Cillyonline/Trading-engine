# Phase 23 /ui Website-Facing Workflow Consolidation Contract

## Purpose
Define the bounded website-facing information architecture (IA) contract after Option 2 ratification:
one canonical `/ui` workflow shell with one bounded non-live signal review and trade-evaluation workflow.

Canonical product-surface authority and non-inference semantics are defined in:
- `docs/operations/ui/product-surface-authority-contract.md`

## Canonical Surface
- Surface name: `Canonical /ui Workflow Shell`
- Runtime entrypoint: `/ui`
- Runtime artifact: `src/ui/index.html`
- Runtime mount: `src/api/main.py`
- Non-authoritative parallel surface: `frontend/` remains non-authoritative unless governance promotion is explicitly documented

`/ui` is the only canonical website-facing workflow entrypoint in this contract.

Roadmap track alignment:
- Product Surface Track: this contract governs canonical `/ui` website-facing workflow authority.
- Strategy Readiness Track: readiness evidence remains separate and must not be inferred from this Product Surface Track contract.

## Primary Navigation Contract
The canonical `/ui` shell owns one bounded signal review and trade-evaluation workflow navigation contract:

1. `Signal Review Workflow Step 1: Run Analysis` (`#analysis-entry`)
2. `Signal Review Workflow Step 2: Configure Watchlist Scope` (`#watchlist-workflow`)
3. `Signal Review Workflow Step 3: Evaluate Ranked Signals` (`#watchlist-results`)
4. `Signal Review Workflow Step 4: Inspect Backtest Artifacts` (`#backtest-entry`)
5. `Signal Review Workflow Step 5: Inspect Runtime Data` (`#runtime-data`)
6. `Signal Review Workflow Step 6: Review Run Evidence` (`#run-evidence`)

These navigation labels and anchors are the website-facing IA ownership markers for this issue slice and explicitly constrain scope to one bounded workflow.

## Explicit Non-Live Boundary
IA consolidation in `/ui` does not introduce:
- live trading
- broker execution
- trader validation
- operational-readiness claims
- production-readiness claims
- technical backtest availability as a substitute for trader validation or readiness evidence
- technical signal visibility as a substitute for trader validation or operational readiness evidence
- trader validation status as a substitute for operational readiness status

Bounded Phase 39 visual-analysis/charting markers coexist on `/ui` and remain technical-only runtime context.
Their presence is an explicit non-inference marker and does not imply trader validation or operational readiness.

## Bounded Workflow Ownership
The `/ui` shell consolidates bounded website-facing workflow entrypoints through existing backend routes:
- `POST /analysis/run`
- `GET/POST/PUT/DELETE /watchlists`
- `POST /watchlists/{watchlist_id}/execute`
- `GET /system/state`
- `GET /strategies`
- `GET /signals`
- `GET /decision-review`
- `GET /decision-cards`
- `GET /signals/decision-surface`
- `GET /backtest/artifacts`
- `GET /backtest/artifacts/{run_id}/{artifact_name}`
- `GET /alerts/history`
- `GET /journal/artifacts`
- `GET /journal/decision-trace`
- `GET /execution/orders`

Consolidation of IA does not widen route scope and does not imply trader validation or operational readiness.
Technical signal visibility and ranked evaluation output are explicitly separated from trader validation and operational readiness claims.
The canonical bounded decision-review contract is `GET /decision-review`, while covered legacy read surfaces (`/decision-cards`, `/signals/decision-surface`) remain available with explicit mapping for canonical decision evidence fields.
The bounded signal decision surface classifies reviewed signals into technical-only decision states (`blocked`, `watch`, `paper_candidate`) with concise rationale, explicit qualification evidence, missing criteria, and blocking conditions.
Decision-surface items also expose canonical bounded decision-card evidence fields (`qualification_state`, `action`, `win_rate`, `expected_value`) for deterministic parity across bounded read surfaces.
Professional non-live qualification criteria remain bounded to explicit signal evidence:
- `stage` must satisfy `entry_confirmed`
- `score` must satisfy configured technical thresholds
- `confirmation_rule` must be explicitly present
- `entry_zone` structure and ordering must be valid (`from_ < to`)

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
