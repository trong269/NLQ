"""
src/core/workflows/nlq_workflow.py
───────────────────────────────────
NlqWorkflow – orchestrates the full Natural Language → SQL pipeline.

Pipeline
────────
  initialize → guardrail ──(HARD_BLOCK)──► END
                          └──(PASS)──► schema_linking → sql_gen → END

Agents
------
  guardrail           – scans NL input for prompt injection
  schema_linking      – maps NL question to relevant DB tables/columns
  sql_gen             – generates SQL, executes it, and auto-retries on error

Database injection
------------------
  The DB connection opened at startup is threaded through every node via
  LangGraph's configurable mechanism.  The caller must pass it like:

      await workflow.ainvoke(
          {"nl_input": "..."},
          config={"configurable": {"db": db}},
      )

Usage
─────
    from src.core.workflows.factory import WorkflowFactory

    workflow = WorkflowFactory.create("nlq")
    state = await workflow.ainvoke(
        {"nl_input": "Top 5 customers by revenue"},
        config={"configurable": {"db": app.state.db}},
    )
    # state["guardrail_verdict"]    → "PASS" | "HARD_BLOCK"
    # state["schema_linking"]       → dict | None
    # state["sql_query"]            → str
    # state["sql_status"]           → "success" | "failed"
    # state["sql_result"]           → list[dict]
    # state["sql_error_message"]    → str
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph as CompiledGraph

from src.core.workflows.base import BaseWorkflow
from src.core.workflows.components.nodes import (
    node_nlq_initialize,
    node_nlq_run_guardrail,
    node_nlq_run_schema_linking,
    node_nlq_run_sql_gen,
    node_nlq_run_reflection,
    route_nlq_after_guardrail,
    route_nlq_after_reflection
)
from src.core.workflows.components.states import NlqState


class NlqWorkflow(BaseWorkflow):
    """Full NLQ-to-SQL pipeline workflow."""

    def build_graph(self) -> CompiledGraph:
        graph = StateGraph(NlqState)

        graph.add_node("initialize",      node_nlq_initialize)
        graph.add_node("guardrail",       node_nlq_run_guardrail)
        graph.add_node("schema_linking",  node_nlq_run_schema_linking)
        graph.add_node("sql_gen",         node_nlq_run_sql_gen)
        graph.add_node("reflection",      node_nlq_run_reflection)

        graph.set_entry_point("initialize")
        graph.add_edge("initialize", "guardrail")
        graph.add_conditional_edges(
            "guardrail",
            route_nlq_after_guardrail,
            {
                "schema_linking": "schema_linking",
                "__end__": END,
            },
        )
        graph.add_edge("schema_linking", "sql_gen")
        graph.add_edge("sql_gen", "reflection")
        graph.add_conditional_edges(
            "reflection",
            route_nlq_after_reflection,
            {
                "retry": "sql_gen",
                "__end__": END,
            },
        )

        return graph.compile()
