"""Abstract Task Worker interface."""

from abc import ABC, abstractmethod

from task_queue.queue import BaseTaskQueue


class BaseTaskWorker(ABC):
    """Abstract interface for background task processing worker."""

    def __init__(self, queue: BaseTaskQueue):
        self.queue = queue

    @abstractmethod
    async def start(self) -> None:
        """Start worker loop."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Gracefully stop worker loop."""
        pass
