from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Mapping

import pytest

from cilly_trading.engine.backtest_execution_contract import (
    BacktestExecutionAssumptions,
    BacktestRunContract,
)
from cilly_trading.engine.backtest_runner import BacktestRunner, BacktestRunnerConfig
from cilly_trading.engine.journal.execution_journal import EXECUTION_JOURNAL_SCHEMA
from tests.utils.json_schema_validator import validate_json_schema


class SpyStrategy:
    def __init__(self) -> None:
        self.calls: List[str] = []

    def on_run_start(self, config: Mapping[str, Any]) -> None:
        self.calls.append("on_run_start")

    def on_snapshot(self, snapshot: Mapping[str, Any], config: Mapping[str, Any]) -> None:
        self.calls.append(f"on_snapshot:{snapshot['id']}")

    def on_run_end(self, config: Mapping[str, Any]) -> None:
        self.calls.append("on_run_end")


def _sample_snapshots() -> List[Dict[str, Any]]:
    return [
        {"id": "s3", "timestamp": "2024-01-02T00:00:00Z", "price": 12},
        {"id": "s1", "timestamp": "2024-01-01T00:00:00Z", "price": 10},
        {"id": "s2", "timestamp": "2024-01-01T00:00:00Z", "price": 11},
    ]


def _run_with_spy(output_dir: Path):
    container: Dict[str, SpyStrategy] = {}

    def strategy_factory() -> SpyStrategy:
        strategy = SpyStrategy()
        container["strategy"] = strategy
        return strategy

    runner = BacktestRunner()
    result = runner.run(
        snapshots=_sample_snapshots(),
        strategy_factory=strategy_factory,
        config=BacktestRunnerConfig(output_dir=output_dir),
    )
    return result, container["strategy"]


def test_backtest_runner_deterministic_repeat(tmp_path: Path) -> None:
    runner = BacktestRunner()

    def strategy_factory() -> SpyStrategy:
        return SpyStrategy()

    run1_dir = tmp_path / "run-1"
    run2_dir = tmp_path / "run-2"

    result1 = runner.run(
        snapshots=_sample_snapshots(),
        strategy_factory=strategy_factory,
        config=BacktestRunnerConfig(output_dir=run1_dir),
    )
    result2 = runner.run(
        snapshots=_sample_snapshots(),
        strategy_factory=strategy_factory,
        config=BacktestRunnerConfig(output_dir=run2_dir),
    )

    bytes1 = result1.artifact_path.read_bytes()
    bytes2 = result2.artifact_path.read_bytes()

    assert bytes1 == bytes2
    assert result1.artifact_sha256 == result2.artifact_sha256


def test_backtest_runner_deterministic_repeat_with_identical_realism_assumptions(tmp_path: Path) -> None:
    runner = BacktestRunner()

    def strategy_factory() -> SpyStrategy:
        return SpyStrategy()

    run_contract = BacktestRunContract(
        execution_assumptions=BacktestExecutionAssumptions(
            slippage_bps=11,
            commission_per_order=Decimal("1.75"),
            fill_timing="next_snapshot",
        )
    )
    snapshots = [
        {
            "id": "s1",
            "timestamp": "2024-01-01T00:00:00Z",
            "symbol": "AAPL",
            "open": "100",
            "signals": [{"signal_id": "sig-buy", "action": "BUY", "quantity": "1", "symbol": "AAPL"}],
        },
        {
            "id": "s2",
            "timestamp": "2024-01-02T00:00:00Z",
            "symbol": "AAPL",
            "open": "101",
            "signals": [{"signal_id": "sig-sell", "action": "SELL", "quantity": "1", "symbol": "AAPL"}],
        },
        {
            "id": "s3",
            "timestamp": "2024-01-03T00:00:00Z",
            "symbol": "AAPL",
            "open": "102",
        },
    ]
    result1 = runner.run(
        snapshots=snapshots,
        strategy_factory=strategy_factory,
        config=BacktestRunnerConfig(output_dir=tmp_path / "run-1", run_contract=run_contract),
    )
    result2 = runner.run(
        snapshots=snapshots,
        strategy_factory=strategy_factory,
        config=BacktestRunnerConfig(output_dir=tmp_path / "run-2", run_contract=run_contract),
    )

    assert result1.artifact_path.read_bytes() == result2.artifact_path.read_bytes()
    assert result1.artifact_sha256 == result2.artifact_sha256


