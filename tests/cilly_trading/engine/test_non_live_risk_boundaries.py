from __future__ import annotations

import math

from cilly_trading.engine.portfolio import load_portfolio_state_from_env
from cilly_trading.portfolio.state import calculate_drawdown


def test_drawdown_is_bounded_to_one_for_negative_equity() -> None:
    assert calculate_drawdown(peak_equity=100_000.0, current_equity=-5_000.0) == 1.0


def test_drawdown_treats_non_finite_current_equity_as_full_drawdown() -> None:
    assert calculate_drawdown(peak_equity=100_000.0, current_equity=math.nan) == 1.0
    assert calculate_drawdown(peak_equity=100_000.0, current_equity=math.inf) == 1.0


def test_load_portfolio_state_from_env_ignores_negative_size_and_price() -> None:
    state = load_portfolio_state_from_env(
        environ={
            "CILLY_PORTFOLIO_POSITIONS": (
                "["
                '{"strategy_id":"valid","symbol":"AAPL","size":1.0,"average_price":100.0,"unrealized_pnl":2.0},'
                '{"strategy_id":"neg-size","symbol":"AAPL","size":-1.0,"average_price":100.0,"unrealized_pnl":0.0},'
                '{"strategy_id":"neg-price","symbol":"MSFT","size":1.0,"average_price":-50.0,"unrealized_pnl":0.0}'
                "]"
            )
        }
    )

    assert len(state.positions) == 1
    assert state.positions[0].strategy_id == "valid"
    assert state.positions[0].symbol == "AAPL"
