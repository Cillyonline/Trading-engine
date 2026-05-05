"""Lightweight market regime classifier (P2-trading #1151).

Classifies bar sequences into four regimes using Average Directional Index
(ADX) for trend strength and realized volatility for vol state.  All
functions are pure and side-effect-free.

Regime labels:
    trending_up    — ADX > threshold AND recent close above lookback close
    trending_down  — ADX > threshold AND recent close below lookback close
    volatile       — realized vol > high_vol_threshold (regardless of ADX)
    ranging        — everything else

Usage in paper execution:
    PaperExecutionRiskProfile.allowed_regimes = frozenset({"trending_up"})
    process_signal(signal, regime_state=classify_regime(bars))
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, log, sqrt
from typing import Literal, Sequence

from cilly_trading.engine.marketdata.models.market_data_models import Bar


RegimeLabel = Literal["trending_up", "trending_down", "ranging", "volatile"]

_ALL_REGIME_LABELS: frozenset[str] = frozenset(
    {"trending_up", "trending_down", "ranging", "volatile"}
)


@dataclass(frozen=True)
class RegimeState:
    """Snapshot of market regime at a point in time."""

    label: RegimeLabel
    adx: float
    realized_vol: float


def compute_adx(bars: Sequence[Bar], *, period: int = 14) -> float:
    """Compute Wilder's Average Directional Index for a bar sequence.

    Returns 0.0 when fewer than ``2 * period`` bars are available.
    """
    bars_list = list(bars)
    if len(bars_list) < period + 1:
        return 0.0

    tr_list: list[float] = []
    plus_dm_list: list[float] = []
    minus_dm_list: list[float] = []

    for i in range(1, len(bars_list)):
        curr = bars_list[i]
        prev = bars_list[i - 1]

        high = float(curr.high)
        low = float(curr.low)
        prev_close = float(prev.close)
        prev_high = float(prev.high)
        prev_low = float(prev.low)

        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))

        up_move = high - prev_high
        down_move = prev_low - low
        plus_dm = max(up_move, 0.0) if up_move > down_move else 0.0
        minus_dm = max(down_move, 0.0) if down_move > up_move else 0.0

        tr_list.append(tr)
        plus_dm_list.append(plus_dm)
        minus_dm_list.append(minus_dm)

    if len(tr_list) < period:
        return 0.0

    # Wilder's initial smoothing (simple sum for first period)
    smooth_tr = sum(tr_list[:period])
    smooth_plus = sum(plus_dm_list[:period])
    smooth_minus = sum(minus_dm_list[:period])

    dx_list: list[float] = []
    for i in range(period, len(tr_list)):
        smooth_tr = smooth_tr - smooth_tr / period + tr_list[i]
        smooth_plus = smooth_plus - smooth_plus / period + plus_dm_list[i]
        smooth_minus = smooth_minus - smooth_minus / period + minus_dm_list[i]

        if smooth_tr == 0.0:
            continue

        plus_di = 100.0 * smooth_plus / smooth_tr
        minus_di = 100.0 * smooth_minus / smooth_tr
        di_sum = plus_di + minus_di
        dx = 100.0 * abs(plus_di - minus_di) / di_sum if di_sum != 0.0 else 0.0
        dx_list.append(dx)

    if not dx_list:
        return 0.0

    # Wilder-smooth DX into ADX
    adx = sum(dx_list[:period]) / period if len(dx_list) >= period else sum(dx_list) / len(dx_list)
    for i in range(period, len(dx_list)):
        adx = (adx * (period - 1) + dx_list[i]) / period

    return adx if isfinite(adx) else 0.0


def compute_realized_vol(bars: Sequence[Bar], *, period: int = 20) -> float:
    """Compute annualized realized volatility from log-close returns.

    Uses the most recent ``period + 1`` bars.  Returns 0.0 when fewer
    bars are available or when closes contain non-positive values.
    """
    bars_list = list(bars)
    window = bars_list[-(period + 1):]
    closes = [float(b.close) for b in window if float(b.close) > 0]
    if len(closes) < 2:
        return 0.0

    log_returns = [log(closes[i] / closes[i - 1]) for i in range(1, len(closes))]
    n = len(log_returns)
    mean = sum(log_returns) / n
    variance = sum((r - mean) ** 2 for r in log_returns) / n
    rv = sqrt(variance) * sqrt(252)
    return rv if isfinite(rv) else 0.0


def classify_regime(
    bars: Sequence[Bar],
    *,
    adx_period: int = 14,
    vol_period: int = 20,
    trend_lookback: int = 20,
    adx_trend_threshold: float = 25.0,
    high_vol_threshold: float = 0.30,
) -> RegimeState:
    """Classify the current market regime from a bar sequence.

    Precedence:
        1. ``volatile``     — realized vol > high_vol_threshold
        2. ``trending_up``  — ADX > threshold AND latest close > lookback close
        3. ``trending_down`` — ADX > threshold AND latest close < lookback close
        4. ``ranging``      — fallback

    Requires at least ``max(adx_period * 2, trend_lookback) + 1`` bars for
    reliable results; returns ``ranging`` with zero indicators otherwise.
    """
    bars_list = list(bars)
    adx = compute_adx(bars_list, period=adx_period)
    rv = compute_realized_vol(bars_list, period=vol_period)

    if rv > high_vol_threshold:
        return RegimeState("volatile", adx, rv)

    if adx > adx_trend_threshold and len(bars_list) >= trend_lookback + 1:
        latest_close = float(bars_list[-1].close)
        lookback_close = float(bars_list[-trend_lookback - 1].close)
        if lookback_close > 0:
            if latest_close > lookback_close:
                return RegimeState("trending_up", adx, rv)
            if latest_close < lookback_close:
                return RegimeState("trending_down", adx, rv)

    return RegimeState("ranging", adx, rv)


__all__ = [
    "RegimeLabel",
    "RegimeState",
    "_ALL_REGIME_LABELS",
    "classify_regime",
    "compute_adx",
    "compute_realized_vol",
]
