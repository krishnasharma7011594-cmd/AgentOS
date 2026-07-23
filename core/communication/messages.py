"""Inter-agent communication message contracts."""

from datetime import datetime
from typing import Any, Dict

from pydantic import BaseModel, Field


class AgentCommunicationEnvelope(BaseModel):
    """Envelope wrapping all inter-agent communications."""

    message_id: str = Field(..., description="Unique message GUID")
    sender_id: str = Field(..., description="ID/Name of sender agent or supervisor")
    recipient_id: str = Field(..., description="ID/Name of target agent or supervisor")
    event_type: str = Field(..., description="Type of event or interaction payload")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Structured content payload")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
