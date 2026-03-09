"""
src/core/workflows/components/nodes.py
───────────────────────────────────
Reusable node functions for multi-agent workflow orchestration.

All public symbols are **factories** that return async callables so
that dependencies can be injected cleanly.

Usage inside a workflow
-----------------------
    from src.core.workflows.components.nodes import (
        node_initialize,
        node_run_agent,
        route_by_next,
    )

    graph.add_node("initialize",  node_initialize)
    graph.add_node("researcher",  node_run_agent("researcher"))
    graph.add_conditional_edges("supervisor", route_by_next, {
        "researcher": "researcher",
        "FINISH":     END,
    })
"""

from __future__ import annotations

from collections.abc import Callable

from src.core.workflows.components.states import WorkflowState


def node_initialize(state: WorkflowState) -> dict:
    """
    Entry node: reset routing fields before the workflow starts.
    Called once at the start of every workflow invocation.
    """
    return {"next": "", "final_answer": ""}


def node_run_agent(agent_name: str) -> Callable[[WorkflowState], dict]:
    """
    Return an async node that creates *agent_name* via ``AgentFactory``
    and runs it against the current message history.

    The agent's last message is appended to ``state["messages"]``.
    """

    async def _node(state: WorkflowState) -> dict:
        # Lazy import prevents circular dependencies at module load time
        from src.core.agents.factory import AgentFactory  # noqa: PLC0415

        agent = AgentFactory.create(agent_name)
        result = await agent.ainvoke({"messages": state["messages"]})
        agent_messages = result.get("messages", [])
        return {"messages": agent_messages[-1:] if agent_messages else []}

    return _node


def route_by_next(state: WorkflowState) -> str:
    """
    Conditional edge: read ``state["next"]`` and return the target node name.
    Return ``"FINISH"`` when the workflow is complete.
    """
    return state.get("next") or "FINISH"