def test_backtest_runner_snapshot_consistency_order(tmp_path: Path) -> None:
    result, _ = _run_with_spy(tmp_path / "ordered")

    processed_ids = [snapshot["id"] for snapshot in result.processed_snapshots]
    assert processed_ids == ["s1", "s2", "s3"]


def test_backtest_runner_strategy_invocation_stability(tmp_path: Path) -> None:
    result1, spy1 = _run_with_spy(tmp_path / "run-a")
    result2, spy2 = _run_with_spy(tmp_path / "run-b")

    assert result1.invocation_log == result2.invocation_log
    assert spy1.calls == spy2.calls
    assert result1.invocation_log == spy1.calls


def test_backtest_runner_smoke_artifact_created(tmp_path: Path) -> None:
    runner = BacktestRunner()

    def strategy_factory() -> SpyStrategy:
        return SpyStrategy()

    result = runner.run(
        snapshots=[
            {"id": "a", "timestamp": "2024-01-01T00:00:00Z", "price": 1},
            {"id": "b", "timestamp": "2024-01-01T00:00:00Z", "price": 2},
        ],
        strategy_factory=strategy_factory,
        config=BacktestRunnerConfig(output_dir=tmp_path / "smoke"),
    )

    assert result.artifact_path.exists()
    assert result.artifact_path.read_text(encoding="utf-8").endswith("\n")


def test_snapshot_linkage_timestamp_mode(tmp_path: Path) -> None:
    runner = BacktestRunner()

    def strategy_factory() -> SpyStrategy:
        return SpyStrategy()

    result = runner.run(
        snapshots=[
            {"id": "b", "timestamp": "2024-01-02T00:00:00Z"},
            {"id": "a", "timestamp": "2024-01-01T00:00:00Z"},
        ],
        strategy_factory=strategy_factory,
        config=BacktestRunnerConfig(output_dir=tmp_path / "timestamp-mode"),
    )

    payload = json.loads(result.artifact_path.read_text(encoding="utf-8"))
    linkage = payload["snapshot_linkage"]
    assert linkage["mode"] == "timestamp"
    assert linkage["start"] == "2024-01-01T00:00:00Z"
    assert linkage["end"] == "2024-01-02T00:00:00Z"


def test_snapshot_linkage_snapshot_key_mode(tmp_path: Path) -> None:
    runner = BacktestRunner()

    def strategy_factory() -> SpyStrategy:
        return SpyStrategy()

    result = runner.run(
        snapshots=[
            {"id": "b", "snapshot_key": "snap-002"},
            {"id": "a", "snapshot_key": "snap-001"},
        ],
        strategy_factory=strategy_factory,
        config=BacktestRunnerConfig(output_dir=tmp_path / "snapshot-key-mode"),
    )

    payload = json.loads(result.artifact_path.read_text(encoding="utf-8"))
    linkage = payload["snapshot_linkage"]
    assert linkage["mode"] == "snapshot_key"
    assert linkage["start"] == "snap-001"
    assert linkage["end"] == "snap-002"


def test_snapshot_linkage_mixed_error(tmp_path: Path) -> None:
    runner = BacktestRunner()

    def strategy_factory() -> SpyStrategy:
        return SpyStrategy()

    with pytest.raises(
        ValueError,
        match="Snapshots must consistently define either 'timestamp' or 'snapshot_key'",
    ):
        runner.run(
            snapshots=[
                {"id": "a", "timestamp": "2024-01-01T00:00:00Z"},
                {"id": "b"},
            ],
            strategy_factory=strategy_factory,
            config=BacktestRunnerConfig(output_dir=tmp_path / "mixed-mode"),
        )


