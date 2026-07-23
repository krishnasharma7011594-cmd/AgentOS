"""GitHubAgent configuration settings."""

from pydantic import BaseModel, Field


class GitHubAgentConfig(BaseModel):
    """Configuration for GitHub Agent."""

    agent_name: str = "GitHubAgent"
    default_branch: str = Field(default="main")
    enabled: bool = Field(default=True)
