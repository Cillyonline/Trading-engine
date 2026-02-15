"""Deterministic snapshot-bound backtest runner."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Protocol, Sequence, Tuple


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
        payload = {
            "invocation_log": invocation_log,
            "processed_snapshots": processed_snapshots,
        }
        artifact_text = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ) + "\n"

        config.output_dir.mkdir(parents=True, exist_ok=True)

        artifact_path = config.output_dir / config.artifact_name
        artifact_path.write_text(artifact_text, encoding="utf-8", newline="\n")

        artifact_sha256 = hashlib.sha256(artifact_text.encode("utf-8")).hexdigest()
        hash_path = config.output_dir / config.hash_name
        hash_path.write_text(f"{artifact_sha256}\n", encoding="utf-8", newline="\n")

        return artifact_path, artifact_sha256
