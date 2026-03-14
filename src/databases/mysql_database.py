"""
src/databases/mysql_database.py
──────────────────────────────
MySQL adapter backed by SQLAlchemy engine.

Connection parameters are loaded from environment variables:
- DB_HOST (default: localhost)
- DB_PORT (default: 3306)
- DB_USER (default: root)
- DB_PASSWORD (default: empty)
- DB_NAME (default: northwind)

Legacy fallback variables are still accepted:
- HOST, USER, PASSWORD, DATABASE
"""

from __future__ import annotations

import asyncio
import os
from collections import defaultdict
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.databases.base import BaseDatabase

load_dotenv()


class MySQLDatabase(BaseDatabase):
    """Async-friendly database adapter wrapping a sync SQLAlchemy engine."""

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self._engine: Engine | None = None

    @staticmethod
    def _build_connection_string() -> str:
        # Prefer DB_* names to avoid clashing with app/server PORT.
        host = os.getenv("DB_HOST") or os.getenv("HOST", "localhost")
        port = os.getenv("DB_PORT", "3306")
        user = os.getenv("DB_USER") or os.getenv("USER", "root")
        password = os.getenv("DB_PASSWORD") or os.getenv("PASSWORD", "")
        database = os.getenv("DB_NAME") or os.getenv("DATABASE", "northwind")

        user_enc = quote_plus(user)
        pwd_enc = quote_plus(password)
        db_enc = quote_plus(database)
        return f"mysql+pymysql://{user_enc}:{pwd_enc}@{host}:{port}/{db_enc}"

    async def connect(self) -> None:
        if self._connected:
            return

        def _create() -> Engine:
            return create_engine(
                self._build_connection_string(),
                echo=False,
                pool_pre_ping=True,
            )

        self._engine = await asyncio.to_thread(_create)
        self._connected = True

    async def disconnect(self) -> None:
        if not self._connected or self._engine is None:
            return

        await asyncio.to_thread(self._engine.dispose)
        self._engine = None
        self._connected = False

    async def execute(self, query: str, params: dict | None = None):
        if not self._connected or self._engine is None:
            await self.connect()

        assert self._engine is not None

        def _run():
            with self._engine.connect() as connection:
                result = connection.execute(text(query), params or {})
                if result.returns_rows:
                    return [dict(row._mapping) for row in result.fetchall()]
                connection.commit()
                return {"rowcount": result.rowcount}

        return await asyncio.to_thread(_run)

    async def get_schema_text(self) -> str:
        """Return DB schema as concise text for schema-linking prompt context."""
        rows = await self.execute(
            """
            SELECT
                TABLE_NAME,
                COLUMN_NAME,
                DATA_TYPE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            ORDER BY TABLE_NAME, ORDINAL_POSITION
            """
        )

        grouped: dict[str, list[str]] = defaultdict(list)
        for row in rows:
            grouped[row["TABLE_NAME"]].append(f"{row['COLUMN_NAME']} ({row['DATA_TYPE']})")

        lines = []
        for table, columns in grouped.items():
            lines.append(f"{table}: {', '.join(columns)}")
        return "\n".join(lines)
