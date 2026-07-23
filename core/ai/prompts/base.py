"""Base prompt management interface for AgentOS."""

from abc import ABC, abstractmethod
from typing import Any, Dict


class BasePromptManager(ABC):
    """Abstract interface for managing and rendering prompt templates."""

    @abstractmethod
    def render_prompt(self, template_name: str, variables: Dict[str, Any]) -> str:
        """Render prompt template with variables."""
        pass
