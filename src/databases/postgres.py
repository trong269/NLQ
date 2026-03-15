"""PostgreSQL async adapter (asyncpg + SQLAlchemy for schema introspection)."""

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.databases.base import BaseDatabase


class PostgresDatabase(BaseDatabase):
    """Async PostgreSQL using SQLAlchemy 2 async + asyncpg."""

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)

        url = config.get("url", "")
        pool_size = config.get("pool_size", 5)
        max_overflow = config.get("max_overflow", 10)

        self._engine = create_async_engine(
            url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            echo=False,
        )

        self._session_factory = sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    # ─────────────────────────────────────
    # Connection lifecycle
    # ─────────────────────────────────────

    async def connect(self) -> None:
        """Test connection to PostgreSQL."""
        async with self._engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        self._connected = True

    async def disconnect(self) -> None:
        """Dispose connection pool."""
        await self._engine.dispose()
        self._connected = False

    # ─────────────────────────────────────
    # Schema introspection
    # ─────────────────────────────────────

    async def get_schema(self) -> str:
        """Return schema description for LLM (tables + columns)."""

        async with self._session_factory() as session:
            q = text("""
                SELECT
                    table_name,
                    column_name,
                    data_type,
                    is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public'
                ORDER BY table_name, ordinal_position
            """)

            result = await session.execute(q)
            rows = result.mappings().all()

        if not rows:
            return "No tables found in public schema."

        lines = ["Schema (public):"]

        current_table = None

        for r in rows:
            table = r["table_name"]
            column = r["column_name"]
            dtype = r["data_type"]
            nullable = r["is_nullable"]

            if table != current_table:
                lines.append(f"\nTable: {table}")
                current_table = table

            null_text = "NULL" if nullable == "YES" else "NOT NULL"

            lines.append(f"  - {column} ({dtype}) {null_text}")

        return "\n".join(lines)

    async def get_schema_text(self) -> str:
        """
        Compatibility wrapper for agents expecting get_schema_text().
        """
        return await self.get_schema()

    # ─────────────────────────────────────
    # Query execution
    # ─────────────────────────────────────

    async def execute(
        self,
        query: str,
        params: dict[str, Any] | None = None,
        read_only: bool = True,
    ) -> list[dict[str, Any]]:

        if read_only:
            forbidden = {
                "INSERT",
                "UPDATE",
                "DELETE",
                "DROP",
                "CREATE",
                "ALTER",
                "TRUNCATE",
            }

            upper_query = query.upper()

            if any(word in upper_query for word in forbidden):
                raise ValueError(
                    "Write operations are not allowed when read_only=True"
                )

        async with self._session_factory() as session:
            result = await session.execute(text(query), params or {})

            rows = result.mappings().all()

        return [dict(r) for r in rows]