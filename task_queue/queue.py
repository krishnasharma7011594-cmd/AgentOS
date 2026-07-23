"""Abstract Task Queue interface."""

from abc import ABC, abstractmethod
from typing import Optional

from core.models.domain import Task
from task_queue.state import QueueItemState


class BaseTaskQueue(ABC):
    """Abstract interface for task enqueueing and dequeuing."""

    @abstractmethod
    async def enqueue(self, task: Task) -> QueueItemState:
        """Enqueue task for background execution."""
        pass

    @abstractmethod
    async def dequeue(self) -> Optional[Task]:
        """Dequeue next available task."""
        pass

    @abstractmethod
    async def get_status(self, task_id: str) -> Optional[QueueItemState]:
        """Get status of task in queue."""
        pass
