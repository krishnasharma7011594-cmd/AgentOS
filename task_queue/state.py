"""Task queue item state representation."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from workflow.states import WorkflowState


class QueueItemState(BaseModel):
    """Encapsulates current state of an item inside the Task Queue."""

    task_id: str = Field(..., description="Unique task identifier")
    state: WorkflowState = Field(default=WorkflowState.QUEUED)
    retries: int = Field(default=0)
    enqueued_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error: Optional[str] = None
