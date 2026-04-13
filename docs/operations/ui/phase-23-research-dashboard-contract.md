# Phase 23 Research Dashboard Minimum Contract

## Purpose
Define the bounded minimum contract that allows Phase 23 (`Research Dashboard`) to be treated as evidenced in-repository, without widening scope into trader or production claims.

## Claimed Surface
- Surface name: `Research Dashboard`
- Runtime entrypoint: `/research-dashboard`
- Runtime artifact: `src/ui/research_dashboard/index.html`
- Runtime mount: `src/api/main.py`

The claimed surface is research-only and is explicitly separate from the shared operator shell at `/ui`.

## Bounded Scope
In scope for this minimum contract:
- one dedicated and identifiable research-only dashboard surface
- one runtime/UI artifact for the same named surface
- one verification artifact for the same named surface
- explicit separation from shared operator-shell claims

Out of scope:
- workstation redesign
- live trading
- execution automation
- trader-readiness claims
- production-readiness claims

## Minimum Evidence Set
Phase 23 minimum evidence is satisfied only when all items below target the same surface:

1. Bounded contract documentation  
   This file defines the claimed surface, route, scope boundary, and non-claims.
2. Runtime/UI implementation artifact  
   `src/ui/research_dashboard/index.html` provides the runtime-served research-only surface at `/research-dashboard`.
3. Verification artifact  
   `src/api/test_research_dashboard_surface.py` verifies route reachability and research/operator-shell boundary markers.

## Separation From Shared Operator Shell Claims
- `/ui` remains the operator workbench shell and must not be used as implied proof of Phase 23.
- `/research-dashboard` is the only Phase 23 minimum-surface claim in this contract.
- Adjacency to `/ui`, charting, analytics, or desk wording is not evidence for this Phase 23 claim.

## OPS-P56 and #914 Non-Interference
This Phase 23 minimum contract does not redefine operational run logging and does not replace OPS-P56 issue #914.

`OPS-P56: Start bounded staged paper-trading runbook and evidence log #914` remains the single operational run log issue.

## Verification Procedure
1. Open `/research-dashboard`.
2. Confirm marker `id="phase23-research-dashboard-surface"` is present.
3. Confirm the page states research-only scope and explicit separation from `/ui`.
4. Run `pytest src/api/test_research_dashboard_surface.py tests/test_phase23_research_dashboard_contract.py`.

## Classification For This Issue
Phase 23 under this minimum contract is classified as:

- technically good, but traderically weak

This means bounded research-surface evidence is present, while trader-readiness and production-readiness are intentionally not claimed.
