"""
src/core/agents/guardrail_agent.py
───────────────────────────────────
This is the first gate in the NL→SQL workflow.  Only `nl_input` is required;
there is no SQL at this stage.
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
        llm = LLMFactory.create(provider=self.config.get("llm_provider"))

        graph = StateGraph(GuardrailState)

        graph.add_node("initialize", node_guardrail_initialize)
        graph.add_node("scan_nl",    node_guardrail_scan_nl(llm))

        graph.set_entry_point("initialize")
        graph.add_edge("initialize", "scan_nl")
        graph.add_edge("scan_nl", END)

        return graph.compile()