def test_backtest_runner_persists_execution_journal_artifacts(tmp_path: Path) -> None:
    runner = BacktestRunner()

    def strategy_factory() -> SpyStrategy:
        return SpyStrategy()

    run_dir = tmp_path / "run-integration"
    runner.run(
        snapshots=_sample_snapshots(),
        strategy_factory=strategy_factory,
        config=BacktestRunnerConfig(output_dir=run_dir, run_id="run-integration"),
    )

    journal_path = run_dir / "execution-journal.json"
    hash_path = run_dir / "execution-journal.sha256"

    assert journal_path.exists()
    assert hash_path.exists()

    journal_payload = json.loads(journal_path.read_text(encoding="utf-8"))
    validation_errors = validate_json_schema(journal_payload, EXECUTION_JOURNAL_SCHEMA)
    assert validation_errors == []
    assert journal_payload["run"]["run_id"] == "run-integration"

    phases = [(event["phase"], event["status"]) for event in journal_payload["lifecycle"]]
    assert phases[0] == ("run", "started")
    assert phases[-1] == ("run", "completed")
    assert any(phase == ("snapshot", "processed") for phase in phases)


def test_backtest_runner_artifact_contains_explicit_run_contract(tmp_path: Path) -> None:
    runner = BacktestRunner()

    def strategy_factory() -> SpyStrategy:
        return SpyStrategy()

    result = runner.run(
        snapshots=[
            {"id": "s1", "timestamp": "2024-01-01T00:00:00Z", "symbol": "AAPL", "open": "100"},
            {"id": "s2", "timestamp": "2024-01-02T00:00:00Z", "symbol": "AAPL", "open": "101"},
        ],
        strategy_factory=strategy_factory,
        config=BacktestRunnerConfig(
            output_dir=tmp_path / "run-config",
            run_id="contract-run",
            strategy_name="REFERENCE",
            strategy_params={"alpha": "1"},
            run_contract=BacktestRunContract(
                execution_assumptions=BacktestExecutionAssumptions(
                    slippage_bps=7,
                    commission_per_order=7,
                )
            ),
        ),
    )

    payload = json.loads(result.artifact_path.read_text(encoding="utf-8"))
    run_config = payload["run_config"]
    assert run_config["contract_version"] == "1.0.0"
    assert run_config["execution_assumptions"]["slippage_bps"] == 7
    assert run_config["execution_assumptions"]["commission_per_order"] == "7"
    assert run_config["reproducibility_metadata"]["run_id"] == "contract-run"
    assert run_config["reproducibility_metadata"]["strategy_name"] == "REFERENCE"
    realism_boundary = payload["realism_boundary"]
    assert realism_boundary["modeled_assumptions"]["fees"]["commission_per_order"] == "7"
    assert realism_boundary["modeled_assumptions"]["slippage"]["slippage_bps"] == 7
    assert realism_boundary["modeled_assumptions"]["fills"]["fill_timing"] == "next_snapshot"
    assert "Not modeled." in realism_boundary["unmodeled_assumptions"]["market_hours"]
    assert "live-trading readiness or approval" in realism_boundary["evidence_boundary"]["unsupported_claims"]
    handoff = payload["phase_handoff"]
    artifact_lineage = handoff["artifact_lineage"]
    backtest_to_portfolio = handoff["canonical_handoffs"]["backtest_to_portfolio"]
    portfolio_to_paper = handoff["canonical_handoffs"]["portfolio_to_paper"]
    assert handoff["source_phase"] == "42b"
    assert handoff["target_phases"] == ["43", "44"]
    assert "realism_boundary" in handoff["authoritative_outputs"]["trader_interpretation"]
    assert artifact_lineage["complete"] is True
    assert "run_config.execution_assumptions" in artifact_lineage["required_fields"]
    assert backtest_to_portfolio["handoff_id"] == "phase_42b_backtest_to_phase_43_portfolio"
    assert backtest_to_portfolio["artifact_lineage_complete"] is True
    assert "realism_boundary.modeled_assumptions" in backtest_to_portfolio["required_inputs"]
    assert portfolio_to_paper["handoff_id"] == "phase_43_portfolio_to_phase_44_paper"
    assert portfolio_to_paper["artifact_lineage_complete"] is True
    assert "orders" in portfolio_to_paper["required_inputs"]
    assert handoff["acceptance_gates"]["phase_43_portfolio_simulation_ready"]["passed"] is True
    assert (
        handoff["acceptance_gates"]["phase_44_paper_trading_readiness_evidence_ready"]["passed"]
        is True
    )


