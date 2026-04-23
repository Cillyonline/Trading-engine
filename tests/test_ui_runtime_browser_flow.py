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
            assert 'id="ui-signal-review-workflow-contract"' in ui_response.text
            assert "Bounded Signal Review and Trade-Evaluation Workflow (Non-live)" in ui_response.text
            assert "technical signals and evaluate trade candidates through non-live runtime evidence" in ui_response.text
            assert "Technical signal visibility is explicitly separate from trader validation and operational readiness decisions." in ui_response.text
            assert "Signal Review Workflow Step 1: Run Analysis" in ui_response.text
            assert "Signal Review Workflow Step 2: Configure Watchlist Scope" in ui_response.text
            assert "Signal Review Workflow Step 3: Evaluate Ranked Signals" in ui_response.text
            assert "Signal Review Workflow Step 4: Inspect Backtest Artifacts" in ui_response.text
            assert "Signal Review Workflow Step 5: Inspect Runtime Data" in ui_response.text
            assert "Signal Review Workflow Step 6: Review Run Evidence" in ui_response.text
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
            assert "Bounded Phase 39 visual-analysis/charting markers coexist" in ui_response.text
            assert 'id="runtime-chart-panel"' in ui_response.text
            assert "phase39-visual-analysis" in ui_response.text
            assert "/signals/decision-surface?limit=20&sort=created_at_desc" in ui_response.text
            assert "Signal Decision Surface" in ui_response.text
            assert "decision_state" in ui_response.text
            assert "qualification_state" in ui_response.text
            assert "expected_value" in ui_response.text
            assert "qualification_policy_version" in ui_response.text
            assert "qualification_evidence" in ui_response.text
            assert "missing_criteria" in ui_response.text
            assert "blocking_conditions" in ui_response.text
            assert "blocked" in ui_response.text
            assert "watch" in ui_response.text
            assert "paper_candidate" in ui_response.text
            assert "/watchlists" in ui_response.text
            assert "/watchlists/{watchlist_id}" in ui_response.text
            assert "/watchlists/{watchlist_id}/execute" in ui_response.text
            assert 'id="watchlist-form"' in ui_response.text
            assert 'id="watchlist-ranked-result-list"' in ui_response.text
            assert "Signal Review Workflow Step 4: Inspect Backtest Artifacts" in ui_response.text
            assert "Backtest Entry/Read Panel" in ui_response.text
            assert 'id="backtest-entry-read-form"' in ui_response.text
            assert 'id="backtest-artifact-list"' in ui_response.text
            assert "/backtest/artifacts" in ui_response.text
            assert "/backtest/artifacts/{run_id}/{artifact_name}" in ui_response.text
            assert "Technical availability of bounded backtest artifacts is not trader validation." in ui_response.text
            assert "does not establish operational readiness or live execution readiness." in ui_response.text
            assert "strategy_readiness_evidence" in ui_response.text
            assert "inferred_readiness_claim" in ui_response.text
            assert "Inferred readiness claim:" in ui_response.text

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

            decision_surface_response = client.get(
                "/signals/decision-surface",
                headers=READ_ONLY_HEADERS,
                params={
                    "ingestion_run_id": ingestion_run_id,
                    "symbol": "AAPL",
                    "sort": "created_at_desc",
                },
            )
            assert decision_surface_response.status_code == 200
            decision_surface_payload = decision_surface_response.json()
            assert decision_surface_payload["items"]
            assert decision_surface_payload["boundary"]["mode"] == "non_live_signal_decision_surface"
            assert (
                decision_surface_payload["boundary"]["strategy_readiness_evidence"]["inferred_readiness_claim"]
                == "prohibited"
            )
            decision_item = decision_surface_payload["items"][0]
            assert decision_item["decision_state"] in {"blocked", "watch", "paper_candidate"}
            assert decision_item["qualification_state"] in {
                "reject",
                "watch",
                "paper_candidate",
                "paper_approved",
            }
            assert decision_item["action"] in {"entry", "exit", "ignore"}
            assert decision_item["qualification_policy_version"] == "professional_non_live_signal_qualification.v1"
            assert isinstance(decision_item["win_rate"], float)
            assert isinstance(decision_item["expected_value"], float)
            assert isinstance(decision_item["qualification_evidence"], list)
            assert "score" in decision_item["score_contribution"].lower()
            assert "stage" in decision_item["stage_assessment"].lower()

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


