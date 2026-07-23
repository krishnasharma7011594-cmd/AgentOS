"""ResearchAgent configuration."""

from pydantic import BaseModel, Field


class ResearchAgentConfig(BaseModel):
    """Configuration for Research Agent."""

    agent_name: str = "ResearchAgent"
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, gt=0)
    enabled: bool = Field(default=True)
