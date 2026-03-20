"""
Repository-Interfaces fuer die Cilly Trading Engine.

Engine und API verwenden diese Interfaces, um mit der Persistenzschicht zu arbeiten.
Die konkrete Implementierung im MVP nutzt SQLite.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Protocol

from cilly_trading.models import ExecutionEvent, Order, PersistedTradePayload, Signal, Trade


class SignalRepository(Protocol):
    """
    Abstraktes Interface fuer das Speichern und Laden von Signals.
    """

    def save_signals(self, signals: List[Signal]) -> None:
        """
        Speichert eine Liste von Signals (z. B. aus einem Analyse-Run).
        """
        ...

    def list_signals(self, limit: int = 100) -> List[Signal]:
        """
        Liefert die letzten `limit` Signals, absteigend nach id.

        (Fuer MVP: einfache Variante ohne komplexe Filter.)
        """
        ...


class TradeRepository(Protocol):
    """
    Legacy-Interface fuer das Speichern und Laden von Paper-Trading-Trade-Payloads.
    """

    def save_trade(self, trade: PersistedTradePayload) -> int:
        """
        Speichert einen Trade und gibt die neue Trade-ID zurueck.
        """
        ...

    def list_trades(self, limit: int = 100) -> List[PersistedTradePayload]:
        """
        Liefert die letzten `limit` Trades, absteigend nach id.
        """
        ...


class CanonicalExecutionRepository(Protocol):
    """Persistence boundary for canonical Order/ExecutionEvent/Trade entities."""

    def save_order(self, order: Order) -> None:
        """Persist or replace a canonical order by identity."""
        ...

    def get_order(self, order_id: str) -> Optional[Order]:
        """Load a canonical order by ID."""
        ...

    def list_orders(
        self,
        *,
        strategy_id: Optional[str] = None,
        symbol: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Order]:
        """List canonical orders in deterministic order."""
        ...

    def save_execution_events(self, events: List[ExecutionEvent]) -> None:
        """Append immutable canonical execution events."""
        ...

    def list_execution_events(
        self,
        *,
        strategy_id: Optional[str] = None,
        symbol: Optional[str] = None,
        order_id: Optional[str] = None,
        trade_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ExecutionEvent]:
        """List canonical execution events in deterministic replay order."""
        ...

    def save_trade(self, trade: Trade) -> None:
        """Persist or replace a canonical derived trade by identity."""
        ...

    def get_trade(self, trade_id: str) -> Optional[Trade]:
        """Load a canonical trade by ID."""
        ...

    def list_trades(
        self,
        *,
        strategy_id: Optional[str] = None,
        symbol: Optional[str] = None,
        position_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Trade]:
        """List canonical trades in deterministic order."""
        ...


@dataclass(frozen=True)
class Watchlist:
    """Deterministic watchlist payload for repository persistence."""

    watchlist_id: str
    name: str
    symbols: tuple[str, ...]


class WatchlistRepository(Protocol):
    """Abstract persistence boundary for named watchlists."""

    def create_watchlist(self, *, watchlist_id: str, name: str, symbols: List[str]) -> Watchlist:
        """Persist a new watchlist."""
        ...

    def get_watchlist(self, watchlist_id: str) -> Optional[Watchlist]:
        """Load a watchlist by ID."""
        ...

    def list_watchlists(self) -> List[Watchlist]:
        """List all watchlists in deterministic order."""
        ...

    def update_watchlist(self, *, watchlist_id: str, name: str, symbols: List[str]) -> Watchlist:
        """Replace the stored name and ordered symbol membership for a watchlist."""
        ...

    def delete_watchlist(self, watchlist_id: str) -> bool:
        """Delete a watchlist and its symbol membership."""
        ...


__all__ = [
    "SignalRepository",
    "TradeRepository",
    "CanonicalExecutionRepository",
    "Watchlist",
    "WatchlistRepository",
]
