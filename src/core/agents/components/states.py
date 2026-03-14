"""
src/core/agents/components/states.py
────────────────────────────────────
TypedDict state definitions shared across agents.

Add a new State class here whenever a new agent with a distinct
state shape is introduced.
"""

from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


# ── Generic agent state ───────────────────────────────────────────────────────

class AgentState(TypedDict):
    """Shared state for tool-calling agents."""

    # Conversation history – new messages are *appended* (not replaced)
    messages: Annotated[list[BaseMessage], add_messages]


# ── Guardrail agent state ─────────────────────────────────────────────────────

def _append_warnings(left: list | None, right: list | None) -> list:
    """Reducer: append new warnings without failing when list is not yet set."""
    return (left or []) + (right or [])


class GuardrailState(TypedDict):
    """State for the Guardrail agent – scans the NL input only."""

    # Input
    nl_input: str          # raw natural language query from the user

    # Outputs
    verdict: str           # PASS | HARD_BLOCK
    block_reason: str      # technical reason (set on HARD_BLOCK)
    warnings: Annotated[list[str], _append_warnings]  # non-blocking diagnostics
    message: str           # human-readable response returned to the caller


# ── SQL Generation agent state ────────────────────────────────────────────────

class SqlGenState(TypedDict):
    """State for the SQL Generation agent."""

    # Inputs
    nl_input: str        # original natural language query
    schema_context: str  # schema linking output (JSON string from SchemaLinkingAgent)

    # Processing
    sql_query: str       # most recently generated SQL
    sql_error: str       # execution error message (empty when none)
    retry_count: int     # number of retries attempted so far

    # Outputs
    status: str          # "running" | "success" | "failed"
    result: list         # rows returned from the DB (empty on failure)
    error_message: str   # human-readable message when status == "failed"
