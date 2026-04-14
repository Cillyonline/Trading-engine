from __future__ import annotations

import json
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

import api.main as api_main

OPERATOR_HEADERS = {api_main.ROLE_HEADER_NAME: "operator"}
READ_ONLY_HEADERS = {api_main.ROLE_HEADER_NAME: "read_only"}


class _RuntimeControllerStub:
    def __init__(self, state: str) -> None:
        self.state = state


@dataclass
class _WatchlistRecord:
    watchlist_id: str
    name: str
    symbols: list[str]


class _InMemorySignalRepo:
    def __init__(self) -> None:
        self._signals: list[dict[str, Any]] = []


    def save_signals(self, signals: list[dict[str, Any]]) -> None:
        self._signals.extend(dict(item) for item in signals)


    def read_signals(
        self,
        *,
        symbol: str | None = None,
        strategy: str | None = None,
        timeframe: str | None = None,
        ingestion_run_id: str | None = None,
        from_: datetime | None = None,
        to: datetime | None = None,
        sort: str = "created_at_desc",
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        del from_, to, timeframe
        items = list(self._signals)
        if ingestion_run_id is not None:
            items = [item for item in items if item.get("ingestion_run_id") == ingestion_run_id]
        if symbol is not None:
            items = [item for item in items if item.get("symbol") == symbol]
        if strategy is not None:
            items = [item for item in items if item.get("strategy") == strategy]
        reverse = sort != "created_at_asc"
        items.sort(key=lambda item: str(item.get("timestamp", "")), reverse=reverse)
        total = len(items)
        return items[offset : offset + limit], total


class _InMemoryAnalysisRunRepo:
    def __init__(self) -> None:
        self._runs: dict[str, dict[str, Any]] = {}


    def get_run(self, analysis_run_id: str) -> dict[str, Any] | None:
        return self._runs.get(analysis_run_id)


    def save_run(
        self,
        *,
        analysis_run_id: str,
        ingestion_run_id: str,
        request_payload: dict[str, Any],
        result_payload: dict[str, Any],
    ) -> dict[str, Any]:
        payload = {
            "analysis_run_id": analysis_run_id,
            "ingestion_run_id": ingestion_run_id,
            "request": dict(request_payload),
            "result": dict(result_payload),
        }
        self._runs[analysis_run_id] = payload
        return payload


class _InMemoryWatchlistRepo:
    def __init__(self) -> None:
        self._items: dict[str, _WatchlistRecord] = {}


    def create_watchlist(self, *, watchlist_id: str, name: str, symbols: list[str]) -> _WatchlistRecord:
        if watchlist_id in self._items:
            raise ValueError("watchlist_id_exists")
        record = _WatchlistRecord(watchlist_id=watchlist_id, name=name, symbols=list(symbols))
        self._items[watchlist_id] = record
        return _WatchlistRecord(**record.__dict__)


    def list_watchlists(self) -> list[_WatchlistRecord]:
        return [
            _WatchlistRecord(watchlist_id=item.watchlist_id, name=item.name, symbols=list(item.symbols))
            for item in self._items.values()
        ]


    def get_watchlist(self, watchlist_id: str) -> _WatchlistRecord | None:
        item = self._items.get(watchlist_id)
        if item is None:
            return None
        return _WatchlistRecord(watchlist_id=item.watchlist_id, name=item.name, symbols=list(item.symbols))


    def update_watchlist(self, *, watchlist_id: str, name: str, symbols: list[str]) -> _WatchlistRecord:
        if watchlist_id not in self._items:
            raise KeyError(watchlist_id)
        record = _WatchlistRecord(watchlist_id=watchlist_id, name=name, symbols=list(symbols))
        self._items[watchlist_id] = record
        return _WatchlistRecord(**record.__dict__)


    def delete_watchlist(self, watchlist_id: str) -> bool:
        if watchlist_id not in self._items:
            return False
        del self._items[watchlist_id]
        return True


def _make_isolated_sqlite_tmp_path() -> Path:
    base_dir = Path.cwd() / "tests" / "pytest_tmp"
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / f"ui-runtime-browser-flow-{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    return path


def _insert_ingestion_run(
    db_path: Path,
    ingestion_run_id: str,
    *,
    symbols: list[str],
    timeframe: str = "D1",
) -> None:
    del db_path, ingestion_run_id, symbols, timeframe


def _insert_snapshot_rows(
    db_path: Path,
    ingestion_run_id: str,
    symbol: str,
    timeframe: str,
    rows: list[tuple[int, float, float, float, float, float]],
) -> None:
    del db_path, ingestion_run_id, symbol, timeframe, rows


class _ScoreFromCloseStrategy:
    name = "WATCHLIST_FAKE"

    def generate_signals(self, df: Any, config: dict[str, Any]) -> list[dict[str, Any]]:
        last_row = df.iloc[-1]
        return [
            {
                "score": float(last_row["volume"]),
                "signal_strength": float(last_row["close"]),
                "stage": "setup",
            }
        ]


def test_ui_browser_flow_uses_existing_runtime_api_surface(monkeypatch) -> None:
    tmp_path = _make_isolated_sqlite_tmp_path()
    try:
        monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")
        monkeypatch.setattr(api_main, "get_runtime_controller", lambda: _RuntimeControllerStub("running"))
        signal_repo = _InMemorySignalRepo()
        analysis_repo = _InMemoryAnalysisRunRepo()
        watchlist_repo = _InMemoryWatchlistRepo()

        monkeypatch.setattr(api_main, "signal_repo", signal_repo)
        monkeypatch.setattr(api_main, "analysis_run_repo", analysis_repo)
        monkeypatch.setattr(api_main, "watchlist_repo", watchlist_repo)
        monkeypatch.setattr(api_main, "_require_engine_runtime_running", lambda: None)
        monkeypatch.setattr(api_main, "_require_ingestion_run", lambda *args, **kwargs: None)
        monkeypatch.setattr(api_main, "_require_snapshot_ready", lambda *args, **kwargs: None)
        monkeypatch.setattr(api_main, "_resolve_analysis_db_path", lambda: str(tmp_path / "analysis.db"))
        monkeypatch.setattr(api_main, "create_registered_strategies", lambda: [_ScoreFromCloseStrategy()])
        monkeypatch.setattr(api_main, "trigger_operator_analysis_run", lambda execute, execute_kwargs, **kwargs: execute(**execute_kwargs))

        def _run_snapshot_analysis_stub(
            *,
            symbols: list[str],
            strategies: list[Any],
            engine_config: Any,
            strategy_configs: dict[str, dict[str, Any]],
            signal_repo: _InMemorySignalRepo,
            ingestion_run_id: str,
            db_path: str,
            run_id: str | None = None,
            symbol_failures: list[dict[str, str]] | None = None,
            isolate_symbol_failures: bool = False,
        ) -> list[dict[str, Any]]:
            del strategies, engine_config, strategy_configs, db_path, symbol_failures, isolate_symbol_failures
            now = datetime.now(timezone.utc).isoformat()
            score_map = {
                "AAPL": (81.0, 81.0),
                "MSFT": (72.0, 72.0),
                "NVDA": (96.0, 96.0),
            }
            output: list[dict[str, Any]] = []
            for symbol in symbols:
                score, signal_strength = score_map.get(symbol, (50.0, 50.0))
                output.append(
                    {
                        "signal_id": f"{run_id or ingestion_run_id}-{symbol}",
                        "analysis_run_id": run_id,
                        "ingestion_run_id": ingestion_run_id,
                        "symbol": symbol,
                        "strategy": "RSI2" if symbol == "AAPL" else "WATCHLIST_FAKE",
                        "direction": "long",
                        "score": score,
                        "signal_strength": signal_strength,
                        "timestamp": now,
                        "stage": "setup",
                        "timeframe": "D1",
                        "market_type": "stock",
                        "data_source": "yahoo",
                    }
                )
            signal_repo.save_signals(output)
            return output

        monkeypatch.setattr(api_main, "_run_snapshot_analysis", _run_snapshot_analysis_stub)

        ingestion_run_id = str(uuid.uuid4())
        _insert_ingestion_run(
            tmp_path / "analysis.db",
            ingestion_run_id,
            symbols=["AAPL", "MSFT", "NVDA"],
        )
        _insert_snapshot_rows(
            tmp_path / "analysis.db",
            ingestion_run_id,
            "AAPL",
            "D1",
            [
                (1735689600000, 101.0, 102.0, 100.0, 101.0, 1000.0),
                (1735776000000, 100.0, 101.0, 90.0, 91.0, 1000.0),
                (1735862400000, 90.0, 91.0, 80.0, 81.0, 1000.0),
            ],
        )
        _insert_snapshot_rows(
            tmp_path / "analysis.db",
            ingestion_run_id,
            "MSFT",
            "D1",
            [
                (1735689600000, 201.0, 202.0, 200.0, 201.0, 70.0),
                (1735776000000, 205.0, 206.0, 204.0, 205.0, 72.0),
            ],
        )
        _insert_snapshot_rows(
            tmp_path / "analysis.db",
            ingestion_run_id,
            "NVDA",
            "D1",
            [
                (1735689600000, 301.0, 302.0, 300.0, 301.0, 95.0),
                (1735776000000, 306.0, 307.0, 305.0, 306.0, 96.0),
            ],
        )

        monkeypatch.setattr(
            api_main,
            "get_system_state_payload",
            lambda: {
                "schema_version": "v1",
                "status": "running",
                    "runtime": {
                        "schema_version": "v1",
                        "runtime_id": "runtime-ui-flow",
                        "mode": "running",
                        "timestamps": {
                            "started_at": "2025-01-01T00:00:00+00:00",
                            "updated_at": "2025-01-01T00:00:00+00:00",
                        },
                        "ownership": {"owner_tag": "engine"},
                        "extensions": [],
                    },
                "metadata": {
                    "read_only": True,
                    "source": "engine_control_plane",
                },
            },
        )

        def _fail_yahoo(*args, **kwargs):
            raise AssertionError("yfinance should not be called")

        def _fail_binance(*args, **kwargs):
            raise AssertionError("ccxt should not be called")

        monkeypatch.setattr("cilly_trading.engine.data._load_stock_yahoo", _fail_yahoo)
        monkeypatch.setattr("cilly_trading.engine.data._load_crypto_binance", _fail_binance)

        with TestClient(api_main.app) as client:
            ui_response = client.get("/ui")
            assert ui_response.status_code == 200
            assert "Bounded Website-Facing Workflow Shell" in ui_response.text
            assert "single canonical website-facing workflow entrypoint" in ui_response.text
            assert 'id="ui-primary-navigation-contract"' in ui_response.text
            assert 'id="ui-workflow-boundary-marker"' in ui_response.text
            assert "No live trading" in ui_response.text
            assert "broker execution controls" in ui_response.text
            assert "operational-readiness inference" in ui_response.text
            assert "/system/state" in ui_response.text
            assert 'roleHeaderName="X-Cilly-Role"' in ui_response.text
            assert 'readOnlyHeaders={[roleHeaderName]:"read_only"}' in ui_response.text
            assert 'operatorHeaders={[roleHeaderName]:"operator"}' in ui_response.text
            assert "/analysis/run" in ui_response.text
            assert "/alerts/history" in ui_response.text
            assert 'id="alert-status"' in ui_response.text
            assert 'id="alert-list"' in ui_response.text
            assert "No Phase 39 or Phase 40 features" in ui_response.text
            assert 'id="runtime-chart-panel"' not in ui_response.text
            assert "phase39-visual-analysis" not in ui_response.text
            assert "/signals?limit=20&sort=created_at_desc" in ui_response.text
            assert "/watchlists" in ui_response.text
            assert "/watchlists/{watchlist_id}" in ui_response.text
            assert "/watchlists/{watchlist_id}/execute" in ui_response.text
            assert 'id="watchlist-form"' in ui_response.text
            assert 'id="watchlist-ranked-result-list"' in ui_response.text
            assert "Workflow: Inspect Backtest Artifacts" in ui_response.text
            assert "Backtest Entry/Read Panel" in ui_response.text
            assert 'id="backtest-entry-read-form"' in ui_response.text
            assert 'id="backtest-artifact-list"' in ui_response.text
            assert "/backtest/artifacts" in ui_response.text
            assert "/backtest/artifacts/{run_id}/{artifact_name}" in ui_response.text
            assert "Technical availability of bounded backtest artifacts is not trader validation." in ui_response.text
            assert "does not establish operational readiness or live execution readiness." in ui_response.text

            state_response = client.get("/system/state", headers=READ_ONLY_HEADERS)
            assert state_response.status_code == 200
            assert state_response.json()["status"] == "running"

            analysis_response = client.post(
                "/analysis/run",
                headers=OPERATOR_HEADERS,
                json={
                    "ingestion_run_id": ingestion_run_id,
                    "symbol": "AAPL",
                    "strategy": "RSI2",
                    "market_type": "stock",
                    "lookback_days": 200,
                },
            )
            assert analysis_response.status_code == 200
            analysis_payload = analysis_response.json()
            assert analysis_payload["analysis_run_id"]
            assert analysis_payload["signals"]

            signals_response = client.get(
                "/signals",
                headers=READ_ONLY_HEADERS,
                params={
                    "ingestion_run_id": ingestion_run_id,
                    "symbol": "AAPL",
                    "sort": "created_at_desc",
                },
            )
            assert signals_response.status_code == 200
            signals_payload = signals_response.json()
            assert signals_payload["total"] >= 1
            assert any(item["symbol"] == "AAPL" for item in signals_payload["items"])

            create_watchlist_response = client.post(
                "/watchlists",
                headers=OPERATOR_HEADERS,
                json={
                    "watchlist_id": "phase37-tech",
                    "name": "Phase 37 Tech",
                    "symbols": ["MSFT", "NVDA"],
                },
            )
            assert create_watchlist_response.status_code == 200
            assert create_watchlist_response.json()["watchlist_id"] == "phase37-tech"

            list_watchlists_response = client.get("/watchlists", headers=READ_ONLY_HEADERS)
            assert list_watchlists_response.status_code == 200
            assert list_watchlists_response.json()["total"] == 1

            update_watchlist_response = client.put(
                "/watchlists/phase37-tech",
                headers=OPERATOR_HEADERS,
                json={
                    "name": "Phase 37 Ranked Tech",
                    "symbols": ["NVDA", "MSFT"],
                },
            )
            assert update_watchlist_response.status_code == 200
            assert update_watchlist_response.json()["name"] == "Phase 37 Ranked Tech"

            read_watchlist_response = client.get(
                "/watchlists/phase37-tech",
                headers=READ_ONLY_HEADERS,
            )
            assert read_watchlist_response.status_code == 200
            assert read_watchlist_response.json()["symbols"] == ["NVDA", "MSFT"]

            execute_watchlist_response = client.post(
                "/watchlists/phase37-tech/execute",
                headers=OPERATOR_HEADERS,
                json={
                    "ingestion_run_id": ingestion_run_id,
                    "market_type": "stock",
                    "lookback_days": 200,
                    "min_score": 60.0,
                },
            )
            assert execute_watchlist_response.status_code == 200
            execute_payload = execute_watchlist_response.json()
            assert execute_payload["watchlist_id"] == "phase37-tech"
            assert execute_payload["watchlist_name"] == "Phase 37 Ranked Tech"
            assert [item["symbol"] for item in execute_payload["ranked_results"]] == ["NVDA", "MSFT"]
            assert [item["rank"] for item in execute_payload["ranked_results"]] == [1, 2]
            assert execute_payload["failures"] == []

            delete_watchlist_response = client.delete(
                "/watchlists/phase37-tech",
                headers=OPERATOR_HEADERS,
            )
            assert delete_watchlist_response.status_code == 200
            assert delete_watchlist_response.json() == {
                "watchlist_id": "phase37-tech",
                "deleted": True,
            }
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)
