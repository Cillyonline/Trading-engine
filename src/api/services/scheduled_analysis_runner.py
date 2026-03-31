from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Literal, Sequence

from fastapi import HTTPException

from cilly_trading.engine.core import canonical_json, sha256_hex
from cilly_trading.engine.data import SnapshotDataError, load_ohlcv_snapshot

from ..models import ManualAnalysisRequest, WatchlistExecutionRequest
from .analysis_service import (
    AnalysisServiceDependencies,
    execute_watchlist,
    manual_analysis,
)

logger = logging.getLogger(__name__)

TaskKind = Literal["analysis", "watchlist"]


def _normalize_identity_value(value: Any) -> Any:
    if isinstance(value, float):
        return format(value, ".10g")
    if isinstance(value, dict):
        return {key: _normalize_identity_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_identity_value(item) for item in value]
    return value


@dataclass(frozen=True)
class ScheduledTask:
    kind: TaskKind
    market_type: str = "stock"
    lookback_days: int = 200
    task_id: str | None = None
    symbol: str | None = None
    strategy: str | None = None
    strategy_config: dict[str, Any] | None = None
    watchlist_id: str | None = None
    min_score: float = 30.0

    @property
    def stable_task_id(self) -> str:
        if self.task_id:
            return self.task_id
        return sha256_hex(canonical_json(self.identity_payload()))

    def identity_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "kind": self.kind,
            "market_type": self.market_type,
            "lookback_days": self.lookback_days,
        }
        if self.kind == "analysis":
            payload["symbol"] = self.symbol
            payload["strategy"] = self.strategy
            payload["strategy_config"] = self.strategy_config or {}
        else:
            payload["watchlist_id"] = self.watchlist_id
            payload["min_score"] = self.min_score
        return _normalize_identity_value(payload)


def parse_scheduled_tasks(raw_tasks_json: str) -> tuple[ScheduledTask, ...]:
    if not raw_tasks_json.strip():
        return ()

    try:
        payload = json.loads(raw_tasks_json)
    except json.JSONDecodeError as exc:
        raise ValueError("scheduled analysis tasks JSON is invalid") from exc

    if not isinstance(payload, list):
        raise ValueError("scheduled analysis tasks JSON must be a list")

    tasks: list[ScheduledTask] = []
    seen_task_ids: set[str] = set()
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"scheduled task at index {index} must be an object")

        kind = item.get("kind")
        if kind not in {"analysis", "watchlist"}:
            raise ValueError(f"scheduled task at index {index} has unsupported kind")

        market_type = item.get("market_type", "stock")
        if market_type not in {"stock", "crypto"}:
            raise ValueError(f"scheduled task at index {index} has invalid market_type")

        lookback_days = item.get("lookback_days", 200)
        if not isinstance(lookback_days, int) or not (30 <= lookback_days <= 1000):
            raise ValueError(f"scheduled task at index {index} has invalid lookback_days")

        raw_task_id = item.get("task_id")
        task_id = None
        if raw_task_id is not None:
            if not isinstance(raw_task_id, str) or not raw_task_id.strip():
                raise ValueError(f"scheduled task at index {index} has invalid task_id")
            task_id = raw_task_id.strip()

        if kind == "analysis":
            symbol = item.get("symbol")
            strategy = item.get("strategy")
            if not isinstance(symbol, str) or not symbol.strip():
                raise ValueError(f"scheduled analysis task at index {index} requires symbol")
            if not isinstance(strategy, str) or not strategy.strip():
                raise ValueError(f"scheduled analysis task at index {index} requires strategy")

            strategy_config = item.get("strategy_config")
            if strategy_config is not None and not isinstance(strategy_config, dict):
                raise ValueError(
                    f"scheduled analysis task at index {index} has invalid strategy_config"
                )

            task = ScheduledTask(
                kind="analysis",
                task_id=task_id,
                symbol=symbol.strip(),
                strategy=strategy.strip(),
                strategy_config=strategy_config,
                market_type=market_type,
                lookback_days=lookback_days,
            )
        else:
            watchlist_id = item.get("watchlist_id")
            if not isinstance(watchlist_id, str) or not watchlist_id.strip():
                raise ValueError(f"scheduled watchlist task at index {index} requires watchlist_id")

            min_score = item.get("min_score", 30.0)
            if not isinstance(min_score, (int, float)) or not (0.0 <= float(min_score) <= 100.0):
                raise ValueError(f"scheduled watchlist task at index {index} has invalid min_score")

            task = ScheduledTask(
                kind="watchlist",
                task_id=task_id,
                watchlist_id=watchlist_id.strip(),
                min_score=float(min_score),
                market_type=market_type,
                lookback_days=lookback_days,
            )

        stable_task_id = task.stable_task_id
        if stable_task_id in seen_task_ids:
            raise ValueError("scheduled analysis tasks must have unique task identities")
        seen_task_ids.add(stable_task_id)
        tasks.append(task)

    return tuple(tasks)


