"""
DB-Paket für die Cilly Trading Engine.

Stellt aktuell nur die Funktion `init_db` zur Initialisierung der SQLite-Datenbank bereit.
"""

from .init_db import init_db

__all__ = ["init_db"]
