"""
src/core/agents/components/nodes.py
───────────────────────────────────
Node functions and routing helpers shared across all agents.

Add guardrail-specific nodes under their own section.
"""

from __future__ import annotations

from collections.abc import Callable

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables import RunnableConfig

from src.core.agents.components.states import AgentState, GuardrailState, SqlGenState


# ═════════════════════════════════════════════════════════════════════════════
# Generic tool-calling agent nodes
# ═════════════════════════════════════════════════════════════════════════════

def _get_max_retries_llm() -> int:
    from src.utils import load_config
    return load_config().get("agents", {}).get("llm_agent", {}).get("max_retries", 2)

def node_call_llm(llm_with_tools: BaseChatModel) -> Callable[[AgentState], dict]:
    async def _node(state: AgentState) -> dict:
        max_retries = _get_max_retries_llm()
        retry_count = state.get("retry_count", 0)
        if retry_count >= max_retries:
            return {
                "status": "failed",
                "error_message": f"Đã vượt quá số lần thử ({max_retries})"
            }
        try:
            response = await llm_with_tools.ainvoke(state["messages"])
            return {"messages": [response], "retry_count": 0, "status": "running"}
        except Exception as exc:
            return {
                "retry_count": retry_count + 1,
                "status": "running",
                "error_message": str(exc)
            }
    return _node

def route_after_llm(state: AgentState) -> str:
    max_retries = _get_max_retries_llm()
    retry_count = state.get("retry_count", 0)
    if state.get("status") == "failed" or retry_count >= max_retries:
        return "__end__"
        
    if state.get("status") == "running" and retry_count > 0:
        return "call_llm"
        
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

    HIGH / MEDIUM / LOW confidence  →  HARD_BLOCK
    """

    async def _node(state: GuardrailState) -> dict:
        from src.core.tools.prompt_injection import scan_prompt_injection  # noqa: PLC0415

        result = await scan_prompt_injection(state["nl_input"], llm)

        if result.is_injection and result.confidence in ("HIGH", "MEDIUM", "LOW"):
            block_reason = f"[PromptInjection/{result.confidence}] {result.reason}"
            return {
                "verdict": _HARD_BLOCK,
                "block_reason": block_reason,
                "message": f"Xin lỗi, tôi không có quyền truy cập SQL như yêu cầu của bạn. Lý do: {block_reason}",
            }
        return {}

    return _node


# ═════════════════════════════════════════════════════════════════════════════
# SQL Generation agent nodes
# ═════════════════════════════════════════════════════════════════════════════

def _get_max_retries() -> int:
    from src.utils import load_config  # noqa: PLC0415
    return load_config().get("agents", {}).get("sql_gen_agent", {}).get("max_retries", 2)


async def node_sql_gen_initialize(state: SqlGenState) -> dict:
    """Reset all output fields before the SQL generation pipeline starts."""
    return {
        "sql_query": state.get("sql_query", ""),
        "sql_error": state.get("sql_error", ""),
        "retry_count": 0,
        "status": "running",
        "result": [],
        "error_message": "",
    }


def node_sql_gen_generate(llm: BaseChatModel) -> Callable[[SqlGenState], dict]:
    """
    Return an async node that generates a SQL query via the LLM.

    On the first attempt ``retry_context`` is empty.
    On retries the previous SQL and error are included so the LLM can self-correct.
    """
    import re  

    from langchain_core.messages import HumanMessage, SystemMessage 

    from src.core.prompts.factory import PROMPTS_DIR, PromptFactory 

    system_text = PromptFactory.render("sql_gen_system")
    raw_human = (PROMPTS_DIR / "sql_gen_human.md").read_text(encoding="utf-8")

    async def _node(state: SqlGenState) -> dict:
        retry_context = ""
        if state.get("sql_error"):
            retry_context = (
                "Previous SQL attempt failed.\n"
                f"SQL tried:\n{state['sql_query']}\n"
                f"Error received:\n{state['sql_error']}\n"
                "Please analyse the error and generate a corrected SQL query."
            )

        human_text = (
            raw_human
            .replace("{{nl_input}}", state.get("nl_input", ""))
            .replace("{{schema_context}}", state.get("schema_context", ""))
            .replace("{{retry_context}}", retry_context)
        )

        response = await llm.ainvoke(
            [SystemMessage(content=system_text), HumanMessage(content=human_text)]
        )
        sql = response.content.strip()
        # Strip markdown code fences if the model wraps the output
        sql = re.sub(r"^```(?:sql)?\s*\n?", "", sql, flags=re.IGNORECASE)
        sql = re.sub(r"\n?```\s*$", "", sql).strip()
        return {"sql_query": sql}

    return _node


async def node_sql_gen_execute(state: SqlGenState, config: RunnableConfig) -> dict:
    """
    Execute the generated SQL via the database injected through LangGraph config:

        await agent.ainvoke(inputs, config={"configurable": {"db": db_instance}})

    Increments ``retry_count`` on failure. Once ``retry_count`` reaches the
    configured retry limit, sets ``status="failed"`` so the router stops the loop.
    """
    db = (config.get("configurable") or {}).get("db") if config else None
    max_retries = _get_max_retries()

    if db is None:
        err = "Database not available – pass db via config['configurable']['db']"
        new_count = state.get("retry_count", 0) + 1
        if new_count >= max_retries:
            return {
                "sql_error": err,
                "retry_count": new_count,
                "status": "failed",
                "error_message": f"Không thể thực thi SQL sau {max_retries} lần thử. Lỗi: {err}",
            }
        return {"sql_error": err, "retry_count": new_count, "status": "running"}

    try:
        rows = await db.execute(state.get("sql_query", ""))
        return {
            "status": "success",
            "result": rows if isinstance(rows, list) else [],
            "sql_error": "",
        }
    except Exception as exc:  # noqa: BLE001
        err = str(exc)
        new_count = state.get("retry_count", 0) + 1
        if new_count >= max_retries:
            return {
                "sql_error": err,
                "retry_count": new_count,
                "status": "failed",
                "error_message": f"Không thể thực thi SQL sau {max_retries} lần thử. Lỗi: {err}",
            }
        return {"sql_error": err, "retry_count": new_count, "status": "running"}


def route_sql_gen_after_execute(state: SqlGenState) -> str:
    """
    Conditional edge after execute:
      success  →  END
      failed   →  END  (retry_count exhausted, error_message is set)
      retry    →  "generate"  (loop back for self-correction)
    """
    status = state.get("status", "running")
    if status == "success":
        return "success"
    if status == "failed":
        return "failed"
    return "retry"
