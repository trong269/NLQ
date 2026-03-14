"""
src/core/agents/base.py
───────────────────────
Abstract base class for all agents.

Subclasses must implement ``build_graph()`` which returns a compiled
LangGraph.  The base class handles lazy compilation and provides
``ainvoke()`` / ``stream()`` shortcuts.

Example
-------
    from src.core.agents.base import BaseAgent

    class MyAgent(BaseAgent):
        def build_graph(self) -> CompiledGraph:
            ...
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from langgraph.graph.state import CompiledStateGraph as CompiledGraph


class BaseAgent(ABC):
    def __init__(self, config: dict) -> None:
        self.config: dict = config
        self._graph: CompiledGraph | None = None

    # ------------------------------------------------------------------ #
    # Abstract interface                                                   #
    # ------------------------------------------------------------------ #

    @abstractmethod
    def build_graph(self) -> CompiledGraph:
        """
        Build and compile the LangGraph for this agent.

        Called once on first access; result is cached in ``self._graph``.
        """

    # ------------------------------------------------------------------ #
    # Public helpers                                                       #
    # ------------------------------------------------------------------ #

    @property
    def graph(self) -> CompiledGraph:
        """Lazily compile and cache the graph."""
        if self._graph is None:
            self._graph = self.build_graph()
        return self._graph

    async def ainvoke(self, inputs: dict, config: dict | None = None) -> dict[str, Any]:
        """Run the agent asynchronously and return the final state."""
        return await self.graph.ainvoke(inputs, config=config)  # type: ignore[return-value]

    async def astream(self, inputs: dict, config: dict | None = None):
        """Stream state updates from the agent graph."""
        async for chunk in self.graph.astream(inputs, config=config):
            yield chunk
