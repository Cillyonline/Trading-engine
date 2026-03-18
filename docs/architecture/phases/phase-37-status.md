# Phase 37 - Watchlist Engine Status

Status: Implemented in Repository  
Scope: Repository-verified watchlist persistence, CRUD API, execution/ranking workflow, and bounded `/ui` watchlist surface  
Owner: Governance

## Purpose
This file is the canonical Phase 37 status and contract artifact for the repository-verified watchlist workflow.

It documents only the Phase 37 behavior that is verifiable in the current repository through code, runtime-facing docs, and tests.

## Verified Phase 37 Scope

### Persistence boundary
- SQLite-backed watchlist persistence exists through `cilly_trading.repositories.watchlists_sqlite.SqliteWatchlistRepository`.
- Stored watchlists preserve deterministic symbol ordering.
- Create and update paths reject invalid or conflicting payloads without partial persistence.

### API boundary
- `POST /watchlists` creates a saved watchlist.
- `GET /watchlists` lists saved watchlists deterministically.
- `GET /watchlists/{watchlist_id}` reads one saved watchlist.
- `PUT /watchlists/{watchlist_id}` replaces a saved watchlist name and membership.
- `DELETE /watchlists/{watchlist_id}` deletes a saved watchlist.
- `POST /watchlists/{watchlist_id}/execute` runs snapshot-only analysis for a saved watchlist and returns deterministic ranked results plus isolated symbol failures.

### Runtime `/ui` boundary
- The backend-served runtime page at `/ui` includes watchlist management and execution markers.
- The page references the implemented watchlist CRUD and execution routes.
- The browser workflow remains bounded to watchlist management/execution on the existing operator workbench rather than implying later trading-desk scope.

## Repository Evidence

| Area | Repository evidence |
| --- | --- |
| Persistence implementation | `src/cilly_trading/repositories/watchlists_sqlite.py` |
| API request/response models and endpoints | `src/api/main.py` |
| Runtime `/ui` watchlist shell markers | `src/ui/index.html` |
| Repository CRUD tests | `tests/test_watchlist_repository_sqlite.py` |
| API CRUD and execution tests | `tests/test_api_watchlists.py` |
| Runtime `/ui` watchlist markers | `src/api/test_operator_workbench_surface.py` |
| Runtime browser workflow using watchlist APIs | `tests/test_ui_runtime_browser_flow.py` |

## Verified Behavior

### Watchlist persistence and CRUD
- Watchlists are stored with `watchlist_id`, human-readable `name`, and ordered `symbols`.
- Repository and API validation reject duplicate identifiers, duplicate names, empty symbol members, and invalid update operations.
- Read paths are deterministic and return stable symbol order.

### Watchlist execution and ranking
- Watchlist execution is snapshot-only and requires `ingestion_run_id`.
- Ranking is returned through `ranked_results`.
- Symbol-level snapshot failures are isolated into `failures` instead of failing the full request when the request itself is otherwise valid.
- The endpoint reuses persisted analysis-run artifacts when the deterministic execution identity already exists.

### `/ui` watchlist behavior
- The current `/ui` workbench includes watchlist management, execution, ranked-results, and failure-list panels.
- The runtime browser flow covers create, list, update, read, execute, and delete behavior against the watchlist API surface.

## Explicit Boundaries
- Phase 37 does not claim market-data provider expansion beyond the current snapshot/runtime behavior.
- Phase 37 does not claim Phase 39 charting or visual-analysis features.
- Phase 37 does not claim Phase 40 trading-desk, leaderboard, heatmap, or richer dashboard capability.
- Phase 37 does not claim alerts, paper-trading product workflows, or live-trading product scope.

## Documentation Alignment Rule
When Phase 37 status is referenced elsewhere in `docs/**`, that wording should align to this file and to the authoritative roadmap entry in `docs/architecture/roadmap/execution_roadmap.md`.
