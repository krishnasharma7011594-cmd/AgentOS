"""Core event schemas for AgentOS."""

from datetime import datetime
from typing import Any, Dict

from pydantic import BaseModel, Field


class BaseEvent(BaseModel):
    """Base event schema for AgentOS system events."""

    event_id: str = Field(..., description="Unique event identifier")
    name: str = Field(..., description="Event name (e.g. task.created, agent.registered)")
    data: Dict[str, Any] = Field(default_factory=dict, description="Event data dictionary")
    created_at: datetime = Field(default_factory=datetime.utcnow)
