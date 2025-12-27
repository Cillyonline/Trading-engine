from __future__ import annotations

from api import main


def test_screener_response_schema_and_ordering(monkeypatch) -> None:
    signals = [
        {
            "symbol": "BBB",
            "stage": "setup",
            "score": 50,
            "signal_strength": 0.5,
            "strategy": "RSI2",
        },
        {
            "symbol": "AAA",
            "stage": "setup",
            "score": 50,
            "signal_strength": 0.7,
            "strategy": "RSI2",
        },
        {
            "symbol": "AAC",
            "stage": "setup",
            "score": 50,
            "signal_strength": 0.7,
            "strategy": "TURTLE",
        },
        {
            "symbol": "CCC",
            "stage": "setup",
            "score": None,
            "signal_strength": 0.9,
            "strategy": "RSI2",
        },
        {
            "symbol": "DDD",
            "stage": "setup",
            "score": None,
            "signal_strength": None,
            "strategy": "RSI2",
        },
        {
            "symbol": "AAA",
            "stage": "setup",
            "score": 40,
            "signal_strength": 0.4,
            "strategy": "TURTLE",
        },
    ]

    def fake_run_watchlist_analysis(*args, **kwargs):
        return signals

    monkeypatch.setattr(main, "run_watchlist_analysis", fake_run_watchlist_analysis)

    request = main.ScreenerRequest(
        symbols=["AAA", "AAC", "BBB", "CCC", "DDD"],
        market_type="stock",
        lookback_days=200,
        min_score=0,
    )
    response = main.basic_screener(request)

    payload = response.model_dump()
    assert payload["market_type"] == "stock"

    items = payload["symbols"]
    assert [item["symbol"] for item in items] == ["AAA", "AAC", "BBB", "CCC", "DDD"]

    for item in items:
        assert set(["symbol", "score", "signal_strength", "setups"]).issubset(item.keys())

    top_item = items[0]
    assert top_item["symbol"] == "AAA"
    assert top_item["score"] == 50
    assert top_item["signal_strength"] == 0.7
