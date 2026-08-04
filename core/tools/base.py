"""Base tool interface for AgentOS."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from core.models.tool import ToolManifest, ToolHealth, ToolExecutionContext


class ToolSchema(BaseModel):
    """Metadata schema defining a tool's name, description and parameters."""

    name: str = Field(..., description="Unique name of the tool")
    description: str = Field(
        ...,
        description="Human readable explanation of tool capabilities",
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="JSON schema of input arguments",
    )


class BaseTool(ABC):
    """
    Abstract Base Tool interface implemented by all AgentOS tools.

    Every concrete tool must:
      - Implement `get_manifest()` to expose its ToolManifest.
      - Implement the async lifecycle hooks.
    """

    def __init__(self) -> None:
        self.schema: Optional[ToolSchema] = None

    @abstractmethod
    def get_manifest(self) -> ToolManifest:
        """Return the manifest describing this tool."""
        pass

    @property
    def name(self) -> str:
        return self.get_manifest().name

    @property
    def description(self) -> str:
        return self.get_manifest().description

    # ------------------------------------------------------------------
    # Lifecycle Hooks
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Called once when the tool is loaded into the registry."""
        pass

    async def health_check(self) -> ToolHealth:
        """Return the current health status of the tool."""
        from core.models.tool import ToolHealth
        return ToolHealth(status="HEALTHY")

    @abstractmethod
    async def execute(self, context: ToolExecutionContext, **kwargs: Any) -> Any:
        """Execute tool logic given key-value parameters and a context."""
        pass

    async def cleanup(self) -> None:
        """Called after an execution completes, whether successful or not."""
        pass

    async def shutdown(self) -> None:
        """Called when the tool is unloaded or the system shuts down."""
        pass
