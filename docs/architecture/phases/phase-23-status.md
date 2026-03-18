# Phase 23 - Research Dashboard

## Status
NOT IMPLEMENTED

## Taxonomy Alignment
Phase 23 means `Research Dashboard` in the authoritative taxonomy source:
`docs/architecture/roadmap/execution_roadmap.md`

## Canonical Bounded Message
Phase 23 means `Research Dashboard`: one dedicated research-only dashboard surface.
Phase 23 remains `NOT IMPLEMENTED` until one coherent minimum evidence set exists for that surface: a bounded dashboard contract, a runtime or UI implementation artifact, and a verification artifact.
Current operator `/ui` surfaces, analytics artifacts, Phase 39 charting surfaces, and Phase 40 trading-desk wording are adjacent only and do not count on their own as Phase 23 implementation evidence.

## Authoritative Bounded Scope
Phase 23 is the repo-verifiable phase for one dedicated research-only dashboard surface that consolidates research review into a single bounded workspace.

That bounded Phase 23 meaning requires repository evidence for a dashboard artifact that:
- is explicitly identified as a Research Dashboard
- is dedicated to research review rather than operator control or trade execution
- combines research-oriented views into one coherent surface instead of scattering them across unrelated routes, panels, or metrics outputs

## Minimum Repo-Verifiable Evidence Contract
A Phase 23 claim must be supported by one coherent minimum artifact set inside the repository. Reviewers should treat the phase as `NOT IMPLEMENTED` unless all three required evidence classes below are present for the same bounded Research Dashboard surface.

### Required evidence class 1: bounded dashboard contract
The repository must contain documentation that identifies one concrete Research Dashboard surface and lets a reviewer distinguish it from adjacent phases. That documentation must:
- name the surface as the Research Dashboard
- state the runtime entrypoint, route, or launch surface being claimed
- describe the bounded research-only purpose of the surface
- identify the core research views or panels that are part of the claimed dashboard

### Required evidence class 2: runtime or UI implementation artifact
The repository must contain at least one implementation artifact for that same bounded surface. Acceptable evidence includes:
- runtime-served UI files or frontend assets that clearly render the named Research Dashboard surface
- backend route, mount, or handler code that serves or exposes the claimed dashboard surface
- a bounded UI contract document tied to existing runtime code and endpoints for that dashboard surface

### Required evidence class 3: verification artifact
The repository must contain at least one verification artifact that checks the same bounded dashboard claim. Acceptable evidence includes:
- tests that assert the dashboard route, mount, rendered marker, or bounded research panels
- reviewable manual verification instructions that reference the exact route, marker, and research-only surface being claimed
- a bounded contract or checklist that a reviewer can apply directly to repo artifacts without guessing

## Classification Rule
Use the following gate when reviewing future Phase 23 claims:
- `NOT IMPLEMENTED`: any required evidence class above is missing, or the artifacts do not point to the same bounded Research Dashboard surface
- `PARTIALLY IMPLEMENTED`: all three required evidence classes are present, but the documented dashboard scope is explicitly incomplete or only some of the defined research views are implemented
- `IMPLEMENTED`: all three required evidence classes are present and they support the complete bounded Research Dashboard scope being claimed in repository docs

Reviewers should reject a status advance when the artifacts require inference across unrelated surfaces instead of demonstrating one coherent dashboard contract.

## Explicit Phase Boundaries
Phase 23 is not satisfied by adjacent phases or by overlapping dashboard language.

- Phase 17b is the Owner Dashboard and the existing runtime-served `/ui` operator surface. Operator workbench panels on `/ui` do not count as implied Phase 23 evidence.
- Phase 30 is the Trading Analytics Layer. Metrics artifacts, performance reports, and analytics outputs do not count as a Research Dashboard by themselves.
- Phase 39 is Charting & Visual Analysis. Read-only chart panels and visual-analysis surfaces do not count as a Research Dashboard by themselves.
- Phase 40 is the Trading Desk Dashboard. Broader desk, overview, or professional trading dashboard language does not define or satisfy Phase 23.

## Verified Repository Evidence
The current repository review did not confirm a Phase 23 implementation artifact in:
- `src/**`
- `engine/**`
- `tests/**`
- runtime-facing documentation for a dedicated research-only dashboard surface

Repository references to `Research Dashboard` in the audited scope are currently limited to roadmap and status-tracking documents, not implementation artifacts.
The current repository therefore fails all three required evidence classes in the minimum Phase 23 evidence contract above.

## Non-Evidence Clarification
The following artifact classes are insufficient on their own to claim Phase 23 implementation progress, even if they mention dashboards, research, analysis, or review:
- roadmap, status, or navigation wording that names a Research Dashboard but is not tied to a concrete runtime surface
- generic dashboard language without a bounded route, mount, or named research-only UI surface
- standalone analytics outputs, metrics reports, or performance summaries
- standalone chart panels, visual-analysis widgets, or chart data contracts
- operator-dashboard, trading-desk, or broader `/ui` documentation that is not explicitly bounded as the Research Dashboard
- endpoint lists, schemas, or data models that could support a dashboard but do not prove a dashboard surface exists
- tests that only cover underlying data endpoints or analytics logic without checking a bounded dashboard surface

The following existing repository surfaces must not be treated as implied Phase 23 implementation evidence unless they are explicitly extended and documented as the bounded Research Dashboard defined above:
- current operator `/ui` surfaces
- existing analytics artifacts or metrics reports
- current charting or visual-analysis surfaces
- trading-desk or operator-dashboard wording in roadmap or navigation documents

## Explicit Declaration
As of this revision, no repository-verifiable code, tests, or runtime documentation were confirmed for the bounded Phase 23 Research Dashboard defined in this file.
Phase 23 therefore remains NOT IMPLEMENTED.
