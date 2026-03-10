"""
src/routers/test_guardrail.py
──────────────────────────────
Development / testing router for the Guardrail Agent.

Endpoints
─────────
POST /test/guardrail
    Scan a single NL input for prompt-injection threats.

POST /test/guardrail/batch
    Scan multiple NL inputs concurrently (regression testing).
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.core.agents.factory import AgentFactory

router = APIRouter(prefix="/test/guardrail", tags=["Test – Guardrail"])


# ── Request / Response models ─────────────────────────────────────────────────

class GuardrailRequest(BaseModel):
    nl_input: str = Field(
        ...,
        description="Natural language query from the user.",
        examples=["Show me all orders from last month"],
    )


class GuardrailResponse(BaseModel):
    verdict: str = Field(description="PASS or HARD_BLOCK")
    block_reason: str = Field(description="Reason for blocking (empty when PASS)")
    warnings: list[str] = Field(description="Non-blocking diagnostic messages")
    message: str = Field(description="Human-readable response message")


def _build_response(state: dict, fallback_input: str = "") -> GuardrailResponse:
    verdict = state.get("verdict", "PASS")
    return GuardrailResponse(
        verdict=verdict,
        block_reason=state.get("block_reason", ""),
        warnings=state.get("warnings", []),
        message=state.get("message", ""),
    )


class BatchGuardrailRequest(BaseModel):
    cases: list[GuardrailRequest] = Field(
        ...,
        description="List of nl_input strings to evaluate.",
        min_length=1,
    )


class BatchGuardrailResponse(BaseModel):
    results: list[GuardrailResponse]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("", response_model=GuardrailResponse, summary="Scan NL input for injection")
async def run_guardrail(body: GuardrailRequest) -> GuardrailResponse:
    """
    Run the prompt-injection scan on the user's natural language input.

    Returns ``PASS`` when safe, ``HARD_BLOCK`` when an injection attempt
    is detected with HIGH or MEDIUM confidence.
    """
    agent = AgentFactory.create("guardrail")
    state = await agent.ainvoke({"nl_input": body.nl_input})
    return _build_response(state)


@router.post(
    "/batch",
    response_model=BatchGuardrailResponse,
    summary="Scan multiple NL inputs concurrently",
)
async def run_guardrail_batch(body: BatchGuardrailRequest) -> BatchGuardrailResponse:
    """
    Evaluate multiple NL inputs concurrently via ``asyncio.gather``.
    Useful for running a regression suite of known-safe and known-malicious queries.
    """
    agent = AgentFactory.create("guardrail")

    async def _run(case: GuardrailRequest) -> GuardrailResponse:
        state = await agent.ainvoke({"nl_input": case.nl_input})
        return _build_response(state)

    results = await asyncio.gather(*[_run(c) for c in body.cases])
    return BatchGuardrailResponse(results=list(results))
