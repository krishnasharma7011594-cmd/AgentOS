"""Base tool interface for AgentOS."""

from abc import ABC, abstractmethod
from typing import Any, ClassVar, Dict, Optional

from pydantic import BaseModel, Field

from core.models.domain import ToolMetadata


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
      - Declare a class-level METADATA: ClassVar[ToolMetadata] object.
      - Implement the async execute(**kwargs) method.

    The METADATA object makes ToolRegistry metadata-driven so callers can
    inspect tool capabilities without instantiating the tool class.
    """

    # Subclasses override this with their rich ToolMetadata descriptor.
    METADATA: ClassVar[ToolMetadata]

    def __init__(
        self,
        name: str,
        description: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.schema = ToolSchema(
            name=name,
            description=description,
            parameters=parameters or {},
        )

    @property
    def name(self) -> str:
        return self.schema.name

    @property
    def description(self) -> str:
        return self.schema.description

    @abstractmethod
    async def execute(self, **kwargs: Any) -> Any:
        """Execute tool logic given key-value parameters."""
        pass
