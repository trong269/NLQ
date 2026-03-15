"""
src/databases/factory.py
────────────────────────
Central registry and factory for database adapters.

To add a new database adapter
------------------------------
    1. Create ``src/databases/my_database.py`` subclassing ``BaseDatabase``.
    2. Import and register the class below:

        from src.databases.my_database import MyDatabase

        DATABASE_REGISTRY = {
            "my_db": MyDatabase,   # ← add here
        }

    3. Add config to ``config/app.yaml`` (url goes in ``.env``):

        databases:
          my_db:
            pool_size: 5

Usage
-----
    from src.databases.factory import DatabaseFactory

    async with DatabaseFactory.create("my_db") as db:
        rows = await db.execute("SELECT 1")
"""

from __future__ import annotations

from src.databases.base import BaseDatabase
from src.databases.mysql_database import MySQLDatabase
from src.databases.postgres import PostgresDatabase
from src.utils import load_config

# ─────────────────────────────────────────────────────────────────────────────
# Registry – map database type  →  adapter class
# ─────────────────────────────────────────────────────────────────────────────
DATABASE_REGISTRY: dict[str, type[BaseDatabase]] = {
    "mysql": MySQLDatabase,
    "postgres": PostgresDatabase,
}


class DatabaseFactory:
    @staticmethod
    def create(db_type: str, config: dict | None = None) -> BaseDatabase:
        """
        Instantiate and return the database adapter registered under *db_type*.

        Raises
        ------
        ValueError  – when *db_type* is not in ``DATABASE_REGISTRY``.
        """
        if db_type not in DATABASE_REGISTRY:
            raise ValueError(
                f"Database '{db_type}' not found in DATABASE_REGISTRY. "
                f"Available databases: {list(DATABASE_REGISTRY)}"
            )
        db_config = config or load_config().get("databases", {}).get(db_type, {})
        return DATABASE_REGISTRY[db_type](config=db_config)

    @staticmethod
    def list_databases() -> list[str]:
        """Return the names of all registered database adapters."""
        return list(DATABASE_REGISTRY)
