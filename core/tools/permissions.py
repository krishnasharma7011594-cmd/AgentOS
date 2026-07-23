"""Tool permissions and security policy interface."""

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseToolPermissionsPolicy(ABC):
    """Abstract interface for checking security policy before tool execution."""

    @abstractmethod
    def validate_permission(self, agent_id: str, tool_name: str, args: Dict[str, Any]) -> bool:
        """Check if an agent is authorized to execute a specific tool with given args."""
        pass
