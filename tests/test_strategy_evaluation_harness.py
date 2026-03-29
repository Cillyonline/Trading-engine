from __future__ import annotations

import json
from pathlib import Path

import pytest

from cilly_trading.strategies.evaluation_harness import (
    StrategyEvaluationSelectionError,
    run_strategy_comparison,
)


def _comparison_snapshots() -> list[dict[str, object]]:
    snapshots: list[dict[str, object]] = []
    for day in range(1, 26):
        timestamp = f"2024-01-{day:02d}T00:00:00Z"
        if day <= 20:
            close = 100
        elif day == 21:
            close = 105
        elif day == 22:
            close = 106
        else:
            close = 130

        snapshots.append(
            {
                "id": f"s{day:02d}",
                "timestamp": timestamp,
                "symbol": "AAPL",
                "open": close,
                "high": close,
                "low": close - 1,
                "close": close,
                "price": close,
            }
        )
    return snapshots


def _strategy_map(payload: dict[str, object]) -> dict[str, dict[str, object]]:
    rows = payload["strategies"]
    assert isinstance(rows, list)
    mapped: dict[str, dict[str, object]] = {}
    for row in rows:
        assert isinstance(row, dict)
        mapped[str(row["strategy_name"])] = row
    return mapped


def test_strategy_comparison_flow_writes_bounded_output(tmp_path: Path) -> None:
    run_dir = tmp_path / "comparison"
    result = run_strategy_comparison(
        snapshots=_comparison_snapshots(),
        strategy_names=["REFERENCE", "TURTLE"],
        output_dir=run_dir,
        run_id="cmp-flow",
    )

    assert result.artifact_path.exists()
    assert (run_dir / "strategy-comparison.sha256").exists()

    payload = json.loads(result.artifact_path.read_text(encoding="utf-8"))
    assert payload["artifact"] == "strategy_comparison"
    assert payload["semantics"]["signal_score"]["comparison_scope"] == "strategy_local_only"
    assert payload["semantics"]["signal_score"]["cross_strategy_score_comparison_supported"] is False
    assert payload["semantics"]["ranking"]["rank_scope"] == "comparison_group"
    assert payload["semantics"]["ranking"]["cross_group_ordering_supported"] is False
    assert payload["semantics"]["ranking"]["cross_group_delta_supported"] is False
    assert payload["workflow"]["name"] == "bounded_comparable_strategy_evaluation"
    assert payload["workflow"]["strategy_order"] == ["REFERENCE", "TURTLE"]
    assert payload["workflow"]["snapshot_linkage"]["count"] == 25

    strategies = _strategy_map(payload)
    reference = strategies["REFERENCE"]
    turtle = strategies["TURTLE"]

    assert reference["signals"]["executable_count"] == 0
    assert turtle["signals"]["executable_count"] == 1
    assert reference["metrics_baseline_summary"]["fill_count"] == 0
    assert turtle["metrics_baseline_summary"]["fill_count"] == 1


def test_strategy_comparison_is_reproducible_across_runs(tmp_path: Path) -> None:
    snapshots = _comparison_snapshots()
    result_a = run_strategy_comparison(
        snapshots=snapshots,
        strategy_names=["REFERENCE", "TURTLE"],
        output_dir=tmp_path / "run-a",
        run_id="cmp-repro",
    )
    result_b = run_strategy_comparison(
        snapshots=snapshots,
        strategy_names=["REFERENCE", "TURTLE"],
        output_dir=tmp_path / "run-b",
        run_id="cmp-repro",
    )

    assert result_a.artifact_path.read_bytes() == result_b.artifact_path.read_bytes()
    assert result_a.artifact_sha256 == result_b.artifact_sha256


def test_strategy_comparison_regression_reference_vs_turtle(tmp_path: Path) -> None:
    result = run_strategy_comparison(
        snapshots=_comparison_snapshots(),
        strategy_names=["REFERENCE", "TURTLE"],
        output_dir=tmp_path / "regression",
        run_id="cmp-regression",
        benchmark_strategy="REFERENCE",
    )

    payload = json.loads(result.artifact_path.read_text(encoding="utf-8"))
    strategies = _strategy_map(payload)

    reference_total_return = strategies["REFERENCE"]["metrics"]["total_return"]
    turtle_total_return = strategies["TURTLE"]["metrics"]["total_return"]
    assert reference_total_return == 0.0
    assert turtle_total_return == 0.00024

    ranking = payload["ranking"]
    assert ranking[0]["strategy_name"] == "REFERENCE"
    assert ranking[0]["comparison_group"] == "reference-control"
    assert ranking[0]["rank_scope"] == "comparison_group"
    assert ranking[0]["rank"] == 1
    assert ranking[1]["strategy_name"] == "TURTLE"
    assert ranking[1]["comparison_group"] == "trend-following"
    assert ranking[1]["rank_scope"] == "comparison_group"
    assert ranking[1]["rank"] == 1

    deltas = {row["strategy_name"]: row for row in payload["deltas_vs_benchmark"]}
    assert deltas["REFERENCE"]["comparison_group"] == "reference-control"
    assert deltas["REFERENCE"]["benchmark_comparison_group"] == "reference-control"
    assert deltas["REFERENCE"]["comparable_to_benchmark"] is True
    assert deltas["REFERENCE"]["total_return_delta"] == 0.0
    assert deltas["TURTLE"]["comparison_group"] == "trend-following"
    assert deltas["TURTLE"]["benchmark_comparison_group"] == "reference-control"
    assert deltas["TURTLE"]["comparable_to_benchmark"] is False
    assert deltas["TURTLE"]["total_return_delta"] is None


def test_strategy_comparison_requires_governed_comparison_group(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "cilly_trading.strategies.evaluation_harness.get_registered_strategy_metadata",
        lambda: {},
    )

    with pytest.raises(
        StrategyEvaluationSelectionError,
        match="outside governed comparison surfaces",
    ):
        run_strategy_comparison(
            snapshots=_comparison_snapshots(),
            strategy_names=["REFERENCE"],
            output_dir=tmp_path / "governance-fail",
            run_id="cmp-governance",
        )
