"""Base reasoning engine interface for AgentOS."""

from abc import ABC, abstractmethod
from typing import Any, Dict

from core.models.domain import Task


class BaseReasoningEngine(ABC):
    """Abstract interface for LLM reasoning and decision strategies (ReAct, CoT, etc.)."""

    @abstractmethod
    async def reason_step(self, context: Dict[str, Any], current_task: Task) -> Dict[str, Any]:
        """Perform a single reasoning step for a given task."""
        pass
