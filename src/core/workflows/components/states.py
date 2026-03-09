"""
src/core/workflows/components/states.py
───────────────────────────────────────
TypedDict state definitions for multi-agent workflow graphs.

``WorkflowState`` is passed between orchestration nodes.  The
``next`` field is used by the supervisor to route to the correct
agent; ``final_answer`` is populated when the workflow completes.
"""

from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class WorkflowState(TypedDict):
    """Shared state that flows through a multi-agent workflow graph."""

    # Full conversation history – new messages are *appended*
    messages: Annotated[list[BaseMessage], add_messages]

    # Name of the agent / node to execute next (set by supervisor)
    next: str

    # Populated by the last agent when the workflow is done
    final_answer: str
