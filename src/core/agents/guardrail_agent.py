"""
src/core/agents/guardrail_agent.py
───────────────────────────────────
GuardrailAgent – scans the user's natural language input for security threats
BEFORE any SQL is generated.

This is the first gate in the NL→SQL workflow.  Only `nl_input` is required;
there is no SQL at this stage.

Pipeline
────────
  initialize → scan_nl → END

  scan_nl uses an LLM to detect prompt-injection attempts with
  structured output (HIGH/MEDIUM → HARD_BLOCK, LOW → WARNING).

Usage
─────
    from src.core.agents.factory import AgentFactory

    agent = AgentFactory.create("guardrail")
    result = await agent.ainvoke({"nl_input": "show all orders from last month"})
    # result["verdict"]      → "PASS" | "HARD_BLOCK"
    # result["warnings"]     → list[str]
    # result["block_reason"] → str  (empty when PASS)
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph as CompiledGraph

from src.core.agents.base import BaseAgent
from src.core.agents.components.nodes import (
    node_guardrail_initialize,
    node_guardrail_scan_nl,
)
from src.core.agents.components.states import GuardrailState
from src.core.llm.factory import LLMFactory


class GuardrailAgent(BaseAgent):
    """Prompt-injection guardrail for raw NL input."""

    def build_graph(self) -> CompiledGraph:
        llm = LLMFactory.create(provider=self.config.get("llm_provider", "mega_llm"))

        graph = StateGraph(GuardrailState)

        graph.add_node("initialize", node_guardrail_initialize)
        graph.add_node("scan_nl",    node_guardrail_scan_nl(llm))

        graph.set_entry_point("initialize")
        graph.add_edge("initialize", "scan_nl")
        graph.add_edge("scan_nl", END)

        return graph.compile()
