from __future__ import annotations

from cilly_trading.trade_attribution import build_trade_attribution


def _signals() -> list[dict[str, object]]:
    return [
        {
            "signal_id": "sig-rsi2-1",
            "symbol": "AAPL",
            "strategy": "RSI2",
            "action": "entry",
            "timestamp": "2024-01-01T09:30:00Z",
            "confirmation_rule": "rsi2-oversold",
            "timeframe": "D1",
            "market_type": "stock",
            "data_source": "yahoo",
        },
        {
            "signal_id": "sig-rsi2-exit",
            "symbol": "AAPL",
            "strategy": "RSI2",
            "action": "exit",
            "timestamp": "2024-01-02T09:30:00Z",
            "confirmation_rule": "rsi2-exit",
            "timeframe": "D1",
            "market_type": "stock",
            "data_source": "yahoo",
        },
        {
            "signal_id": "sig-turtle-1",
            "symbol": "BTC-USD",
            "strategy": "TURTLE",
            "action": "entry",
            "timestamp": "2024-01-03T00:00:00Z",
            "confirmation_rule": "turtle-breakout",
            "timeframe": "H4",
            "market_type": "crypto",
            "data_source": "binance",
            "reasons": [
                {
                    "reason_id": "sr_123",
                    "reason_type": "PATTERN_MATCH",
                    "signal_id": "sig-turtle-1",
                    "ordering_key": 0,
                    "rule_ref": {"rule_id": "TURTLE_BREAKOUT_CONFIRMED", "rule_version": "1.0.0"},
                    "data_refs": [],
                }
            ],
        },
    ]


def _trades() -> list[dict[str, object]]:
    return [
        {
            "symbol": "BTC-USD",
            "strategy": "TURTLE",
            "entry_date": "2024-01-03T00:00:00Z",
            "exit_date": "2024-01-03T04:00:00Z",
            "entry_price": 100.0,
            "exit_price": 104.0,
            "reason_entry": "sr_123",
            "timeframe": "H4",
            "market_type": "crypto",
            "data_source": "binance",
        },
        {
            "symbol": "AAPL",
            "strategy": "RSI2",
            "entry_date": "2024-01-01T09:30:00Z",
            "exit_date": "2024-01-02T09:30:00Z",
            "entry_price": 100.0,
            "exit_price": 102.0,
            "reason_entry": "rsi2-oversold",
            "timeframe": "D1",
            "market_type": "stock",
            "data_source": "yahoo",
        },
    ]


def test_trade_attribution_is_deterministic_and_order_independent() -> None:
    first = build_trade_attribution(trades=_trades(), signals=_signals())
    second = build_trade_attribution(trades=list(reversed(_trades())), signals=list(reversed(_signals())))

    assert first == second
    assert first["artifact"] == "trade_attribution"
    assert first["artifact_version"] == "1"


def test_trade_attribution_links_each_trade_to_originating_signal() -> None:
    payload = build_trade_attribution(trades=_trades(), signals=_signals())
    attributions = payload["attributions"]

    assert isinstance(attributions, list)
    assert len(attributions) == 2

    assert attributions[0]["strategy_id"] == "RSI2"
    assert attributions[0]["originating_signal"]["signal_id"] == "sig-rsi2-1"
    assert attributions[0]["originating_signal"]["reason"] == "rsi2-oversold"
    assert attributions[0]["market_context"] == {
        "timeframe": "D1",
        "market_type": "stock",
        "data_source": "yahoo",
    }

    assert attributions[1]["strategy_id"] == "TURTLE"
    assert attributions[1]["originating_signal"]["signal_id"] == "sig-turtle-1"
    assert attributions[1]["originating_signal"]["reason"] == "sr_123"
    assert attributions[1]["market_context"] == {
        "timeframe": "H4",
        "market_type": "crypto",
        "data_source": "binance",
    }


def test_trade_attribution_raises_when_trade_cannot_be_linked() -> None:
    mismatched_trade = _trades()[0] | {"reason_entry": "missing-signal-reason"}

    try:
        build_trade_attribution(trades=[mismatched_trade], signals=_signals())
    except ValueError as exc:
        assert "no originating signal found" in str(exc)
    else:
        raise AssertionError("Expected unmatched trade attribution to raise ValueError")
