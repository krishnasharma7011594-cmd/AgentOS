"""FinanceAgent configuration settings."""

from pydantic import BaseModel, Field


class FinanceAgentConfig(BaseModel):
    """Configuration for Finance Agent."""

    agent_name: str = "FinanceAgent"
    currency: str = Field(default="USD")
    enabled: bool = Field(default=True)
