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


# ── NLQ pipeline workflow state ───────────────────────────────────────────────

class NlqState(TypedDict):
    """State flowing through the full NLQ pipeline: guardrail → schema linking → SQL gen."""

    # Input
    nl_input: str

    # Guardrail outputs
    guardrail_verdict: str           # PASS | HARD_BLOCK
    guardrail_block_reason: str
    guardrail_warnings: list[str]
    guardrail_message: str

    # Schema linking outputs
    schema_linking_raw: str          # raw JSON string from LLM
    schema_linking: dict | None      # parsed JSON (None if unparseable)
    database_schema: str  
    # SQL generation outputs
    sql_query: str
    sql_status: str                  # success | failed
    sql_result: list
    sql_error_message: str

    # Reflection outputs
    reflection_raw: str             
    reflection: dict | None
    reflection_retry_count: int