"""
src/databases/factory.py
────────────────────────
Central registry and factory for database adapters.
"""

from __future__ import annotations

import os

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


def _resolve_env_vars(config: dict) -> dict:
    """
    Replace values like ${ENV_VAR} with actual environment variable values.
    """
    resolved = {}

    for key, value in config.items():
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            env_var = value[2:-1]
            resolved[key] = os.getenv(env_var)
        else:
            resolved[key] = value

    return resolved


class DatabaseFactory:
    @staticmethod
    def create(db_type: str, config: dict | None = None) -> BaseDatabase:
        """
        Instantiate and return the database adapter registered under *db_type*.

        Raises
        ------
        ValueError – when *db_type* is not in DATABASE_REGISTRY.
        """

        if db_type not in DATABASE_REGISTRY:
            raise ValueError(
                f"Database '{db_type}' not found in DATABASE_REGISTRY. "
                f"Available databases: {list(DATABASE_REGISTRY)}"
            )

        # Load config from app.yaml if not provided
        db_config = config or load_config().get("databases", {}).get(db_type, {})

        # Resolve ${ENV_VAR}
        db_config = _resolve_env_vars(db_config)

        return DATABASE_REGISTRY[db_type](config=db_config)

    @staticmethod
    def list_databases() -> list[str]:
        """Return the names of all registered database adapters."""
        return list(DATABASE_REGISTRY)
