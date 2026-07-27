"""Tests for ExecutionGraph (Phase 4.5)."""

import uuid

import pytest

from core.execution.graph import ExecutionGraph, InvalidTaskTransitionError
from core.models.domain import ExecutionPlan, Goal, Task, TaskResult, TaskStatus


def _make_goal() -> Goal:
    return Goal(id=str(uuid.uuid4()), description="Test goal")


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


def _make_result(task_id: str, status: TaskStatus, agent_id: str = "Agent1") -> TaskResult:
    return TaskResult(
        task_id=task_id,
        agent_id=agent_id,
        status=status,
        summary="done" if status == TaskStatus.SUCCESS else "",
        error=None if status == TaskStatus.SUCCESS else "err",
    )


def _make_plan(tasks: list[Task], goal: Goal) -> ExecutionPlan:
    return ExecutionPlan(id=str(uuid.uuid4()), goal_id=goal.id, tasks=tasks)


class TestExecutionGraphInitialization:
    def test_tasks_without_deps_are_ready(self) -> None:
        goal = _make_goal()
        tasks = [_make_task("t1", goal.id), _make_task("t2", goal.id)]
        graph = ExecutionGraph(_make_plan(tasks, goal))
        graph.initialize()
        ready = [t.id for t in graph.get_ready_tasks()]
        assert "t1" in ready
        assert "t2" in ready

    def test_tasks_with_deps_start_pending(self) -> None:
        goal = _make_goal()
        t1 = _make_task("t1", goal.id)
        t2 = _make_task("t2", goal.id, dependencies=["t1"])
        graph = ExecutionGraph(_make_plan([t1, t2], goal))
        graph.initialize()
        assert graph.get_status("t2") == TaskStatus.PENDING
        assert graph.get_status("t1") == TaskStatus.READY


class TestExecutionGraphTransitions:
    def test_ready_to_running_to_success(self) -> None:
        goal = _make_goal()
        t1 = _make_task("t1", goal.id)
        graph = ExecutionGraph(_make_plan([t1], goal))
        graph.initialize()

        graph.mark_task_running("t1")
        assert graph.get_status("t1") == TaskStatus.RUNNING

        result = _make_result("t1", TaskStatus.SUCCESS)
        graph.mark_task_success("t1", result)
        assert graph.get_status("t1") == TaskStatus.SUCCESS
        assert graph.get_result("t1") == result

    def test_running_to_failed(self) -> None:
        goal = _make_goal()
        t1 = _make_task("t1", goal.id)
        graph = ExecutionGraph(_make_plan([t1], goal))
        graph.initialize()

        graph.mark_task_running("t1")
        result = _make_result("t1", TaskStatus.FAILED)
        graph.mark_task_failed("t1", result)
        assert graph.get_status("t1") == TaskStatus.FAILED

    def test_invalid_transition_raises(self) -> None:
        goal = _make_goal()
        t1 = _make_task("t1", goal.id)
        graph = ExecutionGraph(_make_plan([t1], goal))
        graph.initialize()
        # Cannot go from READY → SUCCESS without RUNNING
        with pytest.raises(InvalidTaskTransitionError):
            graph.mark_task_success("t1", _make_result("t1", TaskStatus.SUCCESS))


class TestExecutionGraphAdvance:
    def test_dep_success_unlocks_downstream(self) -> None:
        goal = _make_goal()
        t1 = _make_task("t1", goal.id)
        t2 = _make_task("t2", goal.id, dependencies=["t1"])
        graph = ExecutionGraph(_make_plan([t1, t2], goal))
        graph.initialize()

        graph.mark_task_running("t1")
        graph.mark_task_success("t1", _make_result("t1", TaskStatus.SUCCESS))
        graph.advance()

        assert graph.get_status("t2") == TaskStatus.READY

    def test_dep_failure_cascades_to_skipped(self) -> None:
        goal = _make_goal()
        t1 = _make_task("t1", goal.id)
        t2 = _make_task("t2", goal.id, dependencies=["t1"])
        graph = ExecutionGraph(_make_plan([t1, t2], goal))
        graph.initialize()

        graph.mark_task_running("t1")
        graph.mark_task_failed("t1", _make_result("t1", TaskStatus.FAILED))
        graph.advance()

        assert graph.get_status("t2") == TaskStatus.SKIPPED

    def test_is_complete_when_all_terminal(self) -> None:
        goal = _make_goal()
        t1 = _make_task("t1", goal.id)
        t2 = _make_task("t2", goal.id)
        graph = ExecutionGraph(_make_plan([t1, t2], goal))
        graph.initialize()

        assert not graph.is_complete()

        graph.mark_task_running("t1")
        graph.mark_task_success("t1", _make_result("t1", TaskStatus.SUCCESS))
        graph.mark_task_running("t2")
        graph.mark_task_success("t2", _make_result("t2", TaskStatus.SUCCESS))

        assert graph.is_complete()
