from __future__ import annotations

import hashlib

from pathlib import Path

from cilly_trading.equity_curve import (
    build_equity_curve_from_trade_ledger,
    canonical_equity_curve_json_bytes,
    load_equity_curve_artifact,
    write_equity_curve_artifact,
)


def _ledger_payload() -> dict[str, object]:
    return {
        "artifact": "trade_ledger",
        "artifact_version": "1",
        "trades": [
            {
                "trade_id": "trade-a",
                "strategy_id": "S",
                "symbol": "AAPL",
                "entry_timestamp": "2024-01-01T00:00:00Z",
                "exit_timestamp": "2024-01-01T01:00:00Z",
                "pnl": "100.0",
            },
            {
                "trade_id": "trade-b",
                "strategy_id": "S",
                "symbol": "AAPL",
                "entry_timestamp": "2024-01-02T00:00:00Z",
                "exit_timestamp": "2024-01-02T01:00:00Z",
                "pnl": "-20.0",
            },
            {
                "trade_id": "trade-c",
                "strategy_id": "S",
                "symbol": "MSFT",
                "entry_timestamp": "2024-01-03T00:00:00Z",
                "exit_timestamp": "2024-01-03T01:00:00Z",
                "pnl": "-10.0",
            },
            {
                "trade_id": "trade-d",
                "strategy_id": "S",
                "symbol": "MSFT",
                "entry_timestamp": "2024-01-04T00:00:00Z",
                "exit_timestamp": "2024-01-04T01:00:00Z",
                "pnl": "40.0",
            },
            {
                "trade_id": "trade-e",
                "strategy_id": "S",
                "symbol": "NVDA",
                "entry_timestamp": "2024-01-05T00:00:00Z",
                "exit_timestamp": "2024-01-05T01:00:00Z",
                "pnl": "-11.0",
            },
        ],
    }


def test_equity_curve_generation_includes_drawdown_statistics() -> None:
    artifact = build_equity_curve_from_trade_ledger(_ledger_payload())

    assert artifact["artifact"] == "equity_curve"
    assert artifact["artifact_version"] == "1"
    assert artifact["equity_curve"] == [
        {"timestamp": "2024-01-01T01:00:00Z", "equity": 100.0},
        {"timestamp": "2024-01-02T01:00:00Z", "equity": 80.0},
        {"timestamp": "2024-01-03T01:00:00Z", "equity": 70.0},
        {"timestamp": "2024-01-04T01:00:00Z", "equity": 110.0},
        {"timestamp": "2024-01-05T01:00:00Z", "equity": 99.0},
    ]
    assert artifact["drawdown_stats"] == {
        "max_drawdown": 0.3,
        "recovery_time_steps": 1,
        "drawdown_distribution": [
            {
                "peak_timestamp": "2024-01-01T01:00:00Z",
                "trough_timestamp": "2024-01-03T01:00:00Z",
                "recovery_timestamp": "2024-01-04T01:00:00Z",
                "drawdown": 0.3,
                "recovery_time_steps": 1,
            },
            {
                "peak_timestamp": "2024-01-04T01:00:00Z",
                "trough_timestamp": "2024-01-05T01:00:00Z",
                "recovery_timestamp": None,
                "drawdown": 0.1,
                "recovery_time_steps": None,
            },
        ],
    }


def test_equity_curve_results_are_order_independent_and_deterministic() -> None:
    payload = _ledger_payload()
    reversed_payload = {
        **payload,
        "trades": list(reversed(payload["trades"])),  # type: ignore[index]
    }

    first = build_equity_curve_from_trade_ledger(payload)
    second = build_equity_curve_from_trade_ledger(reversed_payload)

    bytes_first = canonical_equity_curve_json_bytes(first)
    bytes_second = canonical_equity_curve_json_bytes(second)

    assert first == second
    assert bytes_first == bytes_second
    assert bytes_first.endswith(b"\n")
    assert b"\r\n" not in bytes_first


def test_equity_curve_artifact_write_and_load_round_trip(tmp_path: Path) -> None:
    artifact = build_equity_curve_from_trade_ledger(_ledger_payload())

    path_a, sha_a = write_equity_curve_artifact(tmp_path / "run-a", artifact)
    path_b, sha_b = write_equity_curve_artifact(tmp_path / "run-b", artifact)

    bytes_a = path_a.read_bytes()
    bytes_b = path_b.read_bytes()

    assert bytes_a == bytes_b
    assert sha_a == sha_b
    assert hashlib.sha256(bytes_a).hexdigest() == sha_a
    assert (tmp_path / "run-a" / "equity-curve.sha256").read_text(encoding="utf-8") == f"{sha_a}\n"

    loaded = load_equity_curve_artifact(path_a)
    assert loaded == artifact
