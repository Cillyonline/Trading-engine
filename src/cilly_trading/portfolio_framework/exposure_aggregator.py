"""Pure and deterministic portfolio exposure aggregation."""

from __future__ import annotations

from dataclasses import dataclass

from cilly_trading.portfolio_framework.contract import PortfolioState


@dataclass(frozen=True)
class StrategyExposure:
    """Aggregated exposure information for one strategy.

    Attributes:
        strategy_id: Strategy identifier.
        total_absolute_notional: Sum of absolute notional exposure for strategy positions.
        net_notional: Sum of signed notional exposure for strategy positions.
        gross_exposure_pct: Strategy gross exposure as fraction of absolute account equity.
        net_exposure_pct: Strategy net exposure as fraction of absolute account equity.
    """

    strategy_id: str
    total_absolute_notional: float
    net_notional: float
    gross_exposure_pct: float
    net_exposure_pct: float


@dataclass(frozen=True)
class SymbolExposure:
    """Aggregated exposure information for one symbol.

    Attributes:
        symbol: Instrument symbol.
        total_absolute_notional: Sum of absolute notional exposure for symbol positions.
        net_notional: Sum of signed notional exposure for symbol positions.
        gross_exposure_pct: Symbol gross exposure as fraction of absolute account equity.
        net_exposure_pct: Symbol net exposure as fraction of absolute account equity.
    """

    symbol: str
    total_absolute_notional: float
    net_notional: float
    gross_exposure_pct: float
    net_exposure_pct: float


@dataclass(frozen=True)
class PositionExposure:
    """Normalized exposure information for one position.

    Attributes:
        strategy_id: Strategy identifier that owns the position.
        symbol: Instrument symbol.
        quantity: Signed quantity.
        mark_price: Mark price used for notional.
        notional: Signed notional exposure.
        absolute_notional: Absolute notional exposure.
        exposure_pct: Absolute notional as a fraction of absolute account equity.
    """

    strategy_id: str
    symbol: str
    quantity: float
    mark_price: float
    notional: float
    absolute_notional: float
    exposure_pct: float


@dataclass(frozen=True)
class PortfolioExposureSummary:
    """Aggregate portfolio exposure metrics.

    Attributes:
        strategy_exposures: Deterministically ordered strategy exposure rows.
        symbol_exposures: Deterministically ordered symbol exposure rows.
        position_exposures: Deterministically ordered position exposure rows.
        total_absolute_notional: Sum of absolute notional exposure across positions.
        net_notional: Sum of signed notional exposure across positions.
        gross_exposure_pct: Gross exposure as fraction of absolute account equity.
        net_exposure_pct: Net exposure as fraction of absolute account equity.
    """

    strategy_exposures: tuple[StrategyExposure, ...]
    symbol_exposures: tuple[SymbolExposure, ...]
    position_exposures: tuple[PositionExposure, ...]
    total_absolute_notional: float
    net_notional: float
    gross_exposure_pct: float
    net_exposure_pct: float


def aggregate_portfolio_exposure(state: PortfolioState) -> PortfolioExposureSummary:
    """Aggregate deterministic portfolio exposure metrics from immutable state.

    Args:
        state: Immutable portfolio state.

    Returns:
        PortfolioExposureSummary: Deterministic exposure summary.
    """

    absolute_equity = abs(state.account_equity)

    sorted_positions = tuple(
        sorted(
            state.positions,
            key=lambda position: (
                position.strategy_id,
                position.symbol,
                position.quantity,
                position.mark_price,
            ),
        )
    )

    position_exposures = tuple(
        _position_exposure(
            strategy_id=position.strategy_id,
            symbol=position.symbol,
            quantity=position.quantity,
            mark_price=position.mark_price,
            absolute_equity=absolute_equity,
        )
        for position in sorted_positions
    )

    total_absolute_notional = sum(item.absolute_notional for item in position_exposures)
    net_notional = sum(item.notional for item in position_exposures)

    strategy_exposures = _aggregate_by_strategy(position_exposures, absolute_equity)
    symbol_exposures = _aggregate_by_symbol(position_exposures, absolute_equity)

    gross_exposure_pct = _ratio_or_inf(total_absolute_notional, absolute_equity)
    net_exposure_pct = _signed_ratio_or_inf(net_notional, absolute_equity)

    return PortfolioExposureSummary(
        strategy_exposures=strategy_exposures,
        symbol_exposures=symbol_exposures,
        position_exposures=position_exposures,
        total_absolute_notional=total_absolute_notional,
        net_notional=net_notional,
        gross_exposure_pct=gross_exposure_pct,
        net_exposure_pct=net_exposure_pct,
    )


