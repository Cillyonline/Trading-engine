from __future__ import annotations

from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from typing import Any, Mapping, Sequence

_QUANT = Decimal("0.000000000001")
_ZERO = Decimal("0")
_ONE = Decimal("1")


def _to_decimal(value: object) -> Decimal | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, Decimal):
        number = value
    elif isinstance(value, (int, float, str)):
        try:
            number = Decimal(str(value))
        except Exception:
            return None
    else:
        return None
    if not number.is_finite():
        return None
    return number


def _round_12(value: Decimal) -> Decimal:
    rounded = value.quantize(_QUANT, rounding=ROUND_HALF_EVEN)
    if rounded == _ZERO:
        return _ZERO
    return rounded


def _to_float(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return float(_round_12(value))


def _trade_sort_key(item: tuple[int, Mapping[str, object]]) -> tuple[str, str, str, str, str, int]:
    index, trade = item
    return (
        str(trade.get("exit_timestamp") or ""),
        str(trade.get("entry_timestamp") or ""),
        str(trade.get("symbol") or ""),
        str(trade.get("strategy_id") or ""),
        str(trade.get("trade_id") or ""),
        index,
    )


def _extract_trade_pnls_and_returns(
    trades: Sequence[Mapping[str, object]],
) -> tuple[list[Decimal], list[Decimal]]:
    ordered = sorted(
        [(idx, trade) for idx, trade in enumerate(trades) if isinstance(trade, Mapping)],
        key=_trade_sort_key,
    )

    pnls: list[Decimal] = []
    returns: list[Decimal] = []
    for _, trade in ordered:
        pnl = _to_decimal(trade.get("pnl"))
        if pnl is None:
            continue

        pnls.append(pnl)

        entry_price = _to_decimal(trade.get("entry_price"))
        quantity = _to_decimal(trade.get("quantity"))
        if entry_price is None or quantity is None:
            continue

        notional = abs(entry_price * quantity)
        if notional <= _ZERO:
            continue

        returns.append(pnl / notional)

    return pnls, returns


def _compute_win_rate(pnls: list[Decimal]) -> Decimal | None:
    if not pnls:
        return None
    wins = sum(1 for pnl in pnls if pnl > _ZERO)
    return Decimal(wins) / Decimal(len(pnls))


def _compute_profit_factor(pnls: list[Decimal]) -> Decimal | None:
    if not pnls:
        return None
    gross_profit = sum((pnl for pnl in pnls if pnl > _ZERO), _ZERO)
    gross_loss = sum((-pnl for pnl in pnls if pnl < _ZERO), _ZERO)
    if gross_loss == _ZERO:
        return None
    return gross_profit / gross_loss


def _compute_sharpe_ratio(
    returns: list[Decimal],
    periods_per_year: int | None = None,
) -> Decimal | None:
    """Compute the Sharpe ratio from a list of per-trade returns.

    Uses sample standard deviation (n-1 divisor) for consistency with Sortino.
    Without ``periods_per_year`` the result is an unannnualized per-observation
    ratio.  Pass ``periods_per_year=252`` for daily-bar strategies to annualize.
    """
    count = len(returns)
    if count < 2:
        return None

    mean_return = sum(returns, _ZERO) / Decimal(count)
    variance_sum = sum(((value - mean_return) ** 2 for value in returns), _ZERO)
    variance = variance_sum / Decimal(count - 1)  # sample std dev
    if variance <= _ZERO:
        return None

    with localcontext() as context:
        context.prec = 50
        volatility = variance.sqrt()
    if volatility == _ZERO:
        return None

    ratio = mean_return / volatility
    if periods_per_year is not None and periods_per_year > 0:
        with localcontext() as context:
            context.prec = 50
            ratio = ratio * Decimal(periods_per_year).sqrt()
    return ratio


def _compute_sortino_ratio(
    returns: list[Decimal],
    periods_per_year: int | None = None,
) -> Decimal | None:
    """Compute the Sortino ratio from a list of per-trade returns.

    Uses sample standard deviation (n-1 divisor) consistent with Sharpe.
    MAR (minimum acceptable return) is assumed to be zero.
    Without ``periods_per_year`` the result is an unannnualized per-observation
    ratio.  Pass ``periods_per_year=252`` for daily-bar strategies to annualize.
    """
    count = len(returns)
    if count < 2:
        return None

    mean_return = sum(returns, _ZERO) / Decimal(count)
    downside_sum = sum((((value if value < _ZERO else _ZERO) ** 2) for value in returns), _ZERO)
    if downside_sum == _ZERO:
        return None

    downside_variance = downside_sum / Decimal(count - 1)  # sample std dev, consistent with Sharpe
    with localcontext() as context:
        context.prec = 50
        downside_deviation = downside_variance.sqrt()
    if downside_deviation == _ZERO:
        return None

    ratio = mean_return / downside_deviation
    if periods_per_year is not None and periods_per_year > 0:
        with localcontext() as context:
            context.prec = 50
            ratio = ratio * Decimal(periods_per_year).sqrt()
    return ratio


def _compute_calmar_ratio(returns: list[Decimal]) -> Decimal | None:
    """Compute the Calmar ratio (total return / max drawdown).

    Drawdown is measured at trade-close boundaries only; intra-trade adverse
    moves are not captured.  The ratio is not annualized because trade
    frequency and holding period are not available here.
    """
    if not returns:
        return None

    equity = _ONE
    peak = _ONE
    max_drawdown = _ZERO

    for trade_return in returns:
        equity *= (_ONE + trade_return)
        if equity > peak:
            peak = equity
        if peak > _ZERO:
            drawdown = (peak - equity) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown

    if max_drawdown == _ZERO:
        return None

    total_return = equity - _ONE
    return total_return / max_drawdown


def compute_risk_adjusted_metrics_from_trade_ledger(
    payload: Mapping[str, Any],
    periods_per_year: int | None = None,
) -> dict[str, float | None]:
    """Compute risk-adjusted performance metrics from a trade ledger payload.

    Args:
        payload: dict containing a ``"trades"`` list of trade records.
        periods_per_year: optional annualization factor (e.g. 252 for daily
            bars).  When omitted, Sharpe and Sortino are unannnualized
            per-observation ratios and are not comparable to industry benchmarks
            that assume annualized figures.
    """
    trades_raw = payload.get("trades")
    if not isinstance(trades_raw, list):
        trades: list[Mapping[str, object]] = []
    else:
        trades = [item for item in trades_raw if isinstance(item, Mapping)]

    pnls, returns = _extract_trade_pnls_and_returns(trades)

    metrics = {
        "sharpe_ratio": _to_float(_compute_sharpe_ratio(returns, periods_per_year)),
        "sortino_ratio": _to_float(_compute_sortino_ratio(returns, periods_per_year)),
        "calmar_ratio": _to_float(_compute_calmar_ratio(returns)),
        "profit_factor": _to_float(_compute_profit_factor(pnls)),
        "win_rate": _to_float(_compute_win_rate(pnls)),
    }
    return metrics


__all__ = ["compute_risk_adjusted_metrics_from_trade_ledger"]
