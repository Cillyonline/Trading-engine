# Operator Dashboard Runtime Surface

## Overview
The operator dashboard runtime surface is the backend-served workbench at `/ui`.

This surface is served from `src/ui/index.html` by the backend static mount and is the authoritative operator-facing UI entrypoint at runtime.

If the React frontend remains in local development use, its `/owner` route is a development-only surface. It is not the backend-served runtime dashboard and must not be treated as interchangeable with `/ui`.

The canonical Phase 36 browser runtime contract is documented in `docs/ui/phase-36-web-activation-contract.md`. This document remains the runtime-surface inventory for the current operator workbench.

## Runtime Route
- **Runtime route:** `/ui`
- **Served by:** backend runtime static UI mount
- **Authoritative source:** `src/ui/index.html`

## Runtime Workbench Contents
The current runtime-served `/ui` workbench exposes the following sections:

- Overview
- Runtime Status
- Analysis Runs
- Strategy List
- Signals
- Journal Artifacts
- Decision Trace
- Screener
- Trade Lifecycle
- Audit Trail

The page header labels this surface as **Operator Workbench** and explicitly states that it is served by FastAPI at `/ui`.

For Phase 36 scope and phase-boundary decisions, treat the canonical contract document as authoritative. The list below is a description of the current runtime shell contents, not a claim that every visible section already has a complete browser workflow.

## Runtime Data Surfaces
The runtime workbench currently renders or reserves space for these backend-connected surfaces:

| Workbench area | Runtime behavior |
| --- | --- |
| Strategy List | Read-only metadata fetched from `/strategies` |
| Signals | Read-only latest signal list fetched from `/signals` |
| Journal Artifacts | Read-only artifact browser fetched from `/journal/artifacts` |
| Decision Trace | Read-only trace viewer fetched from `/journal/decision-trace` |
| Trade Lifecycle | Read-only order lifecycle viewer fetched from `/execution/orders` |
| Overview / Runtime Status / Analysis Runs / Screener / Audit Trail | Present in the runtime UI shell, with placeholder or reserved content in the current static page |

## Development-Only Frontend Surface
The frontend route structure in `frontend/src/App.tsx` defines `/owner` as a React route that renders `frontend/src/pages/OwnerDashboard.tsx`.

That route is a development-only frontend surface:

- It exists in the frontend dev server route structure.
- It is not the backend-served runtime entrypoint.
- It must not be cited as the production or runtime dashboard URL.
- It is only relevant when documenting local frontend development behavior.

## Route Distinction
| Route | Environment | Purpose |
| --- | --- | --- |
| `/ui` | Backend runtime | Authoritative operator dashboard surface served in runtime |
| `/owner` | Frontend development server | Development-only React page for local frontend work |

`/ui` and `/owner` are not interchangeable routes.

## Manual Review Checklist
Use this checklist for documentation review against the actual surfaces:

1. Confirm `src/ui/index.html` identifies the runtime-served UI as `/ui`.
2. Confirm the runtime page content matches the workbench sections listed in this document.
3. Confirm `frontend/src/App.tsx` defines `/owner` only in the frontend route structure.
4. Confirm no operator-facing documentation treats `/owner` as a backend runtime URL.
5. Confirm no operator-facing documentation treats `/ui` and `/owner` as equivalent entrypoints.

## Verification Outcome
A reviewer comparing this document to `src/ui/index.html` and the frontend route structure should find:

- `/ui` is the runtime-served operator surface.
- `/owner` is only a development-only frontend route if referenced.
- There is no route ambiguity between runtime and development surfaces.
