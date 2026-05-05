"""Paper-execution performance analytics (P2-trading #1149, #1150).

All functions are pure: they operate on closed Trade records and return
deterministic, frozen dataclasses.  No I/O, no side effects.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, localcontext
from typing import Sequence

from cilly_trading.models import Trade


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sorted_closed(trades: Sequence[Trade]) -> list[Trade]:
    return sorted(
        (t for t in trades if t.status == "closed"),
        key=lambda t: t.closed_at or "",
    )


def _is_win(trade: Trade) -> bool:
    return (trade.realized_pnl or Decimal("0")) > Decimal("0")


def _max_drawdown_pct(
    closed: list[Trade],
    *,
    initial_equity: Decimal,
) -> Decimal:
    if not closed:
        return Decimal("0")
    running = Decimal("0")
    peak = initial_equity
    max_dd = Decimal("0")
    with localcontext() as ctx:
        ctx.prec = 28
        ctx.rounding = ROUND_HALF_UP
        for t in closed:
            running += t.realized_pnl or Decimal("0")
            current = initial_equity + running
            if current > peak:
                peak = current
            if peak > Decimal("0"):
                dd = (peak - current) / peak
                if dd > max_dd:
                    max_dd = dd
    return max_dd


def _bucket_metrics(
    group: list[Trade],
) -> tuple[int, Decimal, Decimal, Decimal]:
    """Return (trade_count, win_rate, expectancy, net_pnl) for a group."""
    if not group:
        return 0, Decimal("0"), Decimal("0"), Decimal("0")
    wins = [t for t in group if _is_win(t)]
    losses = [t for t in group if not _is_win(t)]
    win_rate = Decimal(len(wins)) / Decimal(len(group))
    avg_win = (
        sum((t.realized_pnl or Decimal("0")) for t in wins) / Decimal(len(wins))
        if wins
        else Decimal("0")
    )
    avg_loss = (
        abs(sum((t.realized_pnl or Decimal("0")) for t in losses)) / Decimal(len(losses))
        if losses
        else Decimal("0")
    )
    with localcontext() as ctx:
        ctx.prec = 28
        ctx.rounding = ROUND_HALF_UP
        loss_rate = Decimal("1") - win_rate
        expectancy = (win_rate * avg_win) - (loss_rate * avg_loss)
        net_pnl = sum((t.realized_pnl or Decimal("0")) for t in group)
    return len(group), win_rate, expectancy, net_pnl


# ---------------------------------------------------------------------------
# #1149 — PaperPerformanceSummary
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PaperPerformanceSummary:
    """Trader-relevant performance metrics computed from closed trades.

    All monetary values are in the account's quote currency.
    ``max_drawdown_pct`` is peak-to-trough drawdown from the equity curve.
    ``recovery_factor`` is ``net_pnl / (initial_equity * max_drawdown_pct)``;
    values above 1.0 indicate the strategy earns back more than its worst
    drawdown implies.
    """

    trade_count: int
    win_count: int
    loss_count: int
    win_rate: Decimal
    avg_win: Decimal
    avg_loss: Decimal
    expectancy: Decimal
    profit_factor: Decimal
    max_consecutive_wins: int
    max_consecutive_losses: int
    net_pnl: Decimal
    gross_profit: Decimal
    gross_loss: Decimal
    max_drawdown_pct: Decimal
    recovery_factor: Decimal


def compute_paper_performance_summary(
    trades: Sequence[Trade],
    *,
    initial_equity: Decimal = Decimal("100000"),
) -> PaperPerformanceSummary:
    """Compute performance metrics from a sequence of Trade records.

    Only ``status="closed"`` trades with a non-None ``realized_pnl`` are
    included.  Returns a zero-value summary when no closed trades exist.
    """
    closed = _sorted_closed(trades)
    if not closed:
        return PaperPerformanceSummary(
            trade_count=0,
            win_count=0,
            loss_count=0,
            win_rate=Decimal("0"),
            avg_win=Decimal("0"),
            avg_loss=Decimal("0"),
            expectancy=Decimal("0"),
            profit_factor=Decimal("0"),
            max_consecutive_wins=0,
            max_consecutive_losses=0,
            net_pnl=Decimal("0"),
            gross_profit=Decimal("0"),
            gross_loss=Decimal("0"),
            max_drawdown_pct=Decimal("0"),
            recovery_factor=Decimal("0"),
        )

    wins = [t for t in closed if _is_win(t)]
    losses = [t for t in closed if not _is_win(t)]

    gross_profit = sum((t.realized_pnl or Decimal("0")) for t in wins)
    gross_loss = abs(sum((t.realized_pnl or Decimal("0")) for t in losses))
    net_pnl = gross_profit - gross_loss

    with localcontext() as ctx:
        ctx.prec = 28
        ctx.rounding = ROUND_HALF_UP

        win_rate = Decimal(len(wins)) / Decimal(len(closed))
        avg_win = gross_profit / Decimal(len(wins)) if wins else Decimal("0")
        avg_loss = gross_loss / Decimal(len(losses)) if losses else Decimal("0")
        loss_rate = Decimal("1") - win_rate
        expectancy = (win_rate * avg_win) - (loss_rate * avg_loss)
        profit_factor = gross_profit / gross_loss if gross_loss > Decimal("0") else Decimal("0")

    # Consecutive streaks
    max_cons_wins = cur_wins = 0
    max_cons_losses = cur_losses = 0
    for t in closed:
        if _is_win(t):
            cur_wins += 1
            cur_losses = 0
        else:
            cur_losses += 1
            cur_wins = 0
        max_cons_wins = max(max_cons_wins, cur_wins)
        max_cons_losses = max(max_cons_losses, cur_losses)

    max_dd = _max_drawdown_pct(closed, initial_equity=initial_equity)
    with localcontext() as ctx:
        ctx.prec = 28
        ctx.rounding = ROUND_HALF_UP
        drawdown_amount = initial_equity * max_dd
        recovery_factor = (
            net_pnl / drawdown_amount if drawdown_amount > Decimal("0") else Decimal("0")
        )

    return PaperPerformanceSummary(
        trade_count=len(closed),
        win_count=len(wins),
        loss_count=len(losses),
        win_rate=win_rate,
        avg_win=avg_win,
        avg_loss=avg_loss,
        expectancy=expectancy,
        profit_factor=profit_factor,
        max_consecutive_wins=max_cons_wins,
        max_consecutive_losses=max_cons_losses,
        net_pnl=net_pnl,
        gross_profit=gross_profit,
        gross_loss=gross_loss,
        max_drawdown_pct=max_dd,
        recovery_factor=recovery_factor,
    )


# ---------------------------------------------------------------------------
# #1150 — PaperPerformanceAttribution
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AttributionBucket:
    """Performance slice for a single grouping dimension."""

    trade_count: int
    win_rate: Decimal
    expectancy: Decimal
    net_pnl: Decimal


@dataclass(frozen=True)
class PaperPerformanceAttribution:
    """Per-strategy and per-symbol breakdown of closed-trade performance.

    ``by_strategy_symbol`` is keyed by ``(strategy_id, symbol)`` tuples.
    All buckets with zero trades are omitted.
    """

    by_strategy: dict[str, AttributionBucket]
    by_symbol: dict[str, AttributionBucket]
    by_strategy_symbol: dict[tuple[str, str], AttributionBucket]


def compute_paper_performance_attribution(
    trades: Sequence[Trade],
) -> PaperPerformanceAttribution:
    """Compute attribution buckets from a sequence of Trade records.

    Only ``status="closed"`` trades are included.
    """
    closed = _sorted_closed(trades)

    strategy_groups: dict[str, list[Trade]] = {}
    symbol_groups: dict[str, list[Trade]] = {}
    pair_groups: dict[tuple[str, str], list[Trade]] = {}

    for t in closed:
        strat = t.strategy_id
        sym = t.symbol
        strategy_groups.setdefault(strat, []).append(t)
        symbol_groups.setdefault(sym, []).append(t)
        pair_groups.setdefault((strat, sym), []).append(t)

    def _to_bucket(group: list[Trade]) -> AttributionBucket:
        count, wr, exp, net = _bucket_metrics(group)
        return AttributionBucket(
            trade_count=count,
            win_rate=wr,
            expectancy=exp,
            net_pnl=net,
        )

    return PaperPerformanceAttribution(
        by_strategy={k: _to_bucket(v) for k, v in strategy_groups.items()},
        by_symbol={k: _to_bucket(v) for k, v in symbol_groups.items()},
        by_strategy_symbol={k: _to_bucket(v) for k, v in pair_groups.items()},
    )


__all__ = [
    "AttributionBucket",
    "PaperPerformanceAttribution",
    "PaperPerformanceSummary",
    "compute_paper_performance_attribution",
    "compute_paper_performance_summary",
]
