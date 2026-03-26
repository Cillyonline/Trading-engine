# ARCH-P45A API Module Split

Issue: `#775`  
Date: `2026-03-24`  
Updated: `2026-03-26` (`#790`)

## Summary

`src/api/main.py` is now a composition root focused on:

- app creation
- static `/ui` mount
- bounded dependency/repository wiring
- router inclusion

Runtime lifecycle registration and mutable app-state setup are delegated to explicit bounded modules:

- `src/api/composition/runtime_lifecycle.py`
- `src/api/composition/router_wiring.py`
- `src/api/state/alerts_state.py`

Bounded routers own transport handlers:

- `src/api/routers/control_plane_router.py`
- `src/api/routers/inspection_router.py`
- `src/api/routers/watchlists_router.py`
- `src/api/routers/analysis_router.py`

Bounded service modules own moved orchestration/helper logic:

- `src/api/services/composition_runtime_service.py`
- `src/api/services/control_plane_service.py`
- `src/api/services/inspection_service.py`
- `src/api/services/analysis_service.py`
- `src/api/services/paper_inspection_service.py`

API DTO/query model ownership moved from `main.py` into:

- `src/api/models/control_plane_models.py`
- `src/api/models/inspection_models.py`
- `src/api/models/watchlist_models.py`
- `src/api/models/analysis_models.py`

## Boundaries

- **Control-plane router**: health surfaces, compliance status, runtime/system state, execution lifecycle transport endpoints.
- **Inspection router**: portfolio/paper reads, ingestion run reads, journal/decision-card reads, strategy/signal/execution/trading-core reads.
- **Watchlists router**: watchlist CRUD and watchlist execution transport endpoints.
- **Analysis router**: strategy analysis, manual analysis trigger, and basic screener transport endpoints.
- **Services**: non-transport orchestration/helpers used by routers.
- **Models**: request/response/query DTO definitions.
- **Main module**: composition/wiring only (app, mount, dependency/repository wiring, router inclusion) plus compatibility symbol exports with no helper/transport implementations.
- **Composition modules**: runtime startup/shutdown registration and router inclusion wiring.
- **State modules**: mutable alert app-state initialization and access.

## Behavior

This split is structural only. Endpoint paths, auth semantics, payload schemas, status codes, lifecycle behavior, and `/ui` mounting remain unchanged.
