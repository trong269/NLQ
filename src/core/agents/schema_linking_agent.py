"""
src/core/agents/schema_linking_agent.py
───────────────────────────────────────
SchemaLinkingAgent – maps a natural language question to the
relevant database tables and columns (schema linking) for NLQ→SQL.

This agent:
- Receives a user question and database schema description.
- Calls an LLM with a dedicated prompt to select only the
  relevant tables/columns.
- Returns the result as a final LLM message containing structured JSON.

It does NOT generate SQL – only schema elements and reasoning that
downstream agents (e.g. SQL generation) can consume.
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph as CompiledGraph

from src.core.agents.base import BaseAgent
from src.core.agents.components.nodes import node_call_llm, route_after_llm
from src.core.agents.components.states import AgentState
from src.core.llm.factory import LLMFactory
from src.core.prompts.factory import PromptFactory
from src.core.tools.factory import ToolFactory


class SchemaLinkingAgent(BaseAgent):
    """
    Agent responsible for schema linking in the NLQ→SQL pipeline.

    Inputs
    ------
    Preferred invocation:
        {
            "user_query": "Which customers placed orders in 2024?",
            "database_schema": "<serialized schema>",
        }

    Backwards-compatible invocation (via generic workflows):
        {
            "messages": [...],
        }

    The internal LangGraph state uses ``AgentState`` with a single
    ``messages`` field, consistent with other tool-calling agents.
    """

    async def ainvoke(self, inputs: dict, config: dict | None = None) -> dict[str, Any]:  # type: ignore[override]
        """
        Support two input shapes:

        1) ``{"messages": [...]}`` – pass-through for generic callers.
        2) ``{"user_query": str, "database_schema": str}`` – construct the
           system+human messages from the dedicated schema-linking prompt.
        """
        if "messages" in inputs:
            state: AgentState = {"messages": inputs["messages"]}
        elif {"user_query", "database_schema"} <= inputs.keys():
            prompt = PromptFactory.render(
                "schema_linking",
                user_query=inputs["user_query"],
                database_schema=inputs["database_schema"],
            )
            messages = [
                SystemMessage(content=prompt),
                HumanMessage(content=inputs["user_query"]),
            ]
            state = {"messages": messages}
        else:
            raise ValueError(
                "SchemaLinkingAgent.ainvoke expects either "
                "inputs['messages'] or both 'user_query' and 'database_schema'."
            )

        return await self.graph.ainvoke(state, config=config)  # type: ignore[return-value]

    def build_graph(self) -> CompiledGraph:
        """
        Build a simple LLM-only graph using ``AgentState``.

        The schema-linking task normally does not require tools, but the
        agent still honours the ``tools`` config to stay consistent with
        the generic agent template.
        """
        llm = LLMFactory.create(
            provider=self.config.get("llm_provider"),
            model=self.config.get("llm_model"),
        )
        tools = ToolFactory.get_tools(self.config.get("tools", []))
        llm_with_tools = llm.bind_tools(tools) if tools else llm

        graph = StateGraph(AgentState)

        graph.add_node("call_llm", node_call_llm(llm_with_tools))

        graph.set_entry_point("call_llm")
        graph.add_conditional_edges(
            "call_llm",
            route_after_llm,
            {
                "__end__": END,
            },
        )

        return graph.compile()

