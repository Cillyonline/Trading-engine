"""Router for the manual trade journal (Phase 1)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from api.models.journal_models import (
    JournalTradeCreateRequest,
    JournalTradeExitRequest,
    JournalTradeResponse,
    JournalTradesListResponse,
    PerformanceGroupItem,
    PerformanceMetrics,
    PerformanceSummaryResponse,
    SignalPerformanceResponse,
)
from cilly_trading.models import PersistedTradePayload


@dataclass
class JournalRouterDependencies:
    require_role: Callable[[str], Callable[..., str]]
    get_trade_repo: Callable[[], object]


def build_journal_router(*, deps: JournalRouterDependencies) -> APIRouter:
    router = APIRouter(prefix="/journal", tags=["journal"])

    @router.post(
        "/trades",
        response_model=JournalTradeResponse,
        status_code=201,
        summary="Manuellen Trade eintragen",
        description=(
            "Trägt einen manuell ausgeführten Trade ein. "
            "Die signal_id verknüpft den Trade mit einem Screener-Signal."
        ),
    )
    def create_trade_handler(
        body: JournalTradeCreateRequest,
        _: str = Depends(deps.require_role("operator")),
    ) -> JournalTradeResponse:
        repo = deps.get_trade_repo()
        payload: PersistedTradePayload = {
            "symbol": body.symbol.strip().upper(),
            "strategy": body.strategy,
            "stage": body.stage,
            "timeframe": body.timeframe,
            "market_type": body.market_type,
            "data_source": body.data_source,
            "reason_entry": body.reason_entry,
        }
        if body.signal_id is not None:
            payload["signal_id"] = body.signal_id
        if body.entry_price is not None:
            payload["entry_price"] = body.entry_price
        if body.entry_date is not None:
            payload["entry_date"] = body.entry_date
        if body.notes is not None:
            payload["notes"] = body.notes

        trade_id = repo.save_trade(payload)
        saved = repo.get_trade(trade_id)
        if saved is None:
            raise HTTPException(status_code=500, detail="Trade could not be reloaded after save")
        return JournalTradeResponse.from_payload(dict(saved))

    @router.put(
        "/trades/{trade_id}/exit",
        response_model=JournalTradeResponse,
        summary="Exit-Preis nachtragen",
        description="Trägt Exit-Preis, Exit-Datum und Begründung für einen offenen Trade nach.",
    )
    def log_exit_handler(
        trade_id: int,
        body: JournalTradeExitRequest,
        _: str = Depends(deps.require_role("operator")),
    ) -> JournalTradeResponse:
        repo = deps.get_trade_repo()
        existing = repo.get_trade(trade_id)
        if existing is None:
            raise HTTPException(status_code=404, detail=f"Trade {trade_id} not found")
        if existing.get("exit_price") is not None:
            raise HTTPException(status_code=409, detail=f"Trade {trade_id} already has an exit")

        updated = repo.update_trade_exit(
            trade_id,
            exit_price=body.exit_price,
            exit_date=body.exit_date,
            reason_exit=body.reason_exit,
        )
        if not updated:
            raise HTTPException(status_code=500, detail="Exit could not be saved")

        saved = repo.get_trade(trade_id)
        return JournalTradeResponse.from_payload(dict(saved))

    @router.get(
        "/trades",
        response_model=JournalTradesListResponse,
        summary="Trades auflisten",
        description="Listet manuell eingetragene Trades mit optionalen Filtern.",
    )
    def list_trades_handler(
        symbol: Optional[str] = Query(default=None),
        strategy: Optional[str] = Query(default=None),
        signal_id: Optional[str] = Query(default=None),
        status: Optional[Literal["open", "closed"]] = Query(default=None),
        limit: int = Query(default=50, ge=1, le=500),
        _: str = Depends(deps.require_role("read_only")),
    ) -> JournalTradesListResponse:
        repo = deps.get_trade_repo()
        trades = repo.list_trades(
            limit=limit,
            symbol=symbol,
            strategy=strategy,
            signal_id=signal_id,
            status=status,
        )
        items = [JournalTradeResponse.from_payload(dict(t)) for t in trades]
        return JournalTradesListResponse(items=items, total=len(items))

    @router.get(
        "/performance",
        response_model=PerformanceSummaryResponse,
        summary="Gesamt-Performance",
        description=(
            "Aggregierte Performance über alle manuell eingetragenen Trades. "
            "Zeigt Kennzahlen gesamt sowie aufgeschlüsselt nach Strategie und Symbol."
        ),
    )
    def performance_summary_handler(
        symbol: Optional[str] = Query(default=None),
        strategy: Optional[str] = Query(default=None),
        limit: int = Query(default=500, ge=1, le=1000),
        _: str = Depends(deps.require_role("read_only")),
    ) -> PerformanceSummaryResponse:
        repo = deps.get_trade_repo()
        raw = repo.list_trades(limit=limit, symbol=symbol, strategy=strategy)
        trades = [JournalTradeResponse.from_payload(dict(t)) for t in raw]

        overall = PerformanceMetrics.from_trades(trades)

        by_strategy = _group_performance(trades, key_fn=lambda t: t.strategy)
        by_symbol = _group_performance(trades, key_fn=lambda t: t.symbol)

        return PerformanceSummaryResponse(
            metrics=overall,
            by_strategy=by_strategy,
            by_symbol=by_symbol,
        )

    @router.get(
        "/signals/{signal_id}/performance",
        response_model=SignalPerformanceResponse,
        summary="Performance für ein Signal",
        description="Zeigt alle Trades die aus einem bestimmten Signal entstanden sind, mit aggregierten Kennzahlen.",
    )
    def signal_performance_handler(
        signal_id: str,
        _: str = Depends(deps.require_role("read_only")),
    ) -> SignalPerformanceResponse:
        repo = deps.get_trade_repo()
        raw = repo.list_trades(limit=1000, signal_id=signal_id)
        if not raw:
            raise HTTPException(
                status_code=404,
                detail=f"No trades found for signal_id={signal_id!r}",
            )
        trades = [JournalTradeResponse.from_payload(dict(t)) for t in raw]
        return SignalPerformanceResponse(
            signal_id=signal_id,
            metrics=PerformanceMetrics.from_trades(trades),
            trades=trades,
        )

    return router


def _group_performance(
    trades: list[JournalTradeResponse],
    *,
    key_fn,
) -> list[PerformanceGroupItem]:
    groups: dict[str, list[JournalTradeResponse]] = {}
    for t in trades:
        k = key_fn(t)
        groups.setdefault(k, []).append(t)
    return sorted(
        [
            PerformanceGroupItem(key=k, metrics=PerformanceMetrics.from_trades(v))
            for k, v in groups.items()
        ],
        key=lambda item: (item.metrics.closed_trades or 0),
        reverse=True,
    )
