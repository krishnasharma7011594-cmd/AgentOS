"""Token usage tracking interfaces for AgentOS."""

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseTokenTracker(ABC):
    """Abstract interface for recording LLM token usage and estimated cost."""

    @abstractmethod
    def record_usage(self, provider: str, prompt_tokens: int, completion_tokens: int) -> None:
        """Record token usage metrics."""
        pass

    @abstractmethod
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of accumulated token usage."""
        pass
