"""Tests for SupervisorValidator.validate_plan (Phase 4.5)."""

import uuid

import pytest

from core.models.domain import ExecutionPlan, Goal, Task, TaskStatus
from supervisor.validator import SupervisorValidator


def _make_goal() -> Goal:
    return Goal(id=str(uuid.uuid4()), description="Plan validation test goal")


def _make_task(
    task_id: str,
    goal_id: str,
    dependencies: list[str] | None = None,
    capability: str = "research",
) -> Task:
    return Task(
        id=task_id,
        goal_id=goal_id,
        name=f"Task {task_id}",
        description=f"Task {task_id} description",
        required_capability=capability,
        dependencies=dependencies or [],
    )


def _make_plan(tasks: list[Task], goal: Goal) -> ExecutionPlan:
    return ExecutionPlan(id=str(uuid.uuid4()), goal_id=goal.id, tasks=tasks)


@pytest.fixture
def validator() -> SupervisorValidator:
    return SupervisorValidator(capability_registry=None)


class TestPlanValidation:
    def test_valid_linear_plan(self, validator: SupervisorValidator) -> None:
        goal = _make_goal()
        t1 = _make_task("t1", goal.id)
        t2 = _make_task("t2", goal.id, dependencies=["t1"])
        result = validator.validate_plan(_make_plan([t1, t2], goal))
        assert result.is_valid is True
        assert result.errors == []

    def test_empty_plan_is_invalid(self, validator: SupervisorValidator) -> None:
        goal = _make_goal()
        result = validator.validate_plan(_make_plan([], goal))
        assert result.is_valid is False
        assert any("no tasks" in e.lower() for e in result.errors)

    def test_duplicate_task_ids_are_invalid(self, validator: SupervisorValidator) -> None:
        goal = _make_goal()
        t1a = _make_task("dup", goal.id)
        t1b = _make_task("dup", goal.id)
        result = validator.validate_plan(_make_plan([t1a, t1b], goal))
        assert result.is_valid is False
        assert any("duplicate" in e.lower() for e in result.errors)

    def test_invalid_dependency_reference(self, validator: SupervisorValidator) -> None:
        goal = _make_goal()
        t1 = _make_task("t1", goal.id, dependencies=["nonexistent"])
        result = validator.validate_plan(_make_plan([t1], goal))
        assert result.is_valid is False
        assert any("unknown task" in e.lower() for e in result.errors)

    def test_circular_dependency_detected(self, validator: SupervisorValidator) -> None:
        goal = _make_goal()
        t1 = _make_task("t1", goal.id, dependencies=["t2"])
        t2 = _make_task("t2", goal.id, dependencies=["t1"])
        result = validator.validate_plan(_make_plan([t1, t2], goal))
        assert result.is_valid is False
        assert any("circular" in e.lower() for e in result.errors)

    def test_non_pending_initial_status_flagged(self, validator: SupervisorValidator) -> None:
        goal = _make_goal()
        t1 = _make_task("t1", goal.id)
        t1_modified = t1.model_copy(update={"status": TaskStatus.RUNNING})
        result = validator.validate_plan(_make_plan([t1_modified], goal))
        assert result.is_valid is False
        assert any("unexpected initial status" in e.lower() for e in result.errors)
