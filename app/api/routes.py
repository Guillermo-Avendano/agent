"""API routes for the Guille Agent."""

from pathlib import Path

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.config import settings
from app.db.connection import get_session
from app.models.schemas import (
    AskRequest,
    AskResponse,
    HealthResponse,
    SchemaLoadResponse,
)
from app.agent.core import ask_agent
from app.memory.schema_loader import load_all_schemas
from app.memory.qdrant_store import get_qdrant_client

logger = structlog.get_logger(__name__)

router = APIRouter()


# ─── Health Check ────────────────────────────────────────────
@router.get("/health", response_model=HealthResponse, tags=["system"])
async def health_check(session: AsyncSession = Depends(get_session)):
    """Check connectivity to all services."""
    # PostgreSQL
    pg_status = "ok"
    try:
        await session.execute(text("SELECT 1"))
    except Exception as e:
        pg_status = f"error: {e}"

    # Qdrant
    qdrant_status = "ok"
    try:
        client = get_qdrant_client()
        client.get_collections()
    except Exception as e:
        qdrant_status = f"error: {e}"

    # Ollama
    ollama_status = "ok"
    try:
        async with httpx.AsyncClient(timeout=5) as http:
            resp = await http.get(f"{settings.ollama_base_url}/")
            if resp.status_code != 200:
                ollama_status = f"http {resp.status_code}"
    except Exception as e:
        ollama_status = f"error: {e}"

    overall = "healthy" if all(
        s == "ok" for s in [pg_status, qdrant_status, ollama_status]
    ) else "degraded"

    return HealthResponse(
        status=overall,
        postgres=pg_status,
        qdrant=qdrant_status,
        ollama=ollama_status,
    )


# ─── Load Schema Descriptions ───────────────────────────────
@router.post("/schema/load", response_model=SchemaLoadResponse, tags=["schema"])
async def load_schema():
    """Index schema descriptions from JSON files into Qdrant."""
    try:
        count = load_all_schemas()
        return SchemaLoadResponse(
            indexed_chunks=count,
            message=f"Successfully indexed {count} schema chunks.",
        )
    except Exception as e:
        logger.error("schema_load.error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ─── Ask the Agent ───────────────────────────────────────────
@router.post("/ask", response_model=AskResponse, tags=["agent"])
async def ask(
    request: AskRequest,
    session: AsyncSession = Depends(get_session),
):
    """Send a natural-language question to the AI agent."""
    logger.info("api.ask", question=request.question[:100])
    try:
        result = await ask_agent(
            question=request.question,
            session=session,
            chat_history=[m.model_dump() for m in request.chat_history],
        )
        return AskResponse(**result)
    except Exception as e:
        logger.error("api.ask.error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Agent error: {e}")


# ─── Serve Charts ────────────────────────────────────────────
@router.get("/charts/{filename}", tags=["charts"])
async def get_chart(filename: str):
    """Download a generated chart image."""
    # Sanitize filename to prevent path traversal
    safe_name = Path(filename).name
    filepath = Path("/app/charts_output") / safe_name
    if not filepath.exists() or not filepath.is_file():
        raise HTTPException(status_code=404, detail="Chart not found.")
    return FileResponse(filepath, media_type="image/png")
