"""Tool executor interface for AgentOS."""

from abc import ABC, abstractmethod
from typing import Any, Dict

from core.tools.base import BaseTool
from core.tools.permissions import BaseToolPermissionsPolicy


class BaseToolExecutor(ABC):
    """Abstract interface for safely executing tools with permission checks."""

    def __init__(self, permissions_policy: BaseToolPermissionsPolicy | None = None):
        self.permissions_policy = permissions_policy

    @abstractmethod
    async def run_tool(self, tool: BaseTool, agent_id: str, args: Dict[str, Any]) -> Any:
        """Run tool after evaluating permission policy."""
        pass
