from __future__ import annotations

from pathlib import Path

from cilly_trading.engine.paper_trading import PaperTradingSimulator

from engine.trade_ledger import (
    build_trade_ledger_from_paper_trades,
    canonical_trade_ledger_json_bytes,
    load_trade_ledger_artifact,
    write_trade_ledger_artifact,
)


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


def test_trade_ledger_generation_from_paper_trading_runtime() -> None:
    result = PaperTradingSimulator().run(_signals())

    ledger = build_trade_ledger_from_paper_trades(result.trades, signals=_signals())
    trades = ledger["trades"]

    assert ledger["artifact"] == "trade_ledger"
    assert ledger["artifact_version"] == "1"
    assert isinstance(trades, list)
    assert len(trades) == 2

    expected_first = {
        "strategy_id": "TEST",
        "symbol": "MSFT",
        "entry_timestamp": "2024-01-01T09:35:00Z",
        "exit_timestamp": "2024-01-02T09:35:00Z",
        "entry_price": "200.0000",
        "exit_price": "202.0000",
        "quantity": "1.0000",
        "pnl": "2.0000",
        "holding_time": 86400,
    }

    expected_second = {
        "strategy_id": "TEST",
        "symbol": "AAPL",
        "entry_timestamp": "2024-01-01T09:30:00Z",
        "exit_timestamp": "2024-01-03T09:30:00Z",
        "entry_price": "100.0000",
        "exit_price": "102.0000",
        "quantity": "1.0000",
        "pnl": "2.0000",
        "holding_time": 172800,
    }

    first = trades[0]
    second = trades[1]

    assert first["trade_id"] != second["trade_id"]
    assert {key: first[key] for key in expected_first} == expected_first
    assert {key: second[key] for key in expected_second} == expected_second


def test_trade_ledger_serialization_is_deterministic() -> None:
    result = PaperTradingSimulator().run(_signals())

    ledger_a = build_trade_ledger_from_paper_trades(result.trades, signals=_signals())
    ledger_b = build_trade_ledger_from_paper_trades(
        list(reversed(result.trades)),
        signals=list(reversed(_signals())),
    )

    bytes_a = canonical_trade_ledger_json_bytes(ledger_a)
    bytes_b = canonical_trade_ledger_json_bytes(ledger_b)

    assert bytes_a == bytes_b
    assert bytes_a.endswith(b"\n")
    assert b"\r\n" not in bytes_a


def test_trade_ledger_artifact_can_be_loaded_by_analysis_modules(tmp_path: Path) -> None:
    result = PaperTradingSimulator().run(_signals())
    ledger = build_trade_ledger_from_paper_trades(result.trades, signals=_signals())

    artifact_path, sha_value = write_trade_ledger_artifact(tmp_path, ledger)
    loaded = load_trade_ledger_artifact(artifact_path)

    assert loaded == ledger
    assert (tmp_path / "trade-ledger.sha256").read_text(encoding="utf-8") == f"{sha_value}\n"


def test_trade_ledger_includes_attribution_via_existing_artifact_path() -> None:
    result = PaperTradingSimulator().run(_signals())
    ledger = build_trade_ledger_from_paper_trades(result.trades, signals=_signals())

    attributions = ledger.get("attributions")
    assert isinstance(attributions, list)
    assert len(attributions) == 2

    first = attributions[0]
    second = attributions[1]

    assert first["strategy_id"] == "TEST"
    assert first["originating_signal"]["reason"] == "rule-d"
    assert first["market_context"] == {
        "timeframe": "D1",
        "market_type": "stock",
        "data_source": "yahoo",
    }

    assert second["strategy_id"] == "TEST"
    assert second["originating_signal"]["reason"] == "rule-a"
    assert second["market_context"] == {
        "timeframe": "D1",
        "market_type": "stock",
        "data_source": "yahoo",
    }
