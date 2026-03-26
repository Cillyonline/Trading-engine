from __future__ import annotations

from pathlib import Path

import api.main as api_main


def test_analysis_service_dependencies_follow_main_patch_points(monkeypatch) -> None:
    signal_repo = object()
    analysis_run_repo = object()
    watchlist_repo = object()
    require_ingestion_run = lambda *_args, **_kwargs: None
    require_snapshot_ready = lambda *_args, **_kwargs: None
    run_snapshot_analysis = lambda *_args, **_kwargs: []

    monkeypatch.setattr(api_main, "signal_repo", signal_repo)
    monkeypatch.setattr(api_main, "analysis_run_repo", analysis_run_repo)
    monkeypatch.setattr(api_main, "watchlist_repo", watchlist_repo)
    monkeypatch.setattr(api_main, "_require_ingestion_run", require_ingestion_run)
    monkeypatch.setattr(api_main, "_require_snapshot_ready", require_snapshot_ready)
    monkeypatch.setattr(api_main, "_run_snapshot_analysis", run_snapshot_analysis)

    deps = api_main._analysis_service_dependencies()

    assert deps.signal_repo is signal_repo
    assert deps.analysis_run_repo is analysis_run_repo
    assert deps.watchlist_repo is watchlist_repo
    assert deps.require_ingestion_run is require_ingestion_run
    assert deps.require_snapshot_ready is require_snapshot_ready
    assert deps.run_snapshot_analysis is run_snapshot_analysis


def test_resolve_analysis_db_path_follows_main_override(monkeypatch) -> None:
    analysis_db_path = Path("patched-analysis.db")

    monkeypatch.setattr(api_main, "ANALYSIS_DB_PATH", analysis_db_path)

    assert api_main._resolve_analysis_db_path() == str(analysis_db_path)
