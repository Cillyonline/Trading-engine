from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from cilly_trading.db import DEFAULT_DB_PATH
from cilly_trading.repositories.analysis_runs_sqlite import SqliteAnalysisRunRepository
from cilly_trading.repositories.execution_core_sqlite import SqliteCanonicalExecutionRepository
from cilly_trading.repositories.signals_sqlite import SqliteSignalRepository
from cilly_trading.repositories.watchlists_sqlite import SqliteWatchlistRepository

from ..order_events_sqlite import SqliteOrderEventRepository


@dataclass(frozen=True)
class ApiRepositories:
    signal_repo: SqliteSignalRepository
    order_event_repo: SqliteOrderEventRepository
    canonical_execution_repo: SqliteCanonicalExecutionRepository
    analysis_run_repo: SqliteAnalysisRunRepository
    watchlist_repo: SqliteWatchlistRepository


def create_api_repositories(*, default_db_path: Path = DEFAULT_DB_PATH) -> ApiRepositories:
    return ApiRepositories(
        signal_repo=SqliteSignalRepository(),
        order_event_repo=SqliteOrderEventRepository(db_path=default_db_path),
        canonical_execution_repo=SqliteCanonicalExecutionRepository(db_path=default_db_path),
        analysis_run_repo=SqliteAnalysisRunRepository(db_path=default_db_path),
        watchlist_repo=SqliteWatchlistRepository(db_path=default_db_path),
    )