@dataclass
class ScheduledAnalysisRunner:
    enabled: bool
    poll_interval_seconds: int
    snapshot_scan_limit: int
    raw_tasks_json: str
    build_analysis_service_dependencies: Callable[[], AnalysisServiceDependencies]
    get_runtime_controller: Callable[[], Any]
    resolve_analysis_db_path: Callable[[], str]
    logger: logging.Logger = field(default_factory=lambda: logger)
    sleep_wait: Callable[[threading.Event, float], bool] = field(
        default=lambda stop_event, seconds: stop_event.wait(seconds)
    )
    _tasks: tuple[ScheduledTask, ...] = field(init=False, repr=False)
    _stop_event: threading.Event = field(
        init=False,
        default_factory=threading.Event,
        repr=False,
    )
    _run_lock: threading.Lock = field(init=False, default_factory=threading.Lock, repr=False)
    _thread_lock: threading.Lock = field(init=False, default_factory=threading.Lock, repr=False)
    _thread: threading.Thread | None = field(init=False, default=None, repr=False)
    _last_completed_ingestion_run_ids: dict[str, str] = field(
        init=False,
        default_factory=dict,
        repr=False,
    )

    def __post_init__(self) -> None:
        self._tasks = parse_scheduled_tasks(self.raw_tasks_json)
        self.poll_interval_seconds = max(int(self.poll_interval_seconds), 1)
        self.snapshot_scan_limit = max(int(self.snapshot_scan_limit), 1)

    def start(self) -> str:
        if not self.enabled:
            self.logger.info("Scheduled analysis runner disabled: component=api_scheduler")
            return "disabled"
        if not self._tasks:
            self.logger.info(
                "Scheduled analysis runner enabled without tasks: component=api_scheduler"
            )
            return "idle"

        with self._thread_lock:
            if self._thread is not None and self._thread.is_alive():
                return "running"

            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._run_loop,
                name="cilly-scheduled-analysis-runner",
                daemon=True,
            )
            self._thread.start()
        self.logger.info(
            "Scheduled analysis runner started: component=api_scheduler tasks=%d poll_interval_seconds=%d snapshot_scan_limit=%d",
            len(self._tasks),
            self.poll_interval_seconds,
            self.snapshot_scan_limit,
        )
        return "running"

    def stop(self) -> str:
        with self._thread_lock:
            thread = self._thread
            self._stop_event.set()
            if thread is None:
                return "stopped"

        thread.join(timeout=max(self.poll_interval_seconds, 1) + 1)
        with self._thread_lock:
            self._thread = None
        self.logger.info("Scheduled analysis runner stopped: component=api_scheduler")
        return "stopped"

    def run_once(self) -> list[dict[str, Any]]:
        if not self.enabled or not self._tasks:
            return []

        runtime = self.get_runtime_controller()
        runtime_state = getattr(runtime, "state", None)
        if runtime_state != "running":
            self.logger.info(
                "Scheduled analysis runner skipped because runtime is not running: component=api_scheduler state=%s",
                runtime_state,
            )
            return []

        if not self._run_lock.acquire(blocking=False):
            self.logger.info(
                "Scheduled analysis runner skipped because another execution is active: component=api_scheduler"
            )
            return []

        try:
            deps = self.build_analysis_service_dependencies()
            outcomes: list[dict[str, Any]] = []
            for task in self._tasks:
                selected_ingestion_run_id = self._select_newest_valid_ingestion_run_id(
                    task=task,
                    deps=deps,
                )
                if selected_ingestion_run_id is None:
                    outcomes.append(
                        {
                            "task_id": task.stable_task_id,
                            "kind": task.kind,
                            "status": "no_valid_snapshot",
                        }
                    )
                    continue

                last_completed = self._last_completed_ingestion_run_ids.get(task.stable_task_id)
                if last_completed == selected_ingestion_run_id:
                    outcomes.append(
                        {
                            "task_id": task.stable_task_id,
                            "kind": task.kind,
                            "status": "already_completed_for_snapshot",
                            "ingestion_run_id": selected_ingestion_run_id,
                        }
                    )
                    continue

                outcome = self._execute_task(
                    task=task,
                    ingestion_run_id=selected_ingestion_run_id,
                    deps=deps,
                )
                outcomes.append(outcome)
                if outcome.get("status") == "completed":
                    self._last_completed_ingestion_run_ids[task.stable_task_id] = (
                        selected_ingestion_run_id
                    )
            return outcomes
        finally:
            self._run_lock.release()

    def _run_loop(self) -> None:
        self.run_once()
        while not self.sleep_wait(self._stop_event, self.poll_interval_seconds):
            self.run_once()

    def _select_newest_valid_ingestion_run_id(
        self,
        *,
        task: ScheduledTask,
        deps: AnalysisServiceDependencies,
    ) -> str | None:
        candidate_runs = deps.analysis_run_repo.list_ingestion_runs(limit=self.snapshot_scan_limit)
        if task.kind == "analysis":
            return self._select_newest_valid_analysis_run_id(task=task, deps=deps, candidate_runs=candidate_runs)
        return self._select_newest_valid_watchlist_run_id(
            task=task,
            deps=deps,
            candidate_runs=candidate_runs,
        )

    def _select_newest_valid_analysis_run_id(
        self,
        *,
        task: ScheduledTask,
        deps: AnalysisServiceDependencies,
        candidate_runs: Sequence[dict[str, Any]],
    ) -> str | None:
        assert task.symbol is not None

        db_path = self.resolve_analysis_db_path()
        for candidate in candidate_runs:
            ingestion_run_id = str(candidate["ingestion_run_id"])
            if not deps.analysis_run_repo.ingestion_run_is_ready(
                ingestion_run_id,
                symbols=[task.symbol],
                timeframe="D1",
            ):
                continue
            try:
                load_ohlcv_snapshot(
                    ingestion_run_id=ingestion_run_id,
                    symbol=task.symbol,
                    timeframe="D1",
                    db_path=db_path,
                )
            except SnapshotDataError:
                continue
            return ingestion_run_id
        return None

    def _select_newest_valid_watchlist_run_id(
        self,
        *,
        task: ScheduledTask,
        deps: AnalysisServiceDependencies,
        candidate_runs: Sequence[dict[str, Any]],
    ) -> str | None:
        assert task.watchlist_id is not None

        watchlist = deps.watchlist_repo.get_watchlist(task.watchlist_id)
        if watchlist is None:
            self.logger.warning(
                "Scheduled watchlist task references unknown watchlist: component=api_scheduler watchlist_id=%s task_id=%s",
                task.watchlist_id,
                task.stable_task_id,
            )
            return None

        db_path = self.resolve_analysis_db_path()
        ordered_symbols = sorted(watchlist.symbols)
        for candidate in candidate_runs:
            ingestion_run_id = str(candidate["ingestion_run_id"])
            for symbol in ordered_symbols:
                if not deps.analysis_run_repo.ingestion_run_is_ready(
                    ingestion_run_id,
                    symbols=[symbol],
                    timeframe="D1",
                ):
                    continue
                try:
                    load_ohlcv_snapshot(
                        ingestion_run_id=ingestion_run_id,
                        symbol=symbol,
                        timeframe="D1",
                        db_path=db_path,
                    )
                except SnapshotDataError:
                    continue
                return ingestion_run_id
        return None

    def _execute_task(
        self,
        *,
        task: ScheduledTask,
        ingestion_run_id: str,
        deps: AnalysisServiceDependencies,
    ) -> dict[str, Any]:
        try:
            if task.kind == "analysis":
                response = manual_analysis(
                    req=ManualAnalysisRequest(
                        ingestion_run_id=ingestion_run_id,
                        symbol=task.symbol or "",
                        strategy=task.strategy or "",
                        market_type=task.market_type,
                        lookback_days=task.lookback_days,
                        strategy_config=task.strategy_config,
                    ),
                    deps=deps,
                )
                payload = response.model_dump()
                self.logger.info(
                    "Scheduled analysis task completed: component=api_scheduler task_id=%s analysis_run_id=%s ingestion_run_id=%s symbol=%s strategy=%s signals=%d",
                    task.stable_task_id,
                    payload["analysis_run_id"],
                    payload["ingestion_run_id"],
                    payload["symbol"],
                    payload["strategy"],
                    len(payload["signals"]),
                )
                return {
                    "task_id": task.stable_task_id,
                    "kind": task.kind,
                    "status": "completed",
                    "analysis_run_id": payload["analysis_run_id"],
                    "ingestion_run_id": payload["ingestion_run_id"],
                }

            response = execute_watchlist(
                watchlist_id=task.watchlist_id or "",
                req=WatchlistExecutionRequest(
                    ingestion_run_id=ingestion_run_id,
                    market_type=task.market_type,
                    lookback_days=task.lookback_days,
                    min_score=task.min_score,
                ),
                deps=deps,
            )
            payload = response.model_dump()
            self.logger.info(
                "Scheduled watchlist task completed: component=api_scheduler task_id=%s analysis_run_id=%s ingestion_run_id=%s watchlist_id=%s ranked_results=%d failures=%d",
                task.stable_task_id,
                payload["analysis_run_id"],
                payload["ingestion_run_id"],
                payload["watchlist_id"],
                len(payload["ranked_results"]),
                len(payload["failures"]),
            )
            return {
                "task_id": task.stable_task_id,
                "kind": task.kind,
                "status": "completed",
                "analysis_run_id": payload["analysis_run_id"],
                "ingestion_run_id": payload["ingestion_run_id"],
            }
        except HTTPException as exc:
            self.logger.warning(
                "Scheduled task failed at request scope: component=api_scheduler task_id=%s kind=%s status_code=%s detail=%s",
                task.stable_task_id,
                task.kind,
                exc.status_code,
                exc.detail,
            )
            return {
                "task_id": task.stable_task_id,
                "kind": task.kind,
                "status": "request_failed",
                "ingestion_run_id": ingestion_run_id,
                "detail": exc.detail,
            }
