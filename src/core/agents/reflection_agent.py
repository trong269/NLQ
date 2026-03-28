"""
src/core/agents/reflection_agent.py
───────────────────────────────────
ReflectionAgent – evaluates whether a generated SQL query correctly
answers the user's natural language request before execution.

This agent:
- Receives the user query, generated SQL, and database schema.
- Calls an LLM with a dedicated reflection prompt.
- Returns a structured JSON assessment.

It does NOT generate or modify SQL – it only evaluates correctness.
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

class ReflectionAgent(BaseAgent):
    """
    Agent responsible for SQL reflection in the NLQ→SQL pipeline.

    Expected inputs
    ---------------
    {
        "user_query": str,
        "generated_sql": str,
        "database_schema": str
    }

    Output
    ------
    Returns the LangGraph state containing the LLM message with JSON
    reflection output.
    """

    async def ainvoke(
        self,
        inputs: dict[str, Any],
        config: dict | None = None,
    ) -> dict[str, Any]:
        """
        Prepare reflection prompt and execute the agent graph.
        """

        # Validate required inputs
        required_keys = {"user_query", "generated_sql", "database_schema"}
        missing = required_keys - inputs.keys()

        if missing:
            raise ValueError(
                f"ReflectionAgent.ainvoke missing required inputs: {sorted(missing)}"
            )

        # Render reflection prompt
        prompt = PromptFactory.render(
            "reflection",
            user_query=inputs["user_query"],
            generated_sql=inputs["generated_sql"],
            database_schema=inputs["database_schema"],
        )

        messages = [
            SystemMessage(
                content="You are an expert SQL auditor. Evaluate whether the SQL correctly answers the user's question."
            ),
            HumanMessage(content=prompt),
        ]

        state: AgentState = {"messages": messages}

        return await self.graph.ainvoke(state, config=config)

    def build_graph(self) -> CompiledGraph:
        """
        Build a simple LLM-only graph for reflection.
        """
        llm = LLMFactory.create(
            provider=self.config.get("llm_provider"),
            model=self.config.get("llm_model"),
            temperature=0.0,
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
                "call_llm": "call_llm",
                "run_tools": END, 
            },
        )

        return graph.compile()