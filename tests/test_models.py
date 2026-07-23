"""Tests for core domain Pydantic models."""

from core.models.domain import (
    ExecutionResult,
    Goal,
    Message,
    RoleEnum,
    Task,
    TaskResult,
    TaskStatus,
)


def test_domain_models_creation() -> None:
    goal = Goal(id="goal_1", description="Build AgentOS")
    assert goal.id == "goal_1"

    task = Task(
        id="task_1",
        goal_id=goal.id,
        name="Scaffold Monorepo",
        description="Create directory skeleton",
        required_capability="web_research",
    )
    assert task.status == TaskStatus.PENDING

    task_result = TaskResult(
        task_id=task.id,
        agent_id="ResearchAgent",
        status=TaskStatus.SUCCESS,
        summary="Done research",
    )
    assert task_result.status == TaskStatus.SUCCESS

    result = ExecutionResult(
        goal_id=goal.id,
        status="success",
        response="Done",
        tasks=[task_result],
    )
    assert result.status == "success"

    msg = Message(id="msg_1", role=RoleEnum.USER, content="Hello AgentOS")
    assert msg.role == RoleEnum.USER
