"""Communication dispatcher interface - fixed import."""

from abc import ABC, abstractmethod
from typing import Any, Callable

from core.communication.events import BaseEvent
from core.communication.messages import AgentCommunicationEnvelope


class BaseCommunicationDispatcher(ABC):
    """Abstract interface for dispatching messages/events between components and agents."""

    @abstractmethod
    async def send_message(self, envelope: AgentCommunicationEnvelope) -> None:
        """Send message envelope to recipient agent via event bus."""
        pass

    @abstractmethod
    async def publish_event(self, event: BaseEvent) -> None:
        """Publish system event to all subscribed listeners."""
        pass

    @abstractmethod
    def subscribe(self, event_name: str, handler: Callable[[BaseEvent], Any]) -> None:
        """Subscribe handler function to a specific event name."""
        pass
