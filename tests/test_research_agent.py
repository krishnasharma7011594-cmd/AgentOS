"""Tests for ResearchAgent."""

import pytest

from agents.research.agent import ResearchAgent
from core.models.domain import Task, TaskStatus
from core.utils.helpers import generate_uuid
from tests.test_llm_provider import MockLLMProvider


@pytest.mark.asyncio
async def test_research_agent_execution() -> None:
    provider = MockLLMProvider("LangGraph enables multi-agent state machines.")
    agent = ResearchAgent(llm_provider=provider)

    task = Task(
        id=generate_uuid(),
        goal_id=generate_uuid(),
        name="Research LangGraph",
        description="Explain LangGraph features",
        required_capability="web_research",
    )

    result = await agent.execute_task(task)

    assert result.task_id == task.id
    assert result.agent_id == "ResearchAgent"
    assert result.status == TaskStatus.SUCCESS
    assert "LangGraph" in result.summary
    assert result.metadata["capability_used"] == "web_research"


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
