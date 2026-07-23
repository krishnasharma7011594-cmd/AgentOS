"""Tests for SupervisorPlanner — deterministic capability inference."""

import pytest

from core.models.domain import Goal
from core.utils.helpers import generate_uuid
from supervisor.planner import SupervisorPlanner, _infer_capability


def make_goal(description: str) -> Goal:
    return Goal(id=generate_uuid(), description=description)


def test_infer_capability_web_research() -> None:
    assert _infer_capability("Research LangGraph") == "web_research"
    assert _infer_capability("Explain what transformers are") == "web_research"
    assert _infer_capability("What is RAG?") == "web_research"
    assert _infer_capability("Tell me about FastAPI") == "web_research"


def test_infer_capability_summarization() -> None:
    assert _infer_capability("Summarize this document") == "summarization"
    assert _infer_capability("Give me a summary of the paper") == "summarization"


def test_infer_capability_documentation() -> None:
    assert _infer_capability("Look up documentation for Pydantic") == "documentation_lookup"
    assert _infer_capability("Show me the docs for FastAPI") == "documentation_lookup"


def test_infer_capability_default() -> None:
    # Unrecognized keywords → default to web_research
    assert _infer_capability("42 is the answer") == "web_research"


@pytest.mark.asyncio
async def test_planner_creates_plan() -> None:
    planner = SupervisorPlanner()
    goal = make_goal("Research LangGraph")
    plan = await planner.create_plan(goal)

    assert plan.goal_id == goal.id
    assert len(plan.tasks) == 1
    assert plan.tasks[0].required_capability == "web_research"
    assert plan.tasks[0].priority == "high"


@pytest.mark.asyncio
async def test_planner_empty_goal_raises() -> None:
    from core.exceptions.base import PlanningError

    planner = SupervisorPlanner()
    goal = make_goal("   ")
    with pytest.raises(PlanningError):
        await planner.create_plan(goal)
