"""
Repository-Interfaces für die Cilly Trading Engine.

Engine und API verwenden diese Interfaces, um mit der Persistenzschicht zu arbeiten.
Die konkrete Implementierung im MVP nutzt SQLite.
"""

from __future__ import annotations

from typing import Protocol, List

from cilly_trading.models import Signal, Trade


class SignalRepository(Protocol):
    """
    Abstraktes Interface für das Speichern und Laden von Signals.
    """

    def save_signals(self, signals: List[Signal]) -> None:
        """
        Speichert eine Liste von Signals (z. B. aus einem Analyse-Run).
        """
        ...

    def list_signals(self, limit: int = 100) -> List[Signal]:
        """
        Liefert die letzten `limit` Signals, absteigend nach id.

        (Für MVP: einfache Variante ohne komplexe Filter.)
        """
        ...


class TradeRepository(Protocol):
    """
    Abstraktes Interface für das Speichern und Laden von Trades.
    """

    def save_trade(self, trade: Trade) -> int:
        """
        Speichert einen Trade und gibt die neue Trade-ID zurück.
        """
        ...

    def list_trades(self, limit: int = 100) -> List[Trade]:
        """
        Liefert die letzten `limit` Trades, absteigend nach id.
        """
        ...


__all__ = ["SignalRepository", "TradeRepository"]