def _position_exposure(
    *,
    strategy_id: str,
    symbol: str,
    quantity: float,
    mark_price: float,
    absolute_equity: float,
) -> PositionExposure:
    """Build normalized per-position exposure rows."""

    notional = quantity * mark_price
    absolute_notional = abs(notional)

    return PositionExposure(
        strategy_id=strategy_id,
        symbol=symbol,
        quantity=quantity,
        mark_price=mark_price,
        notional=notional,
        absolute_notional=absolute_notional,
        exposure_pct=_ratio_or_inf(absolute_notional, absolute_equity),
    )


def _aggregate_by_strategy(
    position_exposures: tuple[PositionExposure, ...],
    absolute_equity: float,
) -> tuple[StrategyExposure, ...]:
    """Aggregate exposures grouped by strategy_id in deterministic order."""

    strategy_ids = tuple(sorted({item.strategy_id for item in position_exposures}))

    return tuple(
        _build_strategy_exposure(
            strategy_id=strategy_id,
            position_exposures=position_exposures,
            absolute_equity=absolute_equity,
        )
        for strategy_id in strategy_ids
    )


def _build_strategy_exposure(
    *,
    strategy_id: str,
    position_exposures: tuple[PositionExposure, ...],
    absolute_equity: float,
) -> StrategyExposure:
    """Build one strategy exposure row."""

    rows = tuple(item for item in position_exposures if item.strategy_id == strategy_id)
    total_absolute_notional = sum(item.absolute_notional for item in rows)
    net_notional = sum(item.notional for item in rows)

    return StrategyExposure(
        strategy_id=strategy_id,
        total_absolute_notional=total_absolute_notional,
        net_notional=net_notional,
        gross_exposure_pct=_ratio_or_inf(total_absolute_notional, absolute_equity),
        net_exposure_pct=_signed_ratio_or_inf(net_notional, absolute_equity),
    )


def _aggregate_by_symbol(
    position_exposures: tuple[PositionExposure, ...],
    absolute_equity: float,
) -> tuple[SymbolExposure, ...]:
    """Aggregate exposures grouped by symbol in deterministic order."""

    symbols = tuple(sorted({item.symbol for item in position_exposures}))

    return tuple(
        _build_symbol_exposure(
            symbol=symbol,
            position_exposures=position_exposures,
            absolute_equity=absolute_equity,
        )
        for symbol in symbols
    )


def _build_symbol_exposure(
    *,
    symbol: str,
    position_exposures: tuple[PositionExposure, ...],
    absolute_equity: float,
) -> SymbolExposure:
    """Build one symbol exposure row."""

    rows = tuple(item for item in position_exposures if item.symbol == symbol)
    total_absolute_notional = sum(item.absolute_notional for item in rows)
    net_notional = sum(item.notional for item in rows)

    return SymbolExposure(
        symbol=symbol,
        total_absolute_notional=total_absolute_notional,
        net_notional=net_notional,
        gross_exposure_pct=_ratio_or_inf(total_absolute_notional, absolute_equity),
        net_exposure_pct=_signed_ratio_or_inf(net_notional, absolute_equity),
    )


def _ratio_or_inf(value: float, denominator: float) -> float:
    """Return deterministic non-negative ratio with explicit zero-denominator behavior."""

    if denominator == 0.0:
        return float("inf") if value > 0.0 else 0.0
    return value / denominator


def _signed_ratio_or_inf(value: float, denominator: float) -> float:
    """Return deterministic signed ratio with explicit zero-denominator behavior."""

    if denominator == 0.0:
        if value == 0.0:
            return 0.0
        return float("inf") if value > 0.0 else float("-inf")
    return value / denominator
