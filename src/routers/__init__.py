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
    # Add routers here as the project grows:
    # from src.routers.chat import router as chat_router
    # app.include_router(chat_router)
    pass
