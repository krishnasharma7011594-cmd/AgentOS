"""Tests for ExecutionGraph.apply_mutation and mark_task_ready (Phase 5)."""

import uuid

import pytest

from core.execution.graph import ExecutionGraph, InvalidTaskTransitionError
from core.models.domain import ExecutionPlan, Goal, GraphMutation, Task, TaskResult, TaskStatus


def _goal() -> Goal:
    return Goal(id=str(uuid.uuid4()), description="Graph mutation test")


def _task(task_id: str, goal_id: str, deps: list[str] | None = None) -> Task:
    return Task(
        id=task_id,
        goal_id=goal_id,
        name=f"Task {task_id}",
        description=f"Desc {task_id}",
        required_capability="web_research",
        dependencies=deps or [],
    )


def _result(task_id: str, status: TaskStatus = TaskStatus.SUCCESS) -> TaskResult:
    return TaskResult(
        task_id=task_id,
        agent_id="agent1",
        status=status,
        summary="done",
    )


def _plan(tasks: list[Task], goal_id: str) -> ExecutionPlan:
    return ExecutionPlan(id=str(uuid.uuid4()), goal_id=goal_id, tasks=tasks)


class TestMarkTaskReady:
    def test_failed_task_can_be_re_queued_for_retry(self) -> None:
        goal = _goal()
        t1 = _task("t1", goal.id)
        graph = ExecutionGraph(_plan([t1], goal.id))
        graph.initialize()

        graph.mark_task_running("t1")
        graph.mark_task_failed("t1", _result("t1", TaskStatus.FAILED))
        graph.mark_task_ready("t1")

        assert graph.get_status("t1") == TaskStatus.READY

    def test_non_failed_task_raises_on_mark_ready(self) -> None:
        goal = _goal()
        t1 = _task("t1", goal.id)
        graph = ExecutionGraph(_plan([t1], goal.id))
        graph.initialize()

        with pytest.raises(InvalidTaskTransitionError):
            graph.mark_task_ready("t1")  # READY → cannot re-queue


class TestApplyMutation:
    def test_insert_task_before_pending_task(self) -> None:
        goal = _goal()
        t1 = _task("t1", goal.id)
        t2 = _task("t2", goal.id, deps=["t1"])
        graph = ExecutionGraph(_plan([t1, t2], goal.id))
        graph.initialize()

        new_task = _task("tnew", goal.id)
        mutation = GraphMutation(new_tasks=[new_task], before_task_ids=["t2"])
        graph.apply_mutation(mutation)

        # New task should be READY (no deps)
        assert graph.get_status("tnew") == TaskStatus.READY
        # t2 should now depend on tnew
        assert "tnew" in graph._tasks["t2"].dependencies

    def test_empty_mutation_is_noop(self) -> None:
        goal = _goal()
        t1 = _task("t1", goal.id)
        graph = ExecutionGraph(_plan([t1], goal.id))
        graph.initialize()

        mutation = GraphMutation(new_tasks=[], before_task_ids=[])
        graph.apply_mutation(mutation)  # should not raise

        assert graph.task_count == 1

    def test_insert_before_terminal_task_raises(self) -> None:
        goal = _goal()
        t1 = _task("t1", goal.id)
        t2 = _task("t2", goal.id, deps=["t1"])
        graph = ExecutionGraph(_plan([t1, t2], goal.id))
        graph.initialize()

        # Complete t1
        graph.mark_task_running("t1")
        graph.mark_task_success("t1", _result("t1"))
        graph.advance()
        # Complete t2
        graph.mark_task_running("t2")
        graph.mark_task_success("t2", _result("t2"))

        new_task = _task("tnew", goal.id)
        mutation = GraphMutation(new_tasks=[new_task], before_task_ids=["t2"])
        with pytest.raises(ValueError, match="terminal"):
            graph.apply_mutation(mutation)

    def test_circular_dependency_is_rejected(self) -> None:
        goal = _goal()
        t1 = _task("t1", goal.id)
        graph = ExecutionGraph(_plan([t1], goal.id))
        graph.initialize()

        # Create a task that depends on t1, and try to insert it before t1
        circ = _task("tcirc", goal.id, deps=["t1"])
        mutation = GraphMutation(new_tasks=[circ], before_task_ids=["t1"])
        with pytest.raises(ValueError, match="circular"):
            graph.apply_mutation(mutation)

    def test_task_count_increases_after_mutation(self) -> None:
        goal = _goal()
        t1 = _task("t1", goal.id)
        graph = ExecutionGraph(_plan([t1], goal.id))
        graph.initialize()

        new_task = _task("tnew", goal.id)
        mutation = GraphMutation(new_tasks=[new_task], before_task_ids=[])
        graph.apply_mutation(mutation)

        assert graph.task_count == 2
