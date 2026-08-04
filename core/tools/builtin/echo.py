from typing import Any

from core.models.capability import CapabilityVersion
from core.models.tool import ToolCategory, ToolExecutionContext, ToolManifest
from core.tools.base import BaseTool


class EchoTool(BaseTool):
    """A mock tool that echoes the input parameter."""

    def get_manifest(self) -> ToolManifest:
        return ToolManifest(
            name="echo_tool",
            version=CapabilityVersion(major=1, minor=0, patch=0),
            description="Echoes the provided message.",
            capabilities=["echo"],
            category=ToolCategory.MOCK,
            entry_point="core.tools.builtin.echo.EchoTool",
        )

    async def execute(self, context: ToolExecutionContext, **kwargs: Any) -> Any:
        message = kwargs.get("message", "")
        return f"Echo: {message}"
