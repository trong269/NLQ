"""
src/core/agents/components/states.py
────────────────────────────────────
TypedDict state definitions for individual agent graphs.

AgentState is passed between every node in the graph.  LangGraph
merges list fields using the reducer function (``add_messages``
appends new messages instead of overwriting).
"""

from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """Shared state that flows through an agent's LangGraph."""

    # Conversation history – new messages are *appended* (not replaced)
    messages: Annotated[list[BaseMessage], add_messages]