def test_ui_consolidated_operator_workflow_walks_canonical_read_surfaces(monkeypatch) -> None:
    """Deterministic browser-flow regression for the consolidated bounded
    operator workflow: watchlist -> analysis -> decision review -> backtest
    evidence. Asserts the consolidated workflow consumes only existing
    canonical read surfaces and that consolidated UI markers are present."""

    tmp_path = _make_isolated_sqlite_tmp_path()
    try:
        backtest_root = tmp_path / "runs" / "phase6"
        run_dir = backtest_root / "bt-run-consolidated"
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "backtest-result.json").write_text(
            json.dumps({"run": {"run_id": "bt-run-consolidated"}, "summary": {"total_trades": 1}}),
            encoding="utf-8",
        )

        monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")
        monkeypatch.setattr(api_main, "get_runtime_controller", lambda: _RuntimeControllerStub("running"))
        monkeypatch.setattr(api_main, "JOURNAL_ARTIFACTS_ROOT", backtest_root)

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
        monkeypatch.setattr(
            api_main,
            "trigger_operator_analysis_run",
            lambda execute, execute_kwargs, **kwargs: execute(**execute_kwargs),
        )

        def _run_snapshot_analysis_stub(
            *,
            symbols,
            strategies,
            engine_config,
            strategy_configs,
            signal_repo,
            ingestion_run_id,
            db_path,
            run_id=None,
            symbol_failures=None,
            isolate_symbol_failures=False,
        ):
            del strategies, engine_config, strategy_configs, db_path, symbol_failures, isolate_symbol_failures
            now = datetime.now(timezone.utc).isoformat()
            output = []
            for index, symbol in enumerate(symbols):
                output.append(
                    {
                        "signal_id": f"{run_id or ingestion_run_id}-{symbol}",
                        "analysis_run_id": run_id,
                        "ingestion_run_id": ingestion_run_id,
                        "symbol": symbol,
                        "strategy": "RSI2",
                        "direction": "long",
                        "score": 80.0 - index,
                        "signal_strength": 80.0 - index,
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
        monkeypatch.setattr(
            api_main,
            "get_system_state_payload",
            lambda: {
                "schema_version": "v1",
                "status": "running",
                "runtime": {
                    "schema_version": "v1",
                    "runtime_id": "runtime-ui-consolidated",
                    "mode": "running",
                    "timestamps": {
                        "started_at": "2025-01-01T00:00:00+00:00",
                        "updated_at": "2025-01-01T00:00:00+00:00",
                    },
                    "ownership": {"owner_tag": "engine"},
                    "extensions": [],
                },
                "metadata": {"read_only": True, "source": "engine_control_plane"},
            },
        )

        with TestClient(api_main.app) as client:
            ui_response = client.get("/ui")
            assert ui_response.status_code == 200
            ui_text = ui_response.text

            # Consolidated workflow UI markers must be present.
            assert 'id="ui-consolidated-operator-workflow"' in ui_text
            assert 'id="ui-consolidated-operator-workflow-steps"' in ui_text
            assert 'id="ui-consolidated-operator-workflow-non-live-boundary"' in ui_text
            assert 'id="ui-consolidated-operator-workflow-canonical-reads"' in ui_text
            assert 'id="decision-review"' in ui_text
            assert "Consolidated Bounded Operator Workflow" in ui_text

            # Steps must appear in canonical order: watchlist -> analysis ->
            # decision review -> backtest evidence.
            order = [
                ui_text.index("Step 1 &middot; Watchlist:"),
                ui_text.index("Step 2 &middot; Analysis:"),
                ui_text.index("Step 3 &middot; Decision Review:"),
                ui_text.index("Step 4 &middot; Backtest Evidence:"),
            ]
            assert order == sorted(order)

            # Each consolidated step must deep-link to an existing /ui section
            # backed by an existing canonical read surface.
            for href in (
                'href="#watchlist-workflow"',
                'href="#analysis-entry"',
                'href="#decision-review"',
                'href="#backtest-entry"',
            ):
                assert href in ui_text

            # Non-live boundary text must be preserved by the consolidation.
            assert "does not introduce live trading" in ui_text
            assert "broker integration" in ui_text
            assert "strategy optimization" in ui_text

            ingestion_run_id = str(uuid.uuid4())

            # Step 1 - Watchlist: persist scope through canonical /watchlists.
            create_response = client.post(
                "/watchlists",
                headers=OPERATOR_HEADERS,
                json={
                    "watchlist_id": "consolidated-flow",
                    "name": "Consolidated Flow",
                    "symbols": ["AAPL", "MSFT"],
                },
            )
            assert create_response.status_code == 200
            list_response = client.get("/watchlists", headers=READ_ONLY_HEADERS)
            assert list_response.status_code == 200
            assert list_response.json()["total"] == 1

            # Step 2 - Analysis: run bounded analysis through canonical
            # /watchlists/{watchlist_id}/execute (consumes /analysis surfaces).
            execute_response = client.post(
                "/watchlists/consolidated-flow/execute",
                headers=OPERATOR_HEADERS,
                json={
                    "ingestion_run_id": ingestion_run_id,
                    "market_type": "stock",
                    "lookback_days": 200,
                    "min_score": 0.0,
                },
            )
            assert execute_response.status_code == 200
            execute_payload = execute_response.json()
            assert execute_payload["watchlist_id"] == "consolidated-flow"
            assert {item["symbol"] for item in execute_payload["ranked_results"]} == {"AAPL", "MSFT"}

            # Step 3 - Decision Review: read bounded technical decision surface.
            decision_response = client.get(
                "/signals/decision-surface",
                headers=READ_ONLY_HEADERS,
                params={"ingestion_run_id": ingestion_run_id, "sort": "created_at_desc"},
            )
            assert decision_response.status_code == 200
            decision_payload = decision_response.json()
            assert decision_payload["items"], "decision review must surface reviewed signals"
            assert (
                decision_payload["boundary"]["mode"] == "non_live_signal_decision_surface"
            )
            for item in decision_payload["items"]:
                assert item["decision_state"] in {"blocked", "watch", "paper_candidate"}

            # Step 4 - Backtest Evidence: read bounded backtest artifacts.
            backtest_list_response = client.get(
                "/backtest/artifacts",
                headers=READ_ONLY_HEADERS,
            )
            assert backtest_list_response.status_code == 200
            backtest_payload = backtest_list_response.json()
            assert backtest_payload["workflow_id"] == "ui_bounded_backtest_entry_read"
            assert backtest_payload["boundary"]["mode"] == "non_live_backtest_read_only"
            assert backtest_payload["total"] == 1
            assert backtest_payload["items"][0]["run_id"] == "bt-run-consolidated"

            backtest_content_response = client.get(
                "/backtest/artifacts/bt-run-consolidated/backtest-result.json",
                headers=READ_ONLY_HEADERS,
            )
            assert backtest_content_response.status_code == 200
            assert (
                backtest_content_response.json()["run_id"] == "bt-run-consolidated"
            )
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)
