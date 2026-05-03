"""Data quality API router.

Provides GET /data/quality/{symbol} returning a deterministic quality report
for ingested market data. The data provider callable is injected at build time,
allowing the router to be tested without a real database.
"""

from __future__ import annotations

from typing import Any, Callable, Sequence

from fastapi import APIRouter, HTTPException


def build_data_quality_router(
    *,
    get_bars_for_symbol: Callable[[str], Sequence[dict[str, Any]]],
    sigma_threshold: float = 5.0,
) -> APIRouter:
    """Build the data quality router with an injected data provider.

    Args:
        get_bars_for_symbol: Callable that accepts a symbol string and returns
            a sequence of bar dicts. Each dict should contain at least
            ``timestamp`` and ``close`` keys.
        sigma_threshold: Standard deviation multiplier for outlier detection.

    Returns:
        Configured APIRouter.
    """
    from cilly_trading.engine.data_quality import compute_data_quality_report

    router = APIRouter(prefix="/data", tags=["data-quality"])

    @router.get(
        "/quality/{symbol}",
        summary="Data quality report for a symbol",
        description=(
            "Returns a deterministic data quality summary for the ingested bars "
            "of the requested symbol. Reports gaps, outliers, missing bars, and "
            "timezone consistency. Returns no_data=true when no bars exist."
        ),
    )
    def get_data_quality(symbol: str) -> dict[str, Any]:
        symbol_upper = symbol.strip().upper()
        if not symbol_upper:
            raise HTTPException(status_code=400, detail="symbol must not be empty")

        bars = get_bars_for_symbol(symbol_upper)
        report = compute_data_quality_report(
            symbol=symbol_upper,
            bars=bars,
            sigma_threshold=sigma_threshold,
        )
        return report.to_dict()

    return router
