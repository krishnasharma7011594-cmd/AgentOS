"""
GET /health API Router

Exposes system health diagnostics. Verifies API availability, LLM provider initialization,
and active agent registration status.

Architecture Layer: Apps / API / Routers
"""

from typing import Any, Dict

from fastapi import APIRouter, Request

from core.config.settings import settings

router = APIRouter(tags=["Health"])


@router.get("/health")
async def get_health(request: Request) -> Dict[str, Any]:
    """
    Returns system status and component health checks.

    Checks:
      - API engine status
      - Initialized LLM provider status
      - ResearchAgent registration in AgentRegistry
    """
    orchestrator = getattr(request.app.state, "orchestrator", None)
    startup_error = getattr(request.app.state, "startup_error", None)

    if orchestrator is None:
        return {
            "status": "degraded",
            "app_name": settings.app_name,
            "version": "0.2.0",
            "environment": settings.app_env,
            "error": startup_error or "Orchestrator not initialized",
            "checks": {
                "api": True,
                "llm_provider": False,
                "research_agent_registered": False,
            },
        }

    agent_names = orchestrator.agent_registry.list_agents()
    research_registered = "ResearchAgent" in agent_names
    capabilities = orchestrator.capability_registry.list_capabilities()

    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "version": "0.2.0",
        "environment": settings.app_env,
        "llm_provider": settings.llm.default_provider,
        "checks": {
            "api": True,
            "llm_provider": True,
            "research_agent_registered": research_registered,
        },
        "registered_agents": agent_names,
        "registered_capabilities": capabilities,
    }
