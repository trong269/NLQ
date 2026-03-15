"""
src/core/tools/prompt_injection.py
────────────────────────────────────
LLM-based prompt-injection scanner.

Prompts are loaded from:
  src/core/prompts/guardrail_injection_scan_system.md
  src/core/prompts/guardrail_injection_scan_human.md
"""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

from src.core.prompts.factory import PromptFactory


def _build_prompt() -> ChatPromptTemplate:
    # System prompt has no variables – render directly
    system_text = PromptFactory.render("guardrail_injection_scan_system")

    # Human template has {{nl_input}}; read raw and convert to LangChain {nl_input}
    from src.core.prompts.factory import PROMPTS_DIR  # noqa: PLC0415
    raw_human = (PROMPTS_DIR / "guardrail_injection_scan_human.md").read_text(encoding="utf-8")
    lc_human = raw_human.replace("{{nl_input}}", "{nl_input}")

    return ChatPromptTemplate.from_messages([
        ("system", system_text),
        ("human", lc_human),
    ])


_PROMPT = _build_prompt()


class InjectionScanResult(BaseModel):
    is_injection: bool
    confidence: str   # HIGH | MEDIUM | LOW
    reason: str


async def scan_prompt_injection(
    nl_input: str,
    llm: BaseChatModel,
) -> InjectionScanResult:
    """
    Use *llm* to classify whether *nl_input* is a prompt-injection attempt.

    Returns an ``InjectionScanResult``.
    """
    chain = _PROMPT | llm.with_structured_output(InjectionScanResult)
    return await chain.ainvoke({"nl_input": nl_input})