def test_backtest_runner_emits_deterministic_orders_fills_positions(tmp_path: Path) -> None:
    runner = BacktestRunner()

    def strategy_factory() -> SpyStrategy:
        return SpyStrategy()

    result = runner.run(
        snapshots=[
            {
                "id": "s1",
                "timestamp": "2024-01-01T00:00:00Z",
                "symbol": "AAPL",
                "open": "100",
                "signals": [{"signal_id": "sig-buy", "action": "BUY", "quantity": "1", "symbol": "AAPL"}],
            },
            {
                "id": "s2",
                "timestamp": "2024-01-02T00:00:00Z",
                "symbol": "AAPL",
                "open": "110",
            },
        ],
        strategy_factory=strategy_factory,
        config=BacktestRunnerConfig(output_dir=tmp_path / "flow", run_id="flow-run"),
    )

    payload = json.loads(result.artifact_path.read_text(encoding="utf-8"))
    assert len(payload["orders"]) == 1
    assert len(payload["fills"]) == 1
    assert len(payload["positions"]) == 1
    assert payload["fills"][0]["occurred_at"] == "2024-01-02T00:00:00Z"
    assert "summary" in payload
    assert "equity_curve" in payload
    assert "metrics_baseline" in payload
    assert payload["summary"]["start_equity"] == 100000.0


def test_backtest_runner_metrics_baseline_cost_aware_differs_from_cost_free(tmp_path: Path) -> None:
    runner = BacktestRunner()

    def strategy_factory() -> SpyStrategy:
        return SpyStrategy()

    result = runner.run(
        snapshots=[
            {
                "id": "s1",
                "timestamp": "2024-01-01T00:00:00Z",
                "symbol": "AAPL",
                "open": "100",
                "signals": [{"signal_id": "sig-buy", "action": "BUY", "quantity": "1", "symbol": "AAPL"}],
            },
            {
                "id": "s2",
                "timestamp": "2024-01-02T00:00:00Z",
                "symbol": "AAPL",
                "open": "101",
                "signals": [{"signal_id": "sig-sell", "action": "SELL", "quantity": "1", "symbol": "AAPL"}],
            },
            {
                "id": "s3",
                "timestamp": "2024-01-03T00:00:00Z",
                "symbol": "AAPL",
                "open": "102",
            },
        ],
        strategy_factory=strategy_factory,
        config=BacktestRunnerConfig(
            output_dir=tmp_path / "baseline",
            run_contract=BacktestRunContract(
                execution_assumptions=BacktestExecutionAssumptions(
                    slippage_bps=10,
                    commission_per_order=Decimal("1"),
                    fill_timing="next_snapshot",
                )
            ),
        ),
    )

    payload = json.loads(result.artifact_path.read_text(encoding="utf-8"))
    baseline = payload["metrics_baseline"]

    assert baseline["summary"]["total_transaction_cost"] > 0.0
    assert (
        baseline["summary"]["ending_equity_cost_aware"]
        < baseline["summary"]["ending_equity_cost_free"]
    )
    assert baseline["metrics"]["cost_aware"]["total_return"] < baseline["metrics"]["cost_free"]["total_return"]
    assert (
        payload["phase_handoff"]["assumption_alignment"][
            "run_config_execution_assumptions_match_metrics_baseline_assumptions"
        ]
        is True
    )


