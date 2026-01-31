from __future__ import annotations

import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Dict, List, Optional

import pytest

from cilly_trading.engine.paper_trading import PaperTradingSimulator
from cilly_trading.models import Signal
from cilly_trading.repositories.trades_sqlite import SqliteTradeRepository


@pytest.fixture()
def signal_fixture() -> List[Signal]:
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


PRICE_QUANTIZER = Decimal("0.0001")


def _format_decimal(value: Decimal) -> str:
    return str(value.quantize(PRICE_QUANTIZER, rounding=ROUND_HALF_UP))


def _format_optional_number(value: Optional[float]) -> Optional[str]:
    if value is None:
        return None
    return _format_decimal(Decimal(str(value)))


def _canonical_json(payload: Dict[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _serialize_result(result) -> Dict[str, object]:
    trades = []
    for trade in result.trades:
        trades.append(
            {
                "symbol": trade["symbol"],
                "strategy": trade["strategy"],
                "stage": trade["stage"],
                "entry_price": _format_optional_number(trade.get("entry_price")),
                "entry_date": trade.get("entry_date"),
                "exit_price": _format_optional_number(trade.get("exit_price")),
                "exit_date": trade.get("exit_date"),
                "reason_entry": trade.get("reason_entry"),
                "reason_exit": trade.get("reason_exit"),
                "notes": trade.get("notes"),
                "timeframe": trade.get("timeframe"),
                "market_type": trade.get("market_type"),
                "data_source": trade.get("data_source"),
            }
        )

    positions = {
        symbol: {
            "qty": summary.qty,
            "avg_entry_price": summary.avg_entry_price,
            "realized_pnl": summary.realized_pnl,
            "unrealized_pnl": summary.unrealized_pnl,
            "total_pnl": summary.total_pnl,
        }
        for symbol, summary in result.positions.items()
    }

    return {
        "trades": trades,
        "positions": positions,
        "pnl_by_symbol": result.pnl_by_symbol,
        "pnl_total": result.pnl_total,
    }


def test_paper_trading_snapshot(signal_fixture: List[Signal]) -> None:
    simulator = PaperTradingSimulator()
    result = simulator.run(signal_fixture)

    summary_payload = {
        "positions": {
            "AAPL": {
                "qty": 1,
                "avg_entry_price": "100.5000",
                "realized_pnl": "2.0000",
                "unrealized_pnl": "1.5000",
                "total_pnl": "3.5000",
            },
            "MSFT": {
                "qty": 0,
                "avg_entry_price": "0.0000",
                "realized_pnl": "2.0000",
                "unrealized_pnl": "0.0000",
                "total_pnl": "2.0000",
            },
        },
        "pnl_by_symbol": {
            "AAPL": {"realized": "2.0000", "unrealized": "1.5000", "total": "3.5000"},
            "MSFT": {"realized": "2.0000", "unrealized": "0.0000", "total": "2.0000"},
        },
        "pnl_total": {"realized": "4.0000", "unrealized": "1.5000", "total": "5.5000"},
    }
    summary_notes = _canonical_json(summary_payload)

    snapshot = {
        "trades": [
            {
                "symbol": "AAPL",
                "strategy": "TEST",
                "stage": "entry_confirmed",
                "entry_price": "100.0000",
                "entry_date": "2024-01-01T09:30:00Z",
                "exit_price": "102.0000",
                "exit_date": "2024-01-03T09:30:00Z",
                "reason_entry": "rule-a",
                "reason_exit": "paper_trade_exit",
                "notes": None,
                "timeframe": "D1",
                "market_type": "stock",
                "data_source": "yahoo",
            },
            {
                "symbol": "MSFT",
                "strategy": "TEST",
                "stage": "entry_confirmed",
                "entry_price": "200.0000",
                "entry_date": "2024-01-01T09:35:00Z",
                "exit_price": "202.0000",
                "exit_date": "2024-01-02T09:35:00Z",
                "reason_entry": "rule-d",
                "reason_exit": "paper_trade_exit",
                "notes": None,
                "timeframe": "D1",
                "market_type": "stock",
                "data_source": "yahoo",
            },
            {
                "symbol": "AAPL",
                "strategy": "TEST",
                "stage": "entry_confirmed",
                "entry_price": "101.0000",
                "entry_date": "2024-01-02T09:30:00Z",
                "exit_price": None,
                "exit_date": None,
                "reason_entry": "rule-b",
                "reason_exit": None,
                "notes": None,
                "timeframe": "D1",
                "market_type": "stock",
                "data_source": "yahoo",
            },
            {
                "symbol": "__SUMMARY__",
                "strategy": "PAPER_TRADING",
                "stage": "setup",
                "entry_price": None,
                "entry_date": "2024-01-03T09:30:00Z",
                "exit_price": None,
                "exit_date": None,
                "reason_entry": "paper_trade_summary",
                "reason_exit": None,
                "notes": summary_notes,
                "timeframe": "D1",
                "market_type": "stock",
                "data_source": "yahoo",
            },
        ],
        "positions": {
            "AAPL": {
                "qty": 1,
                "avg_entry_price": "100.5000",
                "realized_pnl": "2.0000",
                "unrealized_pnl": "1.5000",
                "total_pnl": "3.5000",
            },
            "MSFT": {
                "qty": 0,
                "avg_entry_price": "0.0000",
                "realized_pnl": "2.0000",
                "unrealized_pnl": "0.0000",
                "total_pnl": "2.0000",
            },
        },
        "pnl_by_symbol": {
            "AAPL": {"realized": "2.0000", "unrealized": "1.5000", "total": "3.5000"},
            "MSFT": {"realized": "2.0000", "unrealized": "0.0000", "total": "2.0000"},
        },
        "pnl_total": {"realized": "4.0000", "unrealized": "1.5000", "total": "5.5000"},
    }

    assert _serialize_result(result) == snapshot


def test_paper_trading_determinism(signal_fixture: List[Signal]) -> None:
    simulator = PaperTradingSimulator()
    result_one = _serialize_result(simulator.run(signal_fixture))
    result_two = _serialize_result(simulator.run(signal_fixture))

    assert result_one == result_two


def test_paper_trading_repository_integration(
    tmp_path: Path, signal_fixture: List[Signal]
) -> None:
    db_path = tmp_path / "trades.db"
    repository = SqliteTradeRepository(db_path)
    simulator = PaperTradingSimulator(trade_repository=repository)
    result = simulator.run(signal_fixture)

    stored_trades = repository.list_trades(limit=10)
    stored_trades_sorted = list(reversed(stored_trades))

    expected_trades = []
    for trade in result.trades:
        expected_trades.append(
            {
                "symbol": trade["symbol"],
                "strategy": trade["strategy"],
                "stage": trade["stage"],
                "entry_price": _format_optional_number(trade.get("entry_price")),
                "entry_date": trade.get("entry_date"),
                "exit_price": _format_optional_number(trade.get("exit_price")),
                "exit_date": trade.get("exit_date"),
                "reason_entry": trade.get("reason_entry"),
                "reason_exit": trade.get("reason_exit"),
                "notes": trade.get("notes"),
                "timeframe": trade.get("timeframe"),
                "market_type": trade.get("market_type"),
                "data_source": trade.get("data_source"),
            }
        )

    stored_expected = []
    for trade in stored_trades_sorted:
        stored_expected.append(
            {
                "symbol": trade["symbol"],
                "strategy": trade["strategy"],
                "stage": trade["stage"],
                "entry_price": _format_optional_number(trade.get("entry_price")),
                "entry_date": trade.get("entry_date"),
                "exit_price": _format_optional_number(trade.get("exit_price")),
                "exit_date": trade.get("exit_date"),
                "reason_entry": trade.get("reason_entry"),
                "reason_exit": trade.get("reason_exit"),
                "notes": trade.get("notes"),
                "timeframe": trade.get("timeframe"),
                "market_type": trade.get("market_type"),
                "data_source": trade.get("data_source"),
            }
        )

    assert stored_expected == expected_trades
