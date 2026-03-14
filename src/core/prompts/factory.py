"""
src/core/prompts/factory.py
───────────────────────────
Loads prompt templates stored as ``*.md`` files and renders them
by substituting ``{{variable}}`` placeholders.

Usage
-----
    from src.core.prompts.factory import PromptFactory

    text = PromptFactory.render("example_prompt", task="Summarise", context="...")

Convention
----------
- One ``.md`` file  =  one prompt template.
- Variables use double-brace syntax: ``{{variable_name}}``.
- Files live next to this module in ``src/core/prompts/``.
"""

from __future__ import annotations

import re
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent


class PromptFactory:
    @staticmethod
    def render(name: str, **variables) -> str:
        """
        Load ``<name>.md`` from the prompts directory and replace
        every ``{{key}}`` placeholder with the corresponding keyword argument.

        Parameters
        ----------
        name:      Template filename without the ``.md`` extension.
        **variables: Placeholder key/value pairs.

        Raises
        ------
        FileNotFoundError  – when the template file does not exist.
        ValueError         – when required placeholders are still unfilled.
        """
        prompt_file = PROMPTS_DIR / f"{name}.md"
        if not prompt_file.exists():
            raise FileNotFoundError(
                f"Prompt template '{name}' not found at {prompt_file}"
            )

        template = prompt_file.read_text(encoding="utf-8")

        for key, value in variables.items():
            template = template.replace(f"{{{{{key}}}}}", str(value))

        # Warn callers about any remaining unfilled placeholders
        remaining = re.findall(r"\{\{(\w+)\}\}", template)
        if remaining:
            raise ValueError(
                f"Prompt '{name}' has unfilled placeholders: {remaining}"
            )

        return template

    @staticmethod
    def list_prompts() -> list[str]:
        """Return the names (without extension) of all available prompt templates."""
        return [f.stem for f in PROMPTS_DIR.glob("*.md")]
