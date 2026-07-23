"""POST /task — enqueue a named task for background processing (Phase 2 placeholder)."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from core.models.domain import Task
from core.utils.helpers import generate_uuid
from task_queue.state import QueueItemState
from workflow.states import WorkflowState

router = APIRouter(tags=["Task"])


class TaskRequest(BaseModel):
    name: str = Field(..., description="Task name")
    description: str = Field(..., description="Task detail description")
    capability: str = Field(default="web_research", description="Required capability")


@router.post("/task", response_model=QueueItemState)
async def post_task(request: TaskRequest) -> QueueItemState:
    """Enqueues a task definition. Full async processing in Phase 3."""
    task = Task(
        id=generate_uuid(),
        goal_id=generate_uuid(),
        name=request.name,
        description=request.description,
        required_capability=request.capability,
    )
    return QueueItemState(
        task_id=task.id,
        state=WorkflowState.QUEUED,
    )
