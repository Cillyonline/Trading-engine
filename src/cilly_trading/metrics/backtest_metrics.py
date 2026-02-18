from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_EVEN
import math
from statistics import stdev
from typing import Any, Mapping, Sequence


_QUANT = Decimal("0.000000000001")


def _normalize_negative_zero(value: float) -> float:
    if value == 0.0:
        return 0.0
    return value


def _round_12(value: float) -> float:
    rounded = float(Decimal(str(value)).quantize(_QUANT, rounding=ROUND_HALF_EVEN))
    return _normalize_negative_zero(rounded)


def _to_numeric(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        numeric = float(value)
    elif isinstance(value, str):
        try:
            numeric = float(value.strip())
        except (TypeError, ValueError):
            return None
    else:
        return None

    if not math.isfinite(numeric):
        return None
    return numeric


def _timestamp_to_epoch_seconds(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        ts = float(value)
        if math.isfinite(ts):
            return ts
        return None

    if not isinstance(value, str):
        return None

    raw = value.strip()
    if not raw:
        return None

    candidate = raw.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.timestamp()


def _sorted_equity_curve(curve: Sequence[Mapping[str, Any]] | None) -> list[tuple[float, float]]:
    if curve is None:
        return []

    sortable: list[tuple[tuple[float, str, float], tuple[float, float]]] = []
    for point in curve:
        if not isinstance(point, Mapping):
            continue
        timestamp = _timestamp_to_epoch_seconds(point.get("timestamp"))
        equity = _to_numeric(point.get("equity"))
        if timestamp is None or equity is None:
            continue
        sortable.append(((timestamp, str(point.get("timestamp", "")), equity), (timestamp, equity)))

    sortable.sort(key=lambda item: item[0])
    return [item[1] for item in sortable]


def _trade_exit_sort_key(trade: Mapping[str, Any]) -> tuple[float, str]:
    exit_ts = _timestamp_to_epoch_seconds(trade.get("exit_ts"))
    if exit_ts is None:
        exit_ts = 0.0

    trade_id = trade.get("trade_id")
    if trade_id is None:
        trade_id = ""

    return (exit_ts, str(trade_id))


def _extract_trade_pnls(trades: Sequence[Mapping[str, Any]] | None) -> list[float]:
    if trades is None:
        return []

    sorted_trades = sorted(
        [trade for trade in trades if isinstance(trade, Mapping)],
        key=_trade_exit_sort_key,
    )

    pnls: list[float] = []
    for trade in sorted_trades:
        pnl = _to_numeric(trade.get("pnl"))
        if pnl is None:
            pnl = _to_numeric(trade.get("profit"))
        if pnl is None:
            pnl = _to_numeric(trade.get("realized_pnl"))
        if pnl is not None:
            pnls.append(_round_12(pnl))

    return pnls


def _compute_total_return(start_equity: float | None, end_equity: float | None) -> float | None:
    if start_equity is None or end_equity is None or start_equity == 0.0:
        return None
    return _round_12((end_equity - start_equity) / start_equity)


def _compute_cagr(equity_points: list[tuple[float, float]]) -> float | None:
    if len(equity_points) < 2:
        return None

    start_ts, start_equity = equity_points[0]
    end_ts, end_equity = equity_points[-1]

    if start_equity <= 0.0 or end_equity < 0.0:
        return None

    years = (end_ts - start_ts) / (365.25 * 24 * 60 * 60)
    if years <= 0.0:
        return None

    return _round_12((end_equity / start_equity) ** (1.0 / years) - 1.0)


def _compute_max_drawdown(equity_points: list[tuple[float, float]]) -> float | None:
    if len(equity_points) < 2:
        return None

    peak = float("-inf")
    found_positive_peak = False
    max_drawdown = 0.0

    for _, equity in equity_points:
        if equity > peak:
            peak = equity
        if peak > 0.0:
            found_positive_peak = True
            drawdown = (peak - equity) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown

    if not found_positive_peak:
        return None

    return _round_12(max_drawdown)


def _compute_sharpe_ratio(equity_points: list[tuple[float, float]]) -> float | None:
    if len(equity_points) < 2:
        return None

    returns: list[float] = []
    for idx in range(1, len(equity_points)):
        previous = equity_points[idx - 1][1]
        current = equity_points[idx][1]
        if previous == 0.0:
            continue
        returns.append((current - previous) / previous)

    if len(returns) < 2:
        return None

    volatility = stdev(returns)
    if volatility == 0.0:
        return None

    avg_return = sum(returns) / len(returns)
    return _round_12(avg_return / volatility)


def compute_backtest_metrics(
    *,
    summary: Mapping[str, Any] | None = None,
    equity_curve: Sequence[Mapping[str, Any]] | None = None,
    trades: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    sorted_equity_curve = _sorted_equity_curve(equity_curve)

    summary_start = _to_numeric(summary.get("start_equity")) if isinstance(summary, Mapping) else None
    summary_end = _to_numeric(summary.get("end_equity")) if isinstance(summary, Mapping) else None

    curve_start = sorted_equity_curve[0][1] if sorted_equity_curve else None
    curve_end = sorted_equity_curve[-1][1] if sorted_equity_curve else None

    start_equity = summary_start if summary_start is not None else curve_start
    end_equity = summary_end if summary_end is not None else curve_end

    total_return = _compute_total_return(start_equity, end_equity)

    if len(sorted_equity_curve) < 2:
        cagr = None
        max_drawdown = None
        sharpe_ratio = None
    else:
        cagr = _compute_cagr(sorted_equity_curve)
        max_drawdown = _compute_max_drawdown(sorted_equity_curve)
        sharpe_ratio = _compute_sharpe_ratio(sorted_equity_curve)

    trade_pnls = _extract_trade_pnls(trades)

    return {
        "start_equity": _round_12(start_equity) if start_equity is not None else None,
        "end_equity": _round_12(end_equity) if end_equity is not None else None,
        "total_return": total_return,
        "cagr": cagr,
        "max_drawdown": max_drawdown,
        "sharpe_ratio": sharpe_ratio,
        "trade_pnls": trade_pnls,
    }


def compute_metrics(payload: Mapping[str, Any]) -> dict[str, Any]:
    return compute_backtest_metrics(
        summary=payload.get("summary") if isinstance(payload, Mapping) else None,
        equity_curve=payload.get("equity_curve") if isinstance(payload, Mapping) else None,
        trades=payload.get("trades") if isinstance(payload, Mapping) else None,
    )


def calculate_metrics(payload: Mapping[str, Any]) -> dict[str, Any]:
    return compute_metrics(payload)
