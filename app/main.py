"""FastAPI application entry point."""

import structlog
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.api.routes import router
from app.api.openai_compat import openai_router
from app.db.connection import dispose_engine
from app.memory.file_loader import load_files_for_memory

# ─── Structured logging ─────────────────────────────────────
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer() if settings.log_level == "DEBUG"
        else structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        structlog.get_level_from_name(settings.log_level)
    ),
)

logger = structlog.get_logger(__name__)

# ─── Rate limiter ────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["30/minute"])


# ─── Lifespan ────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("app.startup", ollama=settings.ollama_base_url, model=settings.ollama_model)
    try:
        total = load_files_for_memory()
        logger.info("app.files_loaded", chunks=total)
    except Exception as e:
        logger.warning("app.files_load_error", error=str(e))
    yield
    await dispose_engine()
    logger.info("app.shutdown")


# ─── App ─────────────────────────────────────────────────────
app = FastAPI(
    title="SQL Agent API",
    description="AI agent that queries PostgreSQL, explains results, and generates charts.",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(openai_router)
