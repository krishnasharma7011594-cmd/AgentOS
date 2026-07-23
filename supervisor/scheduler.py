"""Supervisor Scheduler interface."""

from abc import ABC, abstractmethod
from typing import List

from core.models.domain import ExecutionPlan, Task


class BaseSupervisorScheduler(ABC):
    """Abstract interface for scheduling task execution sequences."""

    @abstractmethod
    async def schedule_tasks(self, plan: ExecutionPlan) -> List[Task]:
        """Schedule and order tasks for execution."""
        pass
