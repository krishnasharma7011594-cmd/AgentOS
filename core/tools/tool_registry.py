from typing import Dict, List, Optional
from core.tools.base import BaseTool
from core.models.tool import ToolHealth
from core.exceptions.base import ToolNotFoundError
from core.logging.logger import logger


class ToolRegistry:
    """
    Registry for storing loaded tool implementations and their lifecycle state.
    This registry does NOT know about planning or capability requests.
    """

    def __init__(self) -> None:
        # map: tool_name -> BaseTool instance
        self._tools: Dict[str, BaseTool] = {}
        # map: tool_name -> ToolHealth
        self._health_status: Dict[str, ToolHealth] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a concrete tool implementation."""
        manifest = tool.get_manifest()
        self._tools[manifest.name] = tool
        # Default health to UNKNOWN upon registration
        self._health_status[manifest.name] = ToolHealth(status="UNKNOWN")
        logger.info(
            "tool_registered",
            name=manifest.name,
            version=str(manifest.version)
        )

    def unregister(self, name: str) -> None:
        """Remove a tool from the registry."""
        if name in self._tools:
            del self._tools[name]
            if name in self._health_status:
                del self._health_status[name]
            logger.info("tool_unregistered", name=name)

    def get_tool(self, name: str) -> BaseTool:
        """Get a tool instance by name, raising an error if missing."""
        tool = self._tools.get(name)
        if not tool:
            raise ToolNotFoundError(name)
        return tool

    def get(self, name: str) -> Optional[BaseTool]:
        """Safe version of get_tool returning None if missing."""
        return self._tools.get(name)

    def list_tools(self) -> List[BaseTool]:
        """Return all registered tool instances."""
        return list(self._tools.values())

    def update_health(self, name: str, health: ToolHealth) -> None:
        """Update the health status of a tool."""
        if name in self._tools:
            self._health_status[name] = health

    def get_health(self, name: str) -> Optional[ToolHealth]:
        """Get the health status of a tool."""
        return self._health_status.get(name)
