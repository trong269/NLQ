"""
src/core/agents/sql_gen_agent.py
────────────────────────────────
SqlGenAgent – generates a SQL query from a natural language input and a
schema context produced by SchemaLinkingAgent.

This is the third gate in the NL→SQL workflow:
  Guardrail → Schema Linking → SQL Generation

Pipeline
────────
  initialize → generate → execute ┐
                ↑── (retry) ───────┘
                          └── success → END
                          └── failed  → END  (after _MAX_RETRIES attempts)

"""

from __future__ import annotations

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph as CompiledGraph

from src.core.agents.base import BaseAgent
from src.core.agents.components.nodes import (
    node_sql_gen_execute,
    node_sql_gen_generate,
    node_sql_gen_initialize,
    route_sql_gen_after_execute,
)
from src.core.agents.components.states import SqlGenState
from src.core.llm.factory import LLMFactory


class SqlGenAgent(BaseAgent):
    """SQL generation agent with automatic error-driven retry loop."""

    def build_graph(self) -> CompiledGraph:
        llm = LLMFactory.create(provider=self.config.get("llm_provider"))

        graph = StateGraph(SqlGenState)

        graph.add_node("initialize", node_sql_gen_initialize)
        graph.add_node("generate",   node_sql_gen_generate(llm))
        graph.add_node("execute",    node_sql_gen_execute)

        graph.set_entry_point("initialize")
        graph.add_edge("initialize", "generate")
        graph.add_edge("generate",   "execute")
        graph.add_conditional_edges(
            "execute",
            route_sql_gen_after_execute,
            {
                "retry":   "generate",   # loop back for self-correction
                "success": END,
                "failed":  END,
            },
        )

        return graph.compile()
