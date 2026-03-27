# Phase 37 - Watchlist Engine Status

Status: Implemented in Repository  
Scope: Repository-verified watchlist persistence, CRUD API, execution/ranking workflow, and bounded `/ui` watchlist surface  
Owner: Governance

## Purpose
This file is the canonical Phase 37 status and contract artifact for repository-verified watchlist workflow.

## Verified Phase 37 Scope

### Persistence boundary
- SQLite-backed watchlist persistence exists through `cilly_trading.repositories.watchlists_sqlite.SqliteWatchlistRepository`.
- Stored watchlists preserve deterministic symbol ordering.
- Create and update paths reject invalid or conflicting payloads without partial persistence.

### API boundary
- `POST /watchlists`
- `GET /watchlists`
- `GET /watchlists/{watchlist_id}`
- `PUT /watchlists/{watchlist_id}`
- `DELETE /watchlists/{watchlist_id}`
- `POST /watchlists/{watchlist_id}/execute`

These endpoints provide deterministic watchlist CRUD and snapshot-only execution/ranking behavior.

### Runtime `/ui` boundary
- `/ui` includes watchlist management and execution markers.
- `/ui` references watchlist CRUD and execution routes.
- Browser workflow remains bounded to watchlist management/execution on the shared shell.

## Repository Evidence
| Area | Repository evidence |
| --- | --- |
| Persistence implementation | `src/cilly_trading/repositories/watchlists_sqlite.py` |
| API endpoints | `src/api/main.py` |
| Runtime `/ui` markers | `src/ui/index.html` |
| Repository CRUD tests | `tests/test_watchlist_repository_sqlite.py` |
| API CRUD/execution tests | `tests/test_api_watchlists.py` |
| Runtime `/ui` marker tests | `src/api/test_operator_workbench_surface.py` |
| Runtime browser flow tests | `tests/test_ui_runtime_browser_flow.py` |

## Explicit Boundaries
- Phase 37 does not claim Phase 39 chart-panel UI ownership.
- Phase 37 does not claim Phase 40 trading-desk completion.
- Phase 37 does not claim Phase 41 notification-delivery completion.
- Shared-shell sections such as alert history on `/ui` are non-authoritative for Phase 37 completion.

## Documentation Alignment Rule
Phase 37 references in `docs/**` must align to this file, `docs/architecture/roadmap/execution_roadmap.md`, and `docs/architecture/ui-runtime-phase-ownership-boundary.md`.

