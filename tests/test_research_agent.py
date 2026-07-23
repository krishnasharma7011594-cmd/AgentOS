"""Tests for ResearchAgent ReAct lifecycle and tool usage."""

import pytest

from agents.research.agent import ResearchAgent
from core.models.domain import Task, TaskStatus
from core.tools.registry import ToolRegistry
from core.utils.helpers import generate_uuid
from tests.test_llm_provider import MockLLMProvider


@pytest.mark.asyncio
async def test_research_agent_execution_with_react() -> None:
    answer_text = (
        "Thought: I know this.\nFinal Answer: LangGraph enables multi-agent state machines."
    )
    provider = MockLLMProvider(answer_text)
    registry = ToolRegistry()
    agent = ResearchAgent(llm_provider=provider, tool_registry=registry)

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
async def test_research_agent_tool_registration() -> None:
    provider = MockLLMProvider("Thought: Done\nFinal Answer: Summary")
    agent = ResearchAgent(llm_provider=provider)

    task = Task(
        id=generate_uuid(),
        goal_id=generate_uuid(),
        name="Test Tool Setup",
        description="Test description",
        required_capability="web_research",
    )

    await agent.execute_task(task)
    assert agent.tool_registry.get("web_search") is not None


@pytest.mark.asyncio
async def test_research_agent_missing_provider() -> None:
    agent = ResearchAgent(llm_provider=None)
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
