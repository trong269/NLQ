"""
src/core/agents/components/nodes.py
───────────────────────────────────
Reusable node functions and routing helpers for agent graphs.

Every public function is a **factory** that returns the actual
async node callable – this allows injecting dependencies (e.g. the
bound LLM) without relying on global state.

Usage inside an agent
---------------------
    from langgraph.prebuilt import ToolNode
    from src.core.agents.components.nodes import node_call_llm, route_after_llm

    graph.add_node("call_llm", node_call_llm(llm_with_tools))
    graph.add_node("run_tools", ToolNode(tools))
    graph.add_conditional_edges("call_llm", route_after_llm, {
        "run_tools": "run_tools",
        "__end__": END,
    })
"""

from __future__ import annotations

from collections.abc import Callable

from langchain_core.language_models.chat_models import BaseChatModel

from src.core.agents.components.states import AgentState


def node_call_llm(llm_with_tools: BaseChatModel) -> Callable[[AgentState], dict]:
    """
    Return an async node that invokes *llm_with_tools* with the current
    message history and appends the response.
    """

    async def _node(state: AgentState) -> dict:
        response = await llm_with_tools.ainvoke(state["messages"])
        return {"messages": [response]}

    return _node


def route_after_llm(state: AgentState) -> str:
    """
    Conditional edge: if the last message has tool calls, route to
    ``"run_tools"``; otherwise end the graph.
    """
    last_message = state["messages"][-1]
    if getattr(last_message, "tool_calls", None):
        return "run_tools"
    return "__end__"
