"""Base security manager interface for AgentOS."""

from abc import ABC, abstractmethod


class BaseSecurityManager(ABC):
    """Abstract interface for system security policies, auth, and sandbox validation."""

    @abstractmethod
    def sanitize_input(self, text: str) -> str:
        """Sanitize prompt or input text before processing."""
        pass

    @abstractmethod
    def verify_token(self, token: str) -> bool:
        """Verify authorization token."""
        pass
