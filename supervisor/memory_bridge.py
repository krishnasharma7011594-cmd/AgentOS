"""Supervisor Memory Bridge interface."""

from abc import ABC, abstractmethod

from core.memory.interfaces.base import BaseMemory
from core.models.domain import ExecutionResult, Goal


class BaseSupervisorMemoryBridge(ABC):
    """Abstract interface for bridging Supervisor actions with core layered memory."""

    def __init__(self, memory: BaseMemory):
        self.memory = memory

    @abstractmethod
    async def record_goal(self, goal: Goal) -> None:
        """Store goal in memory."""
        pass

    @abstractmethod
    async def record_execution(self, result: ExecutionResult) -> None:
        """Store execution result in memory."""
        pass
