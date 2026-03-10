"""
src/core/agents/components/nodes.py
───────────────────────────────────
Node functions and routing helpers shared across all agents.

Add guardrail-specific nodes under their own section.
"""

from __future__ import annotations

from collections.abc import Callable

from langchain_core.language_models.chat_models import BaseChatModel

from src.core.agents.components.states import AgentState, GuardrailState


# ═════════════════════════════════════════════════════════════════════════════
# Generic tool-calling agent nodes
# ═════════════════════════════════════════════════════════════════════════════

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


# ═════════════════════════════════════════════════════════════════════════════
# Guardrail agent nodes
# ═════════════════════════════════════════════════════════════════════════════

_PASS = "PASS"
_HARD_BLOCK = "HARD_BLOCK"


async def node_guardrail_initialize(state: GuardrailState) -> dict:
    """Reset all output fields before the guardrail pipeline starts."""
    return {
        "verdict": _PASS,
        "block_reason": "",
        "warnings": [],
        "message": "",
    }


def node_guardrail_scan_nl(llm: BaseChatModel) -> Callable[[GuardrailState], dict]:
    """
    Prompt-injection scan on the natural language input.

    HIGH / MEDIUM confidence  →  HARD_BLOCK
    LOW confidence            →  non-blocking WARNING
    """

    async def _node(state: GuardrailState) -> dict:
        from src.core.tools.prompt_injection import scan_prompt_injection  # noqa: PLC0415

        result = await scan_prompt_injection(state["nl_input"], llm)

        if result.is_injection and result.confidence in ("HIGH", "MEDIUM"):
            block_reason = f"[PromptInjection/{result.confidence}] {result.reason}"
            return {
                "verdict": _HARD_BLOCK,
                "block_reason": block_reason,
                "message": f"Xin lỗi, tôi không có quyền truy cập SQL như yêu cầu của bạn. Lý do: {block_reason}",
            }
        if result.is_injection:   # LOW – warn but do not block
            return {"warnings": [f"[PromptInjection/LOW] {result.reason}"]}
        return {}

    return _node
