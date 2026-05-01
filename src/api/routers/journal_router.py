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

    return router
