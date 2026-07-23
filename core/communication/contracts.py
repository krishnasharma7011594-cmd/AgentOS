"""Inter-agent communication protocol contracts."""

from abc import ABC, abstractmethod

from core.communication.messages import AgentCommunicationEnvelope


class BaseCommunicationContract(ABC):
    """Abstract interface defining standard validation for agent messages."""

    @abstractmethod
    def validate_envelope(self, envelope: AgentCommunicationEnvelope) -> bool:
        """Validate inter-agent message schema and protocol requirements."""
        pass
