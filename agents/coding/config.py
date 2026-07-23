"""CodingAgent configuration settings."""

from pydantic import BaseModel, Field


class CodingAgentConfig(BaseModel):
    """Configuration for Coding Agent."""

    agent_name: str = "CodingAgent"
    default_language: str = Field(default="python")
    enabled: bool = Field(default=True)
