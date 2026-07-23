"""GET /agents — list registered agents and their capabilities."""

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(tags=["Agents"])


@router.get("/agents", response_model=List[Dict[str, Any]])
async def list_agents(request: Request) -> List[Dict[str, Any]]:
    """Return all dynamically registered agents and their capabilities."""
    orchestrator = getattr(request.app.state, "orchestrator", None)
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="AgentOS orchestrator not ready.")

    agent_names = orchestrator.agent_registry.list_agents()
    result = []
    for name in agent_names:
        agent = orchestrator.agent_registry.get_agent(name)
        caps = [
            {"name": c.name, "description": c.description}
            for c in getattr(agent, "capabilities", [])
        ]
        result.append({"name": name, "description": agent.description, "capabilities": caps})
    return result
