from __future__ import annotations

import hashlib
import json

from cilly_trading.engine.paper_trading import PaperTradingSimulator

from cilly_trading.risk_adjusted_metrics import compute_risk_adjusted_metrics_from_trade_ledger
from cilly_trading.trade_ledger import build_trade_ledger_from_paper_trades


def _deterministic_ledger() -> dict[str, object]:
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
                "entry_price": "100.0000",
                "exit_price": "110.0000",
                "quantity": "1.0000",
                "pnl": "10.0000",
                "holding_time": 3600,
            },
            {
                "trade_id": "trade-b",
                "strategy_id": "S",
                "symbol": "AAPL",
                "entry_timestamp": "2024-01-02T00:00:00Z",
                "exit_timestamp": "2024-01-02T01:00:00Z",
                "entry_price": "100.0000",
                "exit_price": "95.0000",
                "quantity": "1.0000",
                "pnl": "-5.0000",
                "holding_time": 3600,
            },
            {
                "trade_id": "trade-c",
                "strategy_id": "S",
                "symbol": "MSFT",
                "entry_timestamp": "2024-01-03T00:00:00Z",
                "exit_timestamp": "2024-01-03T01:00:00Z",
                "entry_price": "200.0000",
                "exit_price": "210.0000",
                "quantity": "2.0000",
                "pnl": "20.0000",
                "holding_time": 3600,
            },
            {
                "trade_id": "trade-d",
                "strategy_id": "S",
                "symbol": "MSFT",
                "entry_timestamp": "2024-01-04T00:00:00Z",
                "exit_timestamp": "2024-01-04T01:00:00Z",
                "entry_price": "50.0000",
                "exit_price": "50.0000",
                "quantity": "1.0000",
                "pnl": "0.0000",
                "holding_time": 3600,
            },
        ],
    }


def _signals() -> list[dict[str, object]]:
    return [
        {
            "symbol": "AAPL",
            "strategy": "TEST",
            "direction": "long",
            "action": "entry",
            "timestamp": "2024-01-01T09:30:00Z",
            "stage": "entry_confirmed",
            "entry_zone": {"from_": 99.5, "to": 100.5},
            "confirmation_rule": "rule-a",
            "timeframe": "D1",
            "market_type": "stock",
            "data_source": "yahoo",
        },
        {
            "symbol": "AAPL",
            "strategy": "TEST",
            "direction": "long",
            "action": "entry",
            "timestamp": "2024-01-02T09:30:00Z",
            "stage": "entry_confirmed",
            "entry_zone": {"from_": 100.5, "to": 101.5},
            "confirmation_rule": "rule-b",
            "timeframe": "D1",
            "market_type": "stock",
            "data_source": "yahoo",
        },
        {
            "symbol": "AAPL",
            "strategy": "TEST",
            "direction": "long",
            "action": "exit",
            "timestamp": "2024-01-03T09:30:00Z",
            "stage": "setup",
            "entry_zone": {"from_": 101.0, "to": 103.0},
            "confirmation_rule": "rule-c",
            "timeframe": "D1",
            "market_type": "stock",
            "data_source": "yahoo",
        },
        {
            "symbol": "MSFT",
            "strategy": "TEST",
            "direction": "long",
            "action": "entry",
            "timestamp": "2024-01-01T09:35:00Z",
            "stage": "entry_confirmed",
            "entry_zone": {"from_": 198.0, "to": 202.0},
            "confirmation_rule": "rule-d",
            "timeframe": "D1",
            "market_type": "stock",
            "data_source": "yahoo",
        },
        {
            "symbol": "MSFT",
            "strategy": "TEST",
            "direction": "long",
            "action": "exit",
            "timestamp": "2024-01-02T09:35:00Z",
            "stage": "setup",
            "entry_zone": {"from_": 201.0, "to": 203.0},
            "confirmation_rule": "rule-e",
            "timeframe": "D1",
            "market_type": "stock",
            "data_source": "yahoo",
        },
    ]


def test_risk_adjusted_metrics_values_are_deterministic() -> None:
    metrics = compute_risk_adjusted_metrics_from_trade_ledger(_deterministic_ledger())

    assert metrics == {
        "sharpe_ratio": 0.387298334621,
        "sortino_ratio": 1.0,
        "calmar_ratio": 1.945,
        "profit_factor": 6.0,
        "win_rate": 0.5,
    }


def test_risk_adjusted_metrics_are_order_independent_and_reproducible() -> None:
    ledger = _deterministic_ledger()
    reversed_ledger = {
        **ledger,
        "trades": list(reversed(ledger["trades"])),  # type: ignore[index]
    }

    first = compute_risk_adjusted_metrics_from_trade_ledger(ledger)
    second = compute_risk_adjusted_metrics_from_trade_ledger(reversed_ledger)
    third = compute_risk_adjusted_metrics_from_trade_ledger(ledger)

    first_json = json.dumps(first, sort_keys=True, separators=(",", ":"), allow_nan=False)
    second_json = json.dumps(second, sort_keys=True, separators=(",", ":"), allow_nan=False)
    third_json = json.dumps(third, sort_keys=True, separators=(",", ":"), allow_nan=False)

    assert first == second == third
    assert hashlib.sha256(first_json.encode("utf-8")).hexdigest() == hashlib.sha256(
        second_json.encode("utf-8")
    ).hexdigest()
    assert hashlib.sha256(first_json.encode("utf-8")).hexdigest() == hashlib.sha256(
        third_json.encode("utf-8")
    ).hexdigest()


def test_risk_adjusted_metrics_accept_trade_ledger_artifact_payload() -> None:
    result = PaperTradingSimulator().run(_signals())
    ledger = build_trade_ledger_from_paper_trades(result.trades, signals=_signals())

    metrics = compute_risk_adjusted_metrics_from_trade_ledger(ledger)

    assert set(metrics.keys()) == {
        "sharpe_ratio",
        "sortino_ratio",
        "calmar_ratio",
        "profit_factor",
        "win_rate",
    }
    assert metrics["profit_factor"] is None
    assert metrics["win_rate"] == 1.0
    assert metrics["sharpe_ratio"] == 2.12132034356
    assert metrics["sortino_ratio"] is None
    assert metrics["calmar_ratio"] is None
