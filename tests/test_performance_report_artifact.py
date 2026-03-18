from __future__ import annotations

import hashlib

from pathlib import Path

from cilly_trading.performance_report import (
    build_performance_report_from_trade_ledger,
    canonical_performance_report_json_bytes,
    load_performance_report_artifact,
    write_performance_report_artifact,
)


def _ledger_payload() -> dict[str, object]:
    return {
        "artifact": "trade_ledger",
        "artifact_version": "1",
        "trades": [
            {
                "trade_id": "trade-a",
                "strategy_id": "ALPHA",
                "symbol": "AAPL",
                "entry_timestamp": "2024-01-01T00:00:00Z",
                "exit_timestamp": "2024-01-01T01:00:00Z",
                "entry_price": "100.0000",
                "exit_price": "110.0000",
                "quantity": "1.0000",
                "pnl": "10.0000",
                "holding_time": 3600,
            },
            {
                "trade_id": "trade-b",
                "strategy_id": "BETA",
                "symbol": "MSFT",
                "entry_timestamp": "2024-01-02T00:00:00Z",
                "exit_timestamp": "2024-01-02T00:30:00Z",
                "entry_price": "100.0000",
                "exit_price": "98.0000",
                "quantity": "1.0000",
                "pnl": "-2.0000",
                "holding_time": 1800,
            },
            {
                "trade_id": "trade-c",
                "strategy_id": "ALPHA",
                "symbol": "NVDA",
                "entry_timestamp": "2024-01-03T00:00:00Z",
                "exit_timestamp": "2024-01-03T02:00:00Z",
                "entry_price": "50.0000",
                "exit_price": "54.0000",
                "quantity": "1.0000",
                "pnl": "4.0000",
                "holding_time": 7200,
            },
        ],
        "risk_adjusted_metrics": {
            "sharpe_ratio": 1.23,
            "sortino_ratio": 2.34,
            "calmar_ratio": 0.9,
            "profit_factor": 7.0,
            "win_rate": 0.666666666667,
        },
    }


def test_performance_report_generation_from_trade_ledger() -> None:
    report = build_performance_report_from_trade_ledger(_ledger_payload())

    assert report["artifact"] == "performance_report"
    assert report["artifact_version"] == "1"
    assert report["performance_summary"] == {
        "total_trades": 3,
        "strategies_analyzed": 2,
        "total_pnl": 12.0,
        "winning_trades": 2,
        "losing_trades": 1,
        "breakeven_trades": 0,
    }
    assert report["strategy_comparison"] == [
        {
            "strategy_id": "ALPHA",
            "trade_count": 2,
            "total_pnl": 14.0,
            "average_pnl": 7.0,
            "win_rate": 1.0,
        },
        {
            "strategy_id": "BETA",
            "trade_count": 1,
            "total_pnl": -2.0,
            "average_pnl": -2.0,
            "win_rate": 0.0,
        },
    ]
    assert report["key_metrics_overview"] == {
        "overall_win_rate": 0.666666666667,
        "average_pnl_per_trade": 4.0,
        "average_holding_time_seconds": 4200.0,
        "best_strategy_id": "ALPHA",
        "worst_strategy_id": "BETA",
        "risk_adjusted_metrics": {
            "sharpe_ratio": 1.23,
            "sortino_ratio": 2.34,
            "calmar_ratio": 0.9,
            "profit_factor": 7.0,
            "win_rate": 0.666666666667,
        },
    }


def test_performance_report_serialization_is_deterministic() -> None:
    payload = _ledger_payload()
    reversed_payload = {
        **payload,
        "trades": list(reversed(payload["trades"])),  # type: ignore[index]
    }

    report_a = build_performance_report_from_trade_ledger(payload)
    report_b = build_performance_report_from_trade_ledger(reversed_payload)

    bytes_a = canonical_performance_report_json_bytes(report_a)
    bytes_b = canonical_performance_report_json_bytes(report_b)

    assert report_a == report_b
    assert bytes_a == bytes_b
    assert bytes_a.endswith(b"\n")
    assert b"\r\n" not in bytes_a



def test_performance_report_artifact_write_and_load(tmp_path: Path) -> None:
    report = build_performance_report_from_trade_ledger(_ledger_payload())

    path_a, sha_a = write_performance_report_artifact(tmp_path / "run-a", report)
    path_b, sha_b = write_performance_report_artifact(tmp_path / "run-b", report)

    bytes_a = path_a.read_bytes()
    bytes_b = path_b.read_bytes()

    assert bytes_a == bytes_b
    assert sha_a == sha_b
    assert hashlib.sha256(bytes_a).hexdigest() == sha_a
    assert (tmp_path / "run-a" / "performance-report.sha256").read_text(encoding="utf-8") == f"{sha_a}\n"

    loaded = load_performance_report_artifact(path_a)
    assert loaded == report
