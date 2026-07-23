"""
FastAPI Server Entrypoint

Configures the FastAPI application, CORS middleware, API router inclusions,
and manages component graph lifecycle via lifespan context.

Architecture Layer: Apps / API
"""

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.routers import agents, chat, health, task
from core.config.settings import settings
from core.logging.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Manages application startup and shutdown lifecycle.

    Builds the dependency injection component graph once at server boot and binds
    the SupervisorOrchestrator to `app.state.orchestrator` for request handlers.
    """
    logger.info("AgentOS API: startup — building component graph")
    try:
        from core.di.container import build_orchestrator

        app.state.orchestrator = build_orchestrator()
        logger.info("AgentOS API: component graph ready")
    except Exception as exc:
        logger.error("AgentOS API: startup failed", error=str(exc))
        app.state.orchestrator = None
        app.state.startup_error = str(exc)

    yield

    logger.info("AgentOS API: shutdown")


def create_app() -> FastAPI:
    """
    FastAPI application factory function.

    Returns:
        FastAPI: Configured web application instance.
    """
    application = FastAPI(
        title=settings.app_name,
        version="0.2.0",
        description="AgentOS API Server — Phase 2: End-to-End Agent Execution",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(health.router)
    application.include_router(chat.router)
    application.include_router(agents.router)
    application.include_router(task.router)

    @application.get("/", include_in_schema=False)
    async def root() -> dict[str, Any]:
        return {
            "name": settings.app_name,
            "version": "0.2.0",
            "docs": "/docs",
        }

    return application


app = create_app()
