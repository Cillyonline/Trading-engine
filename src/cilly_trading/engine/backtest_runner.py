"""Deterministic snapshot-bound backtest runner."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Protocol, Sequence, Tuple

from cilly_trading.engine.backtest_execution_contract import (
    BacktestRunContract,
    build_cost_slippage_metrics_baseline,
    serialize_fills,
    serialize_orders,
    serialize_positions,
    simulate_execution_flow,
)
from cilly_trading.engine.backtest_handoff_contract import build_phase_handoff_contract
from cilly_trading.engine.journal.execution_journal import (
    build_execution_journal_artifact,
    write_execution_journal_artifact,
)
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
    run_contract: BacktestRunContract = field(default_factory=BacktestRunContract)


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
        artifact_path, artifact_sha256 = write_artifact(
            output_dir=config.output_dir,
            payload=payload,
            artifact_name=config.artifact_name,
            hash_name=config.hash_name,
        )
        self._write_execution_journal(
            processed_snapshots=processed_snapshots,
            invocation_log=invocation_log,
            config=config,
        )
        return artifact_path, artifact_sha256

    def _write_execution_journal(
        self,
        *,
        processed_snapshots: List[Dict[str, Any]],
        invocation_log: List[str],
        config: BacktestRunnerConfig,
    ) -> None:
        events: List[Dict[str, Any]] = []
        snapshot_lookup = {
            str(snapshot.get("id", "")): snapshot for snapshot in processed_snapshots
        }

        for index, invocation in enumerate(invocation_log, start=1):
            if invocation == "on_run_start":
                events.append(
                    {
                        "event_id": f"{config.run_id}:run_start",
                        "phase": "run",
                        "status": "started",
                        "sequence": index,
                        "snapshot_id": "",
                        "timestamp": "",
                        "metadata": {"hook": invocation},
                    }
                )
                continue

            if invocation == "on_run_end":
                events.append(
                    {
                        "event_id": f"{config.run_id}:run_end",
                        "phase": "run",
                        "status": "completed",
                        "sequence": index,
                        "snapshot_id": "",
                        "timestamp": "",
                        "metadata": {"hook": invocation},
                    }
                )
                continue

            if invocation.startswith("on_snapshot:"):
                snapshot_id = invocation.split(":", 1)[1]
                snapshot_payload = snapshot_lookup.get(snapshot_id, {})
                snapshot_timestamp = snapshot_payload.get("timestamp")
                events.append(
                    {
                        "event_id": f"{config.run_id}:snapshot:{snapshot_id}",
                        "phase": "snapshot",
                        "status": "processed",
                        "sequence": index,
                        "snapshot_id": snapshot_id,
                        "timestamp": "" if snapshot_timestamp is None else str(snapshot_timestamp),
                        "metadata": {"hook": invocation},
                    }
                )

        execution_journal = build_execution_journal_artifact(
            run_id=config.run_id,
            lifecycle_events=events,
            deterministic=True,
            created_at="",
        )
        write_execution_journal_artifact(config.output_dir, execution_journal)

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

        flow_result = simulate_execution_flow(
            snapshots=processed_snapshots,
            run_id=config.run_id,
            strategy_name=config.strategy_name,
            run_contract=config.run_contract,
        )
        metrics_baseline = build_cost_slippage_metrics_baseline(
            ordered_snapshots=processed_snapshots,
            fills=flow_result.fills,
            execution_assumptions=config.run_contract.execution_assumptions,
        )

        payload = {
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
            "run_config": config.run_contract.to_payload(
                run_id=config.run_id,
                strategy_name=config.strategy_name,
                strategy_params=config.strategy_params,
                engine_name=config.engine_name,
                engine_version=config.engine_version,
            ),
            "invocation_log": invocation_log,
            "processed_snapshots": processed_snapshots,
            "orders": serialize_orders(flow_result.orders),
            "fills": serialize_fills(flow_result.fills),
            "positions": serialize_positions(flow_result.positions),
            "summary": {
                "start_equity": metrics_baseline["summary"]["starting_equity"],
                "end_equity": metrics_baseline["summary"]["ending_equity_cost_aware"],
            },
            "equity_curve": metrics_baseline["equity_curve"]["cost_aware"],
            "trades": metrics_baseline["trades"],
            "metrics_baseline": metrics_baseline,
        }
        payload["phase_handoff"] = build_phase_handoff_contract(payload)
        return payload

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
