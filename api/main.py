import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from core.config import get_settings
from db.database import init_db
from api.routers import prompts, executions

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting LLMOps service | env=%s", settings.app_env)
    await init_db()
    logger.info("Database ready")
    yield
    logger.info("Shutting down LLMOps service")


app = FastAPI(
    title="LLMOps Prompt Management API",
    description=(
        "In-house LLMOps solution for programmatic prompt storage, "
        "versioning, dynamic rendering (Jinja2), and Anthropic execution."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(prompts.router)
app.include_router(executions.router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception | path=%s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__},
    )


@app.get("/health", tags=["ops"])
async def health():
    return {"status": "ok", "env": settings.app_env}