"""Working memory (short-term context window) skeleton implementation."""

from typing import Dict, List, Optional

from core.memory.interfaces.base import BaseMemory
from core.models.domain import Message


class WorkingMemory(BaseMemory):
    """In-memory transient context window skeleton."""

    def __init__(self) -> None:
        self._store: Dict[str, List[Message]] = {}

    async def add_message(self, session_id: str, message: Message) -> None:
        if session_id not in self._store:
            self._store[session_id] = []
        self._store[session_id].append(message)

    async def get_messages(self, session_id: str, limit: Optional[int] = None) -> List[Message]:
        messages = self._store.get(session_id, [])
        if limit:
            return messages[-limit:]
        return messages

    async def clear_session(self, session_id: str) -> None:
        self._store.pop(session_id, None)
