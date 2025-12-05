"""
DB-Paket für die Cilly Trading Engine.

Stellt aktuell die Funktion `init_db` und den Standardpfad `DEFAULT_DB_PATH`
zur Initialisierung der SQLite-Datenbank bereit.
"""

from .init_db import init_db, DEFAULT_DB_PATH

__all__ = ["init_db", "DEFAULT_DB_PATH"]
