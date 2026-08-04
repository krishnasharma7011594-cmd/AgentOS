"""Tests for Tools."""

import pytest

from core.models.capability import CapabilityRequest, CapabilityDescriptor, ResolvedCapability, CapabilityMetadata, CapabilityVersion
from core.models.tool import ToolExecutionContext
from core.tools.implementations.web_search import WebSearchTool


@pytest.mark.asyncio
async def test_web_search_tool_execution() -> None:
    tool = WebSearchTool()
    version = CapabilityVersion(major=1, minor=0, patch=0)
    meta = CapabilityMetadata(name="web_search", version=version, description="Search")
    desc = CapabilityDescriptor(metadata=meta)
    
    context = ToolExecutionContext(
        execution_id="test",
        request=CapabilityRequest(capability_name="web_search", parameters={}),
        capability=ResolvedCapability(
            request=CapabilityRequest(capability_name="web_search", parameters={}),
            descriptor=desc,
            tool_name="web_search",
            tool_version=version
        ),
        agent_id="test"
    )
    result = await tool.execute(context=context, query="Python programming", max_results=2)
    assert isinstance(result, str)
    assert len(result) > 0
