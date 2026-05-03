"""
DB-Paket für die Cilly Trading Engine.

Stellt die Funktion `init_db`, den Standardpfad `DEFAULT_DB_PATH`,
sowie die neue `ConnectionFactory` / `DatabaseConfig` Abstraktion bereit.
"""

from .config import ConnectionFactory, DatabaseConfig, load_database_config
from .init_db import init_db, DEFAULT_DB_PATH

__all__ = [
    "ConnectionFactory",
    "DatabaseConfig",
    "DEFAULT_DB_PATH",
    "init_db",
    "load_database_config",
]
