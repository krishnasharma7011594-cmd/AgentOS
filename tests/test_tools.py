"""Tests for ToolRegistry and WebSearchTool."""

import pytest

from core.exceptions.base import ToolNotFoundError
from core.models.domain import ToolCall
from core.tools.base import BaseTool
from core.tools.implementations.web_search import WebSearchTool
from core.tools.registry import ToolRegistry


class SampleTool(BaseTool):
    def __init__(self) -> None:
        super().__init__(
            name="sample_tool",
            description="Sample description.",
            parameters={"param": {"type": "string"}},
        )

    async def execute(self, param: str = "", **kwargs) -> str:
        if param == "error":
            raise ValueError("Execution error")
        return f"Executed with {param}"


def test_tool_registry_registration() -> None:
    registry = ToolRegistry()
    tool = SampleTool()
    registry.register(tool)

    assert registry.get("sample_tool") == tool
    assert len(registry.list_tools()) == 1
    assert "sample_tool: Sample description." in registry.get_tool_descriptions()


def test_tool_registry_get_tool_not_found() -> None:
    registry = ToolRegistry()
    with pytest.raises(ToolNotFoundError):
        registry.get_tool("non_existent_tool")


@pytest.mark.asyncio
async def test_tool_registry_execute_success() -> None:
    registry = ToolRegistry()
    registry.register(SampleTool())

    call = ToolCall(tool_name="sample_tool", parameters={"param": "hello"})
    result = await registry.execute(call)

    assert result.success
    assert result.output == "Executed with hello"
    assert result.error is None


@pytest.mark.asyncio
async def test_tool_registry_execute_failure() -> None:
    registry = ToolRegistry()
    registry.register(SampleTool())

    call = ToolCall(tool_name="sample_tool", parameters={"param": "error"})
    result = await registry.execute(call)

    assert not result.success
    assert result.error == "Execution error"


@pytest.mark.asyncio
async def test_web_search_tool_execution() -> None:
    tool = WebSearchTool()
    result = await tool.execute(query="Python programming", max_results=2)
    assert isinstance(result, str)
    assert len(result) > 0
