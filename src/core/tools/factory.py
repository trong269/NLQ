"""
src/core/tools/factory.py
─────────────────────────
Central registry and factory for LangChain tools.

To add a new tool
-----------------
    1. Create ``src/core/tools/my_tool.py`` that subclasses ``ProjectBaseTool``.
    2. Import and register an instance below:

        from src.core.tools.my_tool import MyTool

        TOOL_REGISTRY: dict[str, BaseTool] = {
            "my_tool": MyTool(),   # ← add here
        }

Usage
-----
    from src.core.tools.factory import ToolFactory

    all_tools  = ToolFactory.get_tools()                  # every registered tool
    some_tools = ToolFactory.get_tools(["web_search"])    # specific subset
"""

from __future__ import annotations

from langchain_core.tools import BaseTool

from src.core.tools.base import ProjectBaseTool  # noqa: F401 – keeps base importable

# ─────────────────────────────────────────────────────────────────────────────
# Registry – add new tool instances here
# ─────────────────────────────────────────────────────────────────────────────
TOOL_REGISTRY: dict[str, BaseTool] = {}


class ToolFactory:
    @staticmethod
    def get_tools(names: list[str] | None = None) -> list[BaseTool]:
        """
        Return tool instances from the registry.

        Parameters
        ----------
        names:
            List of tool names to retrieve.  Pass ``None`` (default) to get
            every registered tool.

        Raises
        ------
        KeyError  – when a requested tool name is not in the registry.
        """
        if names is None:
            return list(TOOL_REGISTRY.values())

        tools: list[BaseTool] = []
        for name in names:
            if name not in TOOL_REGISTRY:
                raise KeyError(
                    f"Tool '{name}' not found in TOOL_REGISTRY. "
                    f"Available tools: {list(TOOL_REGISTRY)}"
                )
            tools.append(TOOL_REGISTRY[name])
        return tools

    @staticmethod
    def list_tools() -> list[str]:
        """Return the names of all registered tools."""
        return list(TOOL_REGISTRY)
