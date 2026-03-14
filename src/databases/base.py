"""
src/databases/base.py
─────────────────────
Abstract base class for all database adapters.

Subclasses must implement ``connect()``, ``disconnect()``, and
``execute()`` and can be used as async context managers.

Example
-------
    from src.databases.base import BaseDatabase

    class MyDatabase(BaseDatabase):
        async def connect(self) -> None:
            self._client = await create_connection(self.config["url"])
            self._connected = True

        async def disconnect(self) -> None:
            await self._client.close()
            self._connected = False

        async def execute(self, query: str, params: dict | None = None):
            return await self._client.run(query, params or {})
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseDatabase(ABC):
    def __init__(self, config: dict) -> None:
        self.config: dict = config
        self._connected: bool = False

    # ------------------------------------------------------------------ #
    # Abstract interface                                                   #
    # ------------------------------------------------------------------ #

    @abstractmethod
    async def connect(self) -> None:
        """Open the database connection / pool."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Close the database connection / pool."""

    @abstractmethod
    async def execute(self, query: str, params: dict | None = None) -> Any:
        """Execute a query and return the result."""

    # ------------------------------------------------------------------ #
    # Context-manager support                                              #
    # ------------------------------------------------------------------ #

    async def __aenter__(self) -> "BaseDatabase":
        await self.connect()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.disconnect()

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    @property
    def is_connected(self) -> bool:
        return self._connected
