"""
src/core/agents/factory.py
──────────────────────────
Central registry and factory for agents.

To add a new agent
------------------
    1. Create ``src/core/agents/my_agent.py`` that subclasses ``BaseAgent``.
    2. Import and register the class below:

        from src.core.agents.my_agent import MyAgent

        AGENT_REGISTRY: dict[str, type[BaseAgent]] = {
            "my_agent": MyAgent,   # ← add here
        }

    3. Add config to ``config/app.yaml``:

        agents:
          my_agent:
            llm_provider: "openai"
            llm_model: "gpt-4o-mini"
            tools: []

Usage
-----
    from src.core.agents.factory import AgentFactory

    agent = AgentFactory.create("my_agent")
    result = await agent.ainvoke({"messages": [HumanMessage(content="Hi")]})
"""

from __future__ import annotations

from src.core.agents.base import BaseAgent
from src.core.agents.guardrail_agent import GuardrailAgent
from src.core.agents.schema_linking_agent import SchemaLinkingAgent
from src.core.agents.sql_gen_agent import SqlGenAgent
from src.core.agents.reflection_agent import ReflectionAgent
from src.utils import load_config

# ─────────────────────────────────────────────────────────────────────────────
# Registry – map agent name  →  agent class
# ─────────────────────────────────────────────────────────────────────────────
AGENT_REGISTRY: dict[str, type[BaseAgent]] = {
    "guardrail": GuardrailAgent,
    "schema_linking_agent": SchemaLinkingAgent,
    "sql_gen_agent": SqlGenAgent,
    "reflection_agent": ReflectionAgent,
}


class AgentFactory:
    @staticmethod
    def create(name: str, config: dict | None = None) -> BaseAgent:
        """
        Instantiate and return the agent registered under *name*.

        The ``config`` for the agent is resolved in this priority order:
          1. Explicit ``config`` argument (if provided)
          2. ``config/app.yaml``  ->  ``agents.<name>``
          3. Empty dict (agent may fall back to its own defaults)

        Raises
        ------
        ValueError  – when *name* is not in ``AGENT_REGISTRY``.
        """
        if name not in AGENT_REGISTRY:
            raise ValueError(
                f"Agent '{name}' not found in AGENT_REGISTRY. "
                f"Available agents: {list(AGENT_REGISTRY)}"
            )
        agent_config = config or load_config().get("agents", {}).get(name, {})
        return AGENT_REGISTRY[name](config=agent_config)

    @staticmethod
    def list_agents() -> list[str]:
        """Return the names of all registered agents."""
        return list(AGENT_REGISTRY)
