"""
src/core/workflows/factory.py
────────────────────────────
Central registry and factory for workflows.

To add a new workflow
---------------------
    1. Create ``src/core/workflows/my_workflow.py`` subclassing ``BaseWorkflow``.
    2. Import and register the class below:

        from src.core.workflows.my_workflow import MyWorkflow

        WORKFLOW_REGISTRY: dict[str, type[BaseWorkflow]] = {
            "my_workflow": MyWorkflow,   # ← add here
        }

    3. Add config to ``config/app.yaml``:

        workflows:
          default: "my_workflow"
          my_workflow:
            agents: ["supervisor", "researcher"]
            checkpointer: true

Usage
-----
    from src.core.workflows.factory import WorkflowFactory

    workflow = WorkflowFactory.create()              # uses app.yaml default
    workflow = WorkflowFactory.create("my_workflow")
    result   = await workflow.ainvoke({"messages": [...]})
"""

from __future__ import annotations

from src.core.workflows.base import BaseWorkflow
from src.core.workflows.nlq_workflow import NlqWorkflow
from src.utils import load_config

# ─────────────────────────────────────────────────────────────────────────────
# Registry – map workflow name  →  workflow class
# ─────────────────────────────────────────────────────────────────────────────
WORKFLOW_REGISTRY: dict[str, type[BaseWorkflow]] = {
    "nlq": NlqWorkflow,
}


class WorkflowFactory:
    @staticmethod
    def create(name: str | None = None, config: dict | None = None) -> BaseWorkflow:
        """
        Instantiate and return the workflow registered under *name*.

        Falls back to ``config/app.yaml``  ->  ``workflows.default`` when
        *name* is ``None``.

        Raises
        ------
        ValueError  – when *name* cannot be resolved or is not in the registry.
        """
        app_cfg = load_config()
        name = name or app_cfg.get("workflows", {}).get("default")

        if not name:
            raise ValueError(
                "No workflow name supplied and 'workflows.default' is not set "
                "in config/app.yaml."
            )
        if name not in WORKFLOW_REGISTRY:
            raise ValueError(
                f"Workflow '{name}' not found in WORKFLOW_REGISTRY. "
                f"Available workflows: {list(WORKFLOW_REGISTRY)}"
            )

        workflow_config = config or app_cfg.get("workflows", {}).get(name, {})
        return WORKFLOW_REGISTRY[name](config=workflow_config)

    @staticmethod
    def list_workflows() -> list[str]:
        """Return the names of all registered workflows."""
        return list(WORKFLOW_REGISTRY)
