"""
src/routers/__init__.py
───────────────────────
Central router registration.

How to add a new router
-----------------------
    1. Create ``src/routers/my_router.py`` with a FastAPI ``APIRouter``.
    2. Import and include it here:

        from src.routers.my_router import router as my_router

        def register_routers(app: FastAPI) -> None:
            app.include_router(my_router)
"""

from fastapi import FastAPI


def register_routers(app: FastAPI) -> None:
    """Include all API routers into *app*."""
    from src.routers.database import router as database_router
    from src.routers.test_guardrail import router as test_guardrail_router
    from src.routers.workflow import router as workflow_router

    app.include_router(test_guardrail_router)
    app.include_router(workflow_router)
    app.include_router(database_router)
