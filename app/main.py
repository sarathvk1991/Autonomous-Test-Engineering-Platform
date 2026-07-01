"""FastAPI application entry point — the single deployable unit.

This module assembles the modular monolith: it wires shared infrastructure
(settings, logging) and mounts the router of each activated platform layer.

Only the Requirement Intelligence Layer is mounted in Phase 1. Future layers
expose their own ``router`` and are added here as they come online, keeping the
deployment a single ASGI application.

Run locally:
    uvicorn app.main:app --reload
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.core.settings import get_settings
from infrastructure.logging import configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application startup/shutdown hook.

    Initialise cross-cutting concerns here (logging, connection pools,
    connector health checks). Tear them down on shutdown.
    """
    settings = get_settings()
    configure_logging(level=settings.log_level, json_output=settings.log_json)
    logger.info("application.startup", env=settings.app_env, name=settings.app_name)
    yield
    logger.info("application.shutdown")


def create_app() -> FastAPI:
    """Application factory.

    Using a factory (rather than a module-level singleton only) keeps the app
    testable and lets tooling import a fresh instance with overridden settings.
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        debug=settings.app_debug,
        lifespan=lifespan,
    )

    # Mount the aggregate API router (per-layer routers are composed within it).
    app.include_router(api_router)

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        """Liveness/readiness probe for the deployable unit."""
        return {"status": "ok", "env": settings.app_env}

    return app


app = create_app()
