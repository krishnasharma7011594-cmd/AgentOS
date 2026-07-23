"""
POST /chat API Router

Exposes the primary REST endpoint for user interaction with AgentOS.
Receives user prompts, submits them to the SupervisorOrchestrator, and returns structured responses.

Architecture Layer: Apps / API / Routers
"""

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from core.logging.logger import logger
from core.models.domain import ExecutionResult, Goal
from core.utils.helpers import generate_uuid

router = APIRouter(tags=["Chat"])


class ChatRequest(BaseModel):
    """Payload schema for POST /chat requests."""

    message: str = Field(..., min_length=1, description="User message or research query")


class ChatResponse(BaseModel):
    """Payload schema for POST /chat responses."""

    status: str
    response: str
    tasks: List[Dict[str, Any]] = Field(default_factory=list)
    goal_id: str


@router.post("/chat", response_model=ChatResponse)
async def post_chat(request: Request, body: ChatRequest) -> ChatResponse:
    """
    Primary user chat endpoint.

    Flow:
        User Request -> FastAPI -> SupervisorOrchestrator -> Planner ->
        Router -> Agent -> Validator -> Report -> User
    """
    logger.info("POST /chat: request received", message_preview=body.message[:80])

    orchestrator = getattr(request.app.state, "orchestrator", None)
    if orchestrator is None:
        startup_error = getattr(request.app.state, "startup_error", "Unknown startup error")
        logger.error("POST /chat: orchestrator not available", error=startup_error)
        raise HTTPException(
            status_code=503,
            detail=f"AgentOS is not ready: {startup_error}",
        )

    goal = Goal(
        id=generate_uuid(),
        description=body.message,
    )

    try:
        result: ExecutionResult = await orchestrator.execute_goal(goal)
    except Exception as exc:
        logger.error("POST /chat: orchestration failed", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Orchestration error: {exc}") from exc

    logger.info(
        "POST /chat: response ready",
        goal_id=goal.id,
        status=result.status,
    )

    return ChatResponse(
        status=result.status,
        response=result.response,
        goal_id=result.goal_id,
        tasks=[
            {
                "task_id": t.task_id,
                "agent_id": t.agent_id,
                "status": t.status.value,
                "summary": t.summary[:200] + "..." if len(t.summary) > 200 else t.summary,
                "metadata": t.metadata,
                "error": t.error,
            }
            for t in result.tasks
        ],
    )
