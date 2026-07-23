"""Long-term memory skeleton implementation."""

from typing import List, Optional

from core.memory.interfaces.base import BaseMemory
from core.models.domain import Message


class LongTermMemory(BaseMemory):
    """Long-term persistent episodic memory skeleton."""

    async def add_message(self, session_id: str, message: Message) -> None:
        """Placeholder for persisting message to DB/Vectorstore."""
        pass

    async def get_messages(self, session_id: str, limit: Optional[int] = None) -> List[Message]:
        """Placeholder for retrieving messages from persistent store."""
        return []

    async def clear_session(self, session_id: str) -> None:
        """Placeholder for clearing persistent messages."""
        pass
