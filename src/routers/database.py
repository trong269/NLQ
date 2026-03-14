from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from src.databases.factory import DatabaseFactory
from src.databases.mysql_database import MySQLDatabase

router = APIRouter(prefix="/database", tags=["Database"])


class DatabaseHealthResponse(BaseModel):
    status: str
    detail: str


class DatabaseSchemaResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    schema_text: str = Field(alias="schema")


@router.get("/health", response_model=DatabaseHealthResponse, summary="Check DB connectivity")
async def database_health() -> DatabaseHealthResponse:
    db = DatabaseFactory.create("mysql")
    try:
        async with db:
            result = await db.execute("SELECT 1 AS ok")
        if not result:
            raise RuntimeError("No response from database")
        return DatabaseHealthResponse(status="ok", detail="Connected to MySQL successfully")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {exc}") from exc


@router.get("/schema", response_model=DatabaseSchemaResponse, summary="Get DB schema text")
async def database_schema() -> DatabaseSchemaResponse:
    db = DatabaseFactory.create("mysql")
    try:
        async with db:
            if not isinstance(db, MySQLDatabase):
                raise RuntimeError("Registered mysql adapter is not MySQLDatabase")
            schema_text = await db.get_schema_text()
        return DatabaseSchemaResponse(schema_text=schema_text)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch schema: {exc}") from exc
