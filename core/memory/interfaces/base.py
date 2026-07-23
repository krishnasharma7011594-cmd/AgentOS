"""Base memory interface for AgentOS."""

from abc import ABC, abstractmethod
from typing import List, Optional

from core.models.domain import Message


class BaseMemory(ABC):
    """Abstract interface defining standard memory operations (store, retrieve, clear)."""

    @abstractmethod
    async def add_message(self, session_id: str, message: Message) -> None:
        """Add a message to the memory store."""
        pass

    @abstractmethod
    async def get_messages(self, session_id: str, limit: Optional[int] = None) -> List[Message]:
        """Retrieve stored messages for a session."""
        pass

    @abstractmethod
    async def clear_session(self, session_id: str) -> None:
        """Clear all stored messages for a session."""
        pass
