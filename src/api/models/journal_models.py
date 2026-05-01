"""Pydantic models for the manual trade journal API."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class JournalTradeCreateRequest(BaseModel):
    signal_id: Optional[str] = Field(default=None, description="Signal-ID aus dem Screener (optional)")
    symbol: str = Field(min_length=1)
    strategy: str = Field(min_length=1)
    stage: Literal["setup", "entry_confirmed"] = "entry_confirmed"
    entry_price: Optional[float] = Field(default=None, gt=0)
    entry_date: Optional[str] = Field(default=None, description="ISO-8601 date, e.g. 2026-05-01")
    timeframe: str = Field(min_length=1, description="e.g. D1, W1")
    market_type: Literal["stock", "crypto"] = "stock"
    data_source: Literal["yahoo", "binance"] = "yahoo"
    reason_entry: str = Field(min_length=1, description="Begründung für den Entry")
    notes: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class JournalTradeExitRequest(BaseModel):
    exit_price: float = Field(gt=0)
    exit_date: str = Field(min_length=1, description="ISO-8601 date, e.g. 2026-05-05")
    reason_exit: str = Field(min_length=1, description="Begründung für den Exit")

    model_config = ConfigDict(extra="forbid")


class JournalTradeResponse(BaseModel):
    id: int
    signal_id: Optional[str] = None
    symbol: str
    strategy: str
    stage: str
    entry_price: Optional[float] = None
    entry_date: Optional[str] = None
    exit_price: Optional[float] = None
    exit_date: Optional[str] = None
    reason_entry: str
    reason_exit: Optional[str] = None
    notes: Optional[str] = None
    timeframe: str
    market_type: str
    data_source: str
    status: Literal["open", "closed"]
    pnl_pct: Optional[float] = None

    model_config = ConfigDict(extra="forbid")

    @classmethod
    def from_payload(cls, payload: dict) -> "JournalTradeResponse":
        entry = payload.get("entry_price")
        exit_ = payload.get("exit_price")
        pnl_pct: Optional[float] = None
        if entry and exit_ and entry > 0:
            pnl_pct = round((exit_ - entry) / entry * 100, 4)

        return cls(
            id=payload["id"],
            signal_id=payload.get("signal_id"),
            symbol=payload["symbol"],
            strategy=payload["strategy"],
            stage=payload["stage"],
            entry_price=entry,
            entry_date=payload.get("entry_date"),
            exit_price=exit_,
            exit_date=payload.get("exit_date"),
            reason_entry=payload["reason_entry"],
            reason_exit=payload.get("reason_exit"),
            notes=payload.get("notes"),
            timeframe=payload["timeframe"],
            market_type=payload["market_type"],
            data_source=payload["data_source"],
            status="closed" if exit_ is not None else "open",
            pnl_pct=pnl_pct,
        )


class JournalTradesListResponse(BaseModel):
    items: list[JournalTradeResponse]
    total: int

    model_config = ConfigDict(extra="forbid")
