"""
Tool Registry

Central registry for dynamically discovering, registering, and executing tools
within AgentOS. Agents do NOT import tool classes directly — they query this
registry by name. This decoupling means new tools can be registered at runtime
without modifying any agent code.

Phase 3 extensions:
  - execute(): async dispatch by tool name, returning ToolResult
  - get_tool_descriptions(): formatted string injected into ReAct system prompts
  - get_tool(): raises ToolNotFoundError instead of returning None

Architecture Layer: Core / Tools
"""

from typing import Any, Dict, List, Optional

from core.exceptions.base import ToolNotFoundError
from core.logging.logger import logger
from core.models.domain import ToolCall, ToolResult
from core.tools.base import BaseTool, ToolSchema


class ToolRegistry:
    """
    Central registry for discovering, registering, and executing AgentOS tools.

    The registry is the single point of truth for what tools are available to
    an agent at runtime. Agents receive a reference to this registry via DI
    and never instantiate tools themselves.
    """

    def __init__(self) -> None:
        # name → BaseTool instance; populated at startup by DI container
        self._tools: Dict[str, BaseTool] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, tool: BaseTool) -> None:
        """
        Register a tool instance.

        Overwrites silently if a tool with the same name is re-registered —
        intentional to support hot-swapping tools in tests.
        """
        self._tools[tool.name] = tool
        logger.info("tool_registered", tool=tool.name)

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def get_tool(self, tool_name: str) -> BaseTool:
        """
        Return the tool instance for the given name.

        Raises:
            ToolNotFoundError: If no tool with that name is registered.
        """
        tool = self._tools.get(tool_name)
        if tool is None:
            raise ToolNotFoundError(tool_name)
        return tool

    def get(self, tool_name: str) -> Optional[BaseTool]:
        """Return the tool or None — safe variant used outside the ReAct loop."""
        return self._tools.get(tool_name)

    def list_tools(self) -> List[BaseTool]:
        """Return all registered tool instances."""
        return list(self._tools.values())

    def list_schemas(self) -> List[ToolSchema]:
        """Return all tool schemas (metadata only, no callable references)."""
        return [tool.schema for tool in self._tools.values()]

    def get_tool_descriptions(self) -> str:
        """
        Build a formatted string of tool names and descriptions for injection
        into LLM system prompts.

        Format (one tool per line):
            web_search: Search the web for current information.
              Parameters: {"query": "string (required)", ...}
        """
        if not self._tools:
            return "No tools are currently registered."

        lines: List[str] = []
        for tool in self._tools.values():
            param_desc = str(tool.schema.parameters) if tool.schema.parameters else "{}"
            lines.append(f"{tool.name}: {tool.description}")
            lines.append(f"  Parameters: {param_desc}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def execute(self, tool_call: ToolCall) -> ToolResult:
        """
        Execute a tool by name with the given parameters.

        Wraps all tool errors into a failed ToolResult so the ReAct loop
        can observe and recover gracefully rather than crashing.

        Args:
            tool_call: ToolCall domain model with tool_name and parameters.

        Returns:
            ToolResult with success=True on completion, success=False on error.
        """
        logger.info(
            "tool_execution_start",
            tool=tool_call.tool_name,
            call_id=tool_call.call_id,
        )
        try:
            tool = self.get_tool(tool_call.tool_name)
            raw_output: Any = await tool.execute(**tool_call.parameters)
            output = str(raw_output) if not isinstance(raw_output, str) else raw_output
            logger.info(
                "tool_execution_success",
                tool=tool_call.tool_name,
                call_id=tool_call.call_id,
                output_length=len(output),
            )
            return ToolResult(
                call_id=tool_call.call_id,
                tool_name=tool_call.tool_name,
                output=output,
                success=True,
            )
        except Exception as exc:
            logger.error(
                "tool_execution_error",
                tool=tool_call.tool_name,
                call_id=tool_call.call_id,
                error=str(exc),
            )
            return ToolResult(
                call_id=tool_call.call_id,
                tool_name=tool_call.tool_name,
                output="",
                error=str(exc),
                success=False,
            )
