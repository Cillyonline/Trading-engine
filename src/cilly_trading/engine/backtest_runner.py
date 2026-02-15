"""Deterministic snapshot-bound backtest runner."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Protocol, Sequence, Tuple

from cilly_trading.engine.result_artifact import write_artifact


class BacktestStrategy(Protocol):
    """Strategy protocol used by ``BacktestRunner``."""

    def on_run_start(self, config: Mapping[str, Any]) -> None:
        """Hook called once before snapshot processing starts."""

    def on_snapshot(self, snapshot: Mapping[str, Any], config: Mapping[str, Any]) -> None:
        """Hook called for each snapshot in deterministic order."""

    def on_run_end(self, config: Mapping[str, Any]) -> None:
        """Hook called once after all snapshots have been processed."""


@dataclass(frozen=True)
class BacktestResult:
    """Result payload for a deterministic backtest run."""

    processed_snapshots: List[Dict[str, Any]]
    invocation_log: List[str]
    artifact_path: Path
    artifact_sha256: str


@dataclass(frozen=True)
class BacktestRunnerConfig:
    """Configuration for deterministic backtest execution."""

    output_dir: Path
    artifact_name: str = "backtest-result.json"
    hash_name: str = "backtest-result.sha256"
    run_id: str = "deterministic"
    strategy_name: str = "strategy"
    strategy_params: Mapping[str, Any] = field(default_factory=dict)
    engine_name: str = "cilly_trading_engine"
    engine_version: str | None = None


class BacktestRunner:
    """Deterministic snapshot-bound backtest runner."""

    def run(
        self,
        *,
        snapshots: Sequence[Mapping[str, Any]],
        strategy_factory: Callable[[], BacktestStrategy],
        config: BacktestRunnerConfig,
    ) -> BacktestResult:
        strategy = strategy_factory()
        ordered_snapshots = self._sort_snapshots(snapshots)

        invocation_log: List[str] = ["on_run_start"]
        strategy.on_run_start(config={
            "output_dir": str(config.output_dir),
            "artifact_name": config.artifact_name,
            "hash_name": config.hash_name,
        })

        processed_snapshots: List[Dict[str, Any]] = []
        for snapshot in ordered_snapshots:
            snapshot_id = str(snapshot.get("id", ""))
            invocation_log.append(f"on_snapshot:{snapshot_id}")
            strategy.on_snapshot(snapshot=snapshot, config={
                "output_dir": str(config.output_dir),
                "artifact_name": config.artifact_name,
                "hash_name": config.hash_name,
            })
            processed_snapshots.append(dict(snapshot))

        invocation_log.append("on_run_end")
        strategy.on_run_end(config={
            "output_dir": str(config.output_dir),
            "artifact_name": config.artifact_name,
            "hash_name": config.hash_name,
        })

        artifact_path, artifact_sha256 = self._write_artifacts(
            processed_snapshots=processed_snapshots,
            invocation_log=invocation_log,
            config=config,
        )

        return BacktestResult(
            processed_snapshots=processed_snapshots,
            invocation_log=invocation_log,
            artifact_path=artifact_path,
            artifact_sha256=artifact_sha256,
        )

    def _sort_snapshots(self, snapshots: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
        sortable: List[Tuple[Tuple[str, str], Dict[str, Any]]] = []
        for snapshot in snapshots:
            normalized = dict(snapshot)
            primary = str(
                normalized.get("timestamp", normalized.get("snapshot_key", ""))
            )
            secondary = str(normalized.get("id", ""))
            sortable.append(((primary, secondary), normalized))

        sortable.sort(key=lambda item: item[0])
        return [item[1] for item in sortable]

    def _write_artifacts(
        self,
        *,
        processed_snapshots: List[Dict[str, Any]],
        invocation_log: List[str],
        config: BacktestRunnerConfig,
    ) -> tuple[Path, str]:
        payload = self._build_payload(
            processed_snapshots=processed_snapshots,
            invocation_log=invocation_log,
            config=config,
        )
        return write_artifact(
            output_dir=config.output_dir,
            payload=payload,
            artifact_name=config.artifact_name,
            hash_name=config.hash_name,
        )

    def _build_payload(
        self,
        *,
        processed_snapshots: List[Dict[str, Any]],
        invocation_log: List[str],
        config: BacktestRunnerConfig,
    ) -> Dict[str, Any]:
        if not processed_snapshots:
            snapshot_mode = "timestamp"
            start = None
            end = None
        else:
            all_have_timestamp = all("timestamp" in snapshot for snapshot in processed_snapshots)
            all_have_snapshot_key = all("snapshot_key" in snapshot for snapshot in processed_snapshots)
            if all_have_timestamp:
                snapshot_mode = "timestamp"
            elif all_have_snapshot_key:
                snapshot_mode = "snapshot_key"
            else:
                raise ValueError("Snapshots must consistently define either 'timestamp' or 'snapshot_key'")
            start, end = self._snapshot_boundaries(processed_snapshots, snapshot_mode)

        return {
            "artifact_version": "1",
            "engine": {
                "name": config.engine_name,
                "version": config.engine_version,
            },
            "run": {
                "run_id": config.run_id,
                "created_at": None,
                "deterministic": True,
            },
            "snapshot_linkage": {
                "mode": snapshot_mode,
                "start": start,
                "end": end,
                "count": len(processed_snapshots),
            },
            "strategy": {
                "name": config.strategy_name,
                "version": None,
                "params": dict(config.strategy_params),
            },
            "invocation_log": invocation_log,
            "processed_snapshots": processed_snapshots,
            "orders": [],
            "fills": [],
            "positions": [],
        }

    def _snapshot_boundaries(
        self,
        processed_snapshots: List[Dict[str, Any]],
        snapshot_mode: str,
    ) -> Tuple[str | None, str | None]:
        if not processed_snapshots:
            return None, None

        boundary_key = "timestamp" if snapshot_mode == "timestamp" else "snapshot_key"
        start = processed_snapshots[0].get(boundary_key)
        end = processed_snapshots[-1].get(boundary_key)
        return str(start) if start is not None else None, str(end) if end is not None else None
