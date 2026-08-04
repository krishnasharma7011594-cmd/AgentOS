"""Tests for ResearchAgent ReAct lifecycle and tool usage."""

import pytest

from agents.research.agent import ResearchAgent
from core.models.domain import Task, TaskStatus
from core.utils.helpers import generate_uuid
from tests.test_llm_provider import MockLLMProvider
from core.tools.engine import CapabilityEngine
from registry.capability_registry import CapabilityRegistry
from core.tools.permissions import PermissionManager
from core.tools.resolver import CapabilityResolver
from core.tools.executor import CapabilityExecutor
from core.tools.sandbox import ToolSandbox
from core.tools.resources import ResourceManager
from core.tools.tool_registry import ToolRegistry


@pytest.mark.asyncio
async def test_research_agent_execution_with_react() -> None:
    answer_text = (
        "Thought: I know this.\nFinal Answer: LangGraph enables multi-agent state machines."
    )
    provider = MockLLMProvider(answer_text)
    cap_reg = CapabilityRegistry()
    tool_reg = ToolRegistry()
    perm_mgr = PermissionManager()
    res_mgr = ResourceManager()
    resolver = CapabilityResolver(cap_reg, tool_reg)
    sandbox = ToolSandbox()
    executor = CapabilityExecutor(tool_reg, res_mgr, sandbox)
    cap_engine = CapabilityEngine(cap_reg, perm_mgr, resolver, executor)

    agent = ResearchAgent(llm_provider=provider, capability_engine=cap_engine)

    task = Task(
        id=generate_uuid(),
        goal_id=generate_uuid(),
        name="Research LangGraph",
        description="Explain LangGraph features",
        required_capability="web_research",
    )

    result = await agent.execute_task(task)

    assert result.task_id == task.id
    assert result.status == TaskStatus.SUCCESS
    assert "LangGraph" in result.summary
    assert "reasoning_steps" in result.metadata
    assert result.metadata["total_steps"] == 1

@pytest.mark.asyncio
async def test_research_agent_missing_provider() -> None:
    agent = ResearchAgent(llm_provider=None, capability_engine=None)
    task = Task(
        id=generate_uuid(),
        goal_id=generate_uuid(),
        name="Test",
        description="Test description",
        required_capability="web_research",
    )

    result = await agent.execute_task(task)

    assert result.status == TaskStatus.FAILED
    assert "No LLM provider" in (result.error or "")
