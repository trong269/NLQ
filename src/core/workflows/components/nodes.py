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

import json
from collections.abc import Callable

from langchain_core.runnables import RunnableConfig

from src.core.workflows.components.states import NlqState, WorkflowState


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


# ═════════════════════════════════════════════════════════════════════════════
# NLQ pipeline workflow nodes
# ═════════════════════════════════════════════════════════════════════════════

async def node_nlq_initialize(state: NlqState) -> dict:
    """Reset all output fields before the NLQ pipeline starts."""
    return {
        "guardrail_verdict": "",
        "guardrail_block_reason": "",
        "guardrail_warnings": [],
        "guardrail_message": "",
        "schema_linking_raw": "",
        "schema_linking": None,
        "sql_query": "",
        "sql_status": "",
        "sql_result": [],
        "sql_error_message": "",
        "reflection_raw": "",
        "reflection": None,
        "reflection_retry_count": 0,
    }


async def node_nlq_run_guardrail(state: NlqState) -> dict:
    """Run the Guardrail agent and store its verdict in workflow state."""
    from src.core.agents.factory import AgentFactory  # noqa: PLC0415

    agent = AgentFactory.create("guardrail")
    result = await agent.ainvoke({"nl_input": state["nl_input"]})
    return {
        "guardrail_verdict": result.get("verdict", "PASS"),
        "guardrail_block_reason": result.get("block_reason", ""),
        "guardrail_warnings": result.get("warnings", []),
        "guardrail_message": result.get("message", ""),
    }


async def node_nlq_run_schema_linking(state: NlqState, config: RunnableConfig) -> dict:
    from src.core.agents.factory import AgentFactory
    from langchain_core.messages import AIMessage
    import json

    db = (config.get("configurable") or {}).get("db")
    if db is None:
        return {
            "database_schema": "",
            "schema_linking_raw": "",
            "schema_linking": None,
        }

    database_schema = await db.get_schema_text()

    agent = AgentFactory.create("schema_linking_agent")

    result = await agent.ainvoke(
        {
            "user_query": state["nl_input"],
            "database_schema": database_schema,
        }
    )

    messages = result.get("messages", [])

    raw = ""

    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            raw = msg.content
            break

    try:
        parsed = json.loads(raw) if raw else None
    except json.JSONDecodeError:
        parsed = None
    print("RAW:", raw)
    print("PARSED:", parsed)
    return {
        "database_schema": database_schema,
        "schema_linking_raw": raw,
        "schema_linking": parsed,
    }


async def node_nlq_run_sql_gen(state: NlqState, config: RunnableConfig) -> dict:
    """
    Run SqlGenAgent with the schema context; pass ``db`` through configurable
    so the agent can execute and auto-retry SQL.
    """
    from src.core.agents.sql_gen_agent import SqlGenAgent  # noqa: PLC0415
    from src.utils import load_config  # noqa: PLC0415

    sql_gen_cfg = load_config().get("agents", {}).get("sql_gen_agent", {})
    agent = SqlGenAgent(config=sql_gen_cfg)
    
    inputs = {
        "nl_input": state["nl_input"],
        "schema_context": state.get("schema_linking_raw", ""),
    }
    
    if state.get("reflection_raw"):
        inputs["sql_error"] = state.get("reflection_raw", "")
        inputs["sql_query"] = state.get("sql_query", "")

    result = await agent.ainvoke(
        inputs,
        config=config,  # db flows through configurable
    )
    return {
        "sql_query": result.get("sql_query", ""),
        "sql_status": result.get("status", ""),
        "sql_result": result.get("result", []),
        "sql_error_message": result.get("error_message", ""),
    }


def route_nlq_after_guardrail(state: NlqState) -> str:
    """
    Conditional edge: skip the rest of the pipeline when guardrail blocks.
    """
    return "schema_linking" if state.get("guardrail_verdict") != "HARD_BLOCK" else "__end__"


async def node_nlq_run_reflection(state: NlqState, config: RunnableConfig) -> dict:
    """
    Run ReflectionAgent to verify generated SQL correctness.
    """
    from src.core.agents.factory import AgentFactory
    import json

    sql_query = state.get("sql_query", "")
    if not sql_query:
        return {
            "reflection_raw": "",
            "reflection": None,
            "reflection_retry": False,
        }

    agent = AgentFactory.create("reflection_agent")

    result = await agent.ainvoke(
        {
            "user_query": state["nl_input"],
            "generated_sql": sql_query,
            "database_schema": state.get("database_schema", ""),
            "query_result": state.get("sql_result", [])[:5],
        }
    )

    messages = result.get("messages", [])
    raw = ""

    if messages:
        content = getattr(messages[-1], "content", "")
        raw = content if isinstance(content, str) else str(content)

    try:
        parsed = json.loads(raw) if raw else None
    except json.JSONDecodeError:
        parsed = None

    retry_count = state.get("reflection_retry_count", 0)

    is_correct = bool(parsed and parsed.get("is_correct", False))

    if not is_correct:
        return {
            "reflection_raw": raw,
            "reflection": parsed,
            "reflection_retry_count": retry_count + 1,

            # reset SQL state so it can re-execute cleanly next round
            "sql_result": [],
            "sql_status": "",
            "sql_error_message": "",
        }

    return {
        "reflection_raw": raw,
        "reflection": parsed,
        "reflection_retry_count": retry_count,
    }

MAX_REFLECTION_RETRY = 2

def route_nlq_after_reflection(state: NlqState) -> str:

    reflection = state.get("reflection")
    retry_count = state.get("reflection_retry_count", 0)

    if not isinstance(reflection, dict):
        return "__end__"

    if reflection.get("is_correct"):
        return "__end__"

    if retry_count >= MAX_REFLECTION_RETRY:
        return "__end__"

    return "retry"