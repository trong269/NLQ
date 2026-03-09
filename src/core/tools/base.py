"""
src/core/tools/base.py
──────────────────────
Abstract base class for all project tools.

Every custom tool must:
  1. Inherit from ``ProjectBaseTool``.
  2. Define ``name`` and ``description`` as class attributes.
  3. Implement ``_arun()`` (async) – ``_run()`` should raise ``NotImplementedError``.
  4. Register an instance in ``src/core/tools/factory.TOOL_REGISTRY``.

Example
-------
    from src.core.tools.base import ProjectBaseTool

    class MyTool(ProjectBaseTool):
        name: str = "my_tool"
        description: str = "Does something useful for the LLM."

        async def _arun(self, query: str) -> str:
            return f"Result for: {query}"

        def _run(self, query: str) -> str:
            raise NotImplementedError("Use _arun instead.")
"""

from __future__ import annotations

from abc import abstractmethod

from langchain_core.tools import BaseTool


class ProjectBaseTool(BaseTool):
    """Thin wrapper around LangChain's ``BaseTool`` that enforces async-first usage."""

    @abstractmethod
    async def _arun(self, *args, **kwargs) -> str:  # type: ignore[override]
        """Async execution – implement this in every subclass."""

    def _run(self, *args, **kwargs) -> str:  # type: ignore[override]
        raise NotImplementedError(
            f"Tool '{self.name}' only supports async execution via _arun()."
        )
