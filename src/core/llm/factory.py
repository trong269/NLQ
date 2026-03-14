"""
src/core/llm/factory.py
───────────────────────
Central factory for creating chat-model instances.

Usage
-----
    from src.core.llm.factory import LLMFactory

    llm = LLMFactory.create()                                   # uses app.yaml defaults
    llm = LLMFactory.create(provider="anthropic")
    llm = LLMFactory.create(provider="openai", model="gpt-4o") # override model
"""

from __future__ import annotations

import os

from langchain_core.language_models.chat_models import BaseChatModel

from src.utils import load_config


class LLMFactory:
    @staticmethod
    def create(
        provider: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        **kwargs,
    ) -> BaseChatModel:
        """
        Instantiate a chat model for the requested *provider*.

        Falls back to ``config/app.yaml`` values when parameters are ``None``.

        Supported providers
        -------------------
        ``"openai"`` | ``"anthropic"`` | ``"google"``
        """
        config = load_config()
        llm_cfg = config.get("llm", {})

        provider = provider or llm_cfg.get("default_provider", "openai")
        provider_cfg = llm_cfg.get("providers", {}).get(provider, {})

        model = model or provider_cfg.get("model") or llm_cfg.get("default_model", "gpt-4o-mini")
        temperature = temperature if temperature is not None else provider_cfg.get("temperature", 0.0)

        match provider:
            case "mega_llm":
                from langchain_openai import ChatOpenAI  # noqa: PLC0415
                return ChatOpenAI(
                    model=model,
                    base_url=provider_cfg.get("base_url", "https://ai.megallm.io/v1"),
                    api_key=os.getenv("MEGALLM_API_KEY"),
                    temperature=temperature,
                )
            case _:
                raise ValueError(
                    f"Unknown LLM provider '{provider}'. "
                    "Supported: 'mega_llm'."
                )