def test_backtest_runner_cost_outputs_change_when_realism_assumptions_change(tmp_path: Path) -> None:
    runner = BacktestRunner()

    def strategy_factory() -> SpyStrategy:
        return SpyStrategy()

    snapshots = [
        {
            "id": "s1",
            "timestamp": "2024-01-01T00:00:00Z",
            "symbol": "AAPL",
            "open": "100",
            "signals": [{"signal_id": "sig-buy", "action": "BUY", "quantity": "1", "symbol": "AAPL"}],
        },
        {
            "id": "s2",
            "timestamp": "2024-01-02T00:00:00Z",
            "symbol": "AAPL",
            "open": "101",
            "signals": [{"signal_id": "sig-sell", "action": "SELL", "quantity": "1", "symbol": "AAPL"}],
        },
        {
            "id": "s3",
            "timestamp": "2024-01-03T00:00:00Z",
            "symbol": "AAPL",
            "open": "102",
        },
    ]
    low_cost = runner.run(
        snapshots=snapshots,
        strategy_factory=strategy_factory,
        config=BacktestRunnerConfig(
            output_dir=tmp_path / "low-cost",
            run_contract=BacktestRunContract(
                execution_assumptions=BacktestExecutionAssumptions(
                    slippage_bps=0,
                    commission_per_order=Decimal("0"),
                )
            ),
        ),
    )
    high_cost = runner.run(
        snapshots=snapshots,
        strategy_factory=strategy_factory,
        config=BacktestRunnerConfig(
            output_dir=tmp_path / "high-cost",
            run_contract=BacktestRunContract(
                execution_assumptions=BacktestExecutionAssumptions(
                    slippage_bps=20,
                    commission_per_order=Decimal("2.50"),
                )
            ),
        ),
    )

    low_payload = json.loads(low_cost.artifact_path.read_text(encoding="utf-8"))
    high_payload = json.loads(high_cost.artifact_path.read_text(encoding="utf-8"))

    assert low_payload["metrics_baseline"]["summary"]["total_transaction_cost"] == 0.0
    assert (
        high_payload["metrics_baseline"]["summary"]["total_transaction_cost"]
        > low_payload["metrics_baseline"]["summary"]["total_transaction_cost"]
    )
    assert (
        high_payload["metrics_baseline"]["summary"]["ending_equity_cost_aware"]
        < low_payload["metrics_baseline"]["summary"]["ending_equity_cost_aware"]
    )


def test_backtest_runner_persists_identical_realism_assumptions_across_artifact_sections(
    tmp_path: Path,
) -> None:
    runner = BacktestRunner()

    def strategy_factory() -> SpyStrategy:
        return SpyStrategy()

    assumptions = BacktestExecutionAssumptions(
        slippage_bps=9,
        commission_per_order=Decimal("1.40"),
        fill_timing="same_snapshot",
    )
    result = runner.run(
        snapshots=[
            {
                "id": "s1",
                "timestamp": "2024-01-01T00:00:00Z",
                "symbol": "AAPL",
                "open": "100",
                "signals": [{"signal_id": "sig-buy", "action": "BUY", "quantity": "1", "symbol": "AAPL"}],
            },
            {"id": "s2", "timestamp": "2024-01-02T00:00:00Z", "symbol": "AAPL", "open": "102"},
        ],
        strategy_factory=strategy_factory,
        config=BacktestRunnerConfig(
            output_dir=tmp_path / "assumption-contract",
            run_contract=BacktestRunContract(execution_assumptions=assumptions),
        ),
    )
    payload = json.loads(result.artifact_path.read_text(encoding="utf-8"))
    expected = assumptions.to_payload()

    assert payload["run_config"]["execution_assumptions"] == expected
    assert payload["metrics_baseline"]["assumptions"] == expected
    assert payload["realism_boundary"]["modeled_assumptions"]["fills"]["fill_timing"] == expected["fill_timing"]
    assert payload["realism_boundary"]["modeled_assumptions"]["fills"]["price_source"] == expected["price_source"]
    assert (
        payload["realism_boundary"]["modeled_assumptions"]["fees"]["commission_per_order"]
        == expected["commission_per_order"]
    )
    assert (
        payload["realism_boundary"]["modeled_assumptions"]["slippage"]["slippage_bps"]
        == expected["slippage_bps"]
    )
