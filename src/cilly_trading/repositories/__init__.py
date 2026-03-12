"""
Repository-Interfaces fuer die Cilly Trading Engine.

Engine und API verwenden diese Interfaces, um mit der Persistenzschicht zu arbeiten.
Die konkrete Implementierung im MVP nutzt SQLite.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Protocol

from cilly_trading.models import Signal, Trade


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
    Abstraktes Interface fuer das Speichern und Laden von Trades.
    """

    def save_trade(self, trade: Trade) -> int:
        """
        Speichert einen Trade und gibt die neue Trade-ID zurueck.
        """
        ...

    def list_trades(self, limit: int = 100) -> List[Trade]:
        """
        Liefert die letzten `limit` Trades, absteigend nach id.
        """
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
    "Watchlist",
    "WatchlistRepository",
]
