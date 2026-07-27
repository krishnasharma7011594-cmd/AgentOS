"""Tests for Adaptive Supervisor Orchestrator — decision flow integration (Phase 5)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.models.domain import (
    ExecutionPlan,
    Goal,
    Task,
    TaskResult,
    TaskStatus,
    ValidationResult,
)
from supervisor.orchestrator import SupervisorOrchestrator
from supervisor.policies import RetryPolicy

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _goal(description: str = "Test goal") -> Goal:
    return Goal(id=str(uuid.uuid4()), description=description)


def _task(goal_id: str, task_id: str = "t1", capability: str = "web_research") -> Task:
    return Task(
        id=task_id,
        goal_id=goal_id,
        name=f"Task {task_id}",
        description="Do the thing",
        required_capability=capability,
    )


def _task_result(task_id: str, status: TaskStatus, error: str | None = None) -> TaskResult:
    return TaskResult(
        task_id=task_id,
        agent_id="agent1",
        status=status,
        summary=(
            "Result summary with enough content to be valid."
            if status == TaskStatus.SUCCESS
            else ""
        ),
        error=error,
    )


def _make_plan(tasks: list[Task], goal_id: str) -> ExecutionPlan:
    return ExecutionPlan(id=str(uuid.uuid4()), goal_id=goal_id, tasks=tasks)


def _make_orchestrator(
    plan: ExecutionPlan,
    router_side_effects: list[TaskResult],
    retry_policy: RetryPolicy | None = None,
) -> SupervisorOrchestrator:
    """Build a fully mocked SupervisorOrchestrator for integration tests."""
    planner = MagicMock()
    planner.create_plan = AsyncMock(return_value=plan)
    planner.create_recovery_tasks = AsyncMock(return_value=[])

    router = MagicMock()
    router.route_task = AsyncMock(side_effect=router_side_effects)

    validator = MagicMock()
    validator.validate_plan = MagicMock(return_value=MagicMock(is_valid=True, errors=[]))
    validator.validate_result = AsyncMock(
        return_value=ValidationResult(task_id="t1", is_valid=True, reason="ok")
    )

    report_generator = MagicMock()
    from core.models.domain import ExecutionResult

    report_generator.generate_report = AsyncMock(
        return_value=ExecutionResult(
            goal_id=plan.goal_id,
            status="success",
            response="Done.",
            tasks=router_side_effects,
        )
    )

    return SupervisorOrchestrator(
        agent_registry=MagicMock(),
        capability_registry=MagicMock(),
        planner=planner,
        router=router,
        validator=validator,
        report_generator=report_generator,
        retry_policy=retry_policy or RetryPolicy(),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAdaptiveOrchestratorContinue:
    @pytest.mark.asyncio
    async def test_single_success_task_continues(self) -> None:
        goal = _goal()
        task = _task(goal.id, "t1")
        plan = _make_plan([task], goal.id)

        result = _task_result("t1", TaskStatus.SUCCESS)
        orchestrator = _make_orchestrator(plan, [result])

        outcome = await orchestrator.execute_goal(goal)
        assert outcome.status == "success"


class TestAdaptiveOrchestratorRetry:
    @pytest.mark.asyncio
    async def test_timeout_failure_triggers_retry_then_success(self) -> None:
        goal = _goal()
        task = _task(goal.id, "t1")
        plan = _make_plan([task], goal.id)

        fail = _task_result("t1", TaskStatus.FAILED, error="connection timeout exceeded")
        success = _task_result("t1", TaskStatus.SUCCESS)

        # Fail first, succeed on retry
        orchestrator = _make_orchestrator(plan, [fail, success])
        outcome = await orchestrator.execute_goal(goal)
        assert outcome.status == "success"
        mock_router = orchestrator.router.route_task
        assert hasattr(mock_router, "call_count")
        assert mock_router.call_count == 2


class TestAdaptiveOrchestratorSkip:
    @pytest.mark.asyncio
    async def test_capability_unavailable_causes_skip(self) -> None:
        goal = _goal()
        task = _task(goal.id, "t1")
        plan = _make_plan([task], goal.id)

        fail = _task_result(
            "t1", TaskStatus.FAILED, error="capability unavailable for this request"
        )

        orchestrator = _make_orchestrator(
            plan, [fail], retry_policy=RetryPolicy(max_retries_by_category={})
        )
        await orchestrator.execute_goal(goal)
        # Router called exactly once — no retries for CAPABILITY_UNAVAILABLE
        mock_router = orchestrator.router.route_task
        assert hasattr(mock_router, "call_count")
        assert mock_router.call_count == 1


class TestAdaptiveOrchestratorMetrics:
    @pytest.mark.asyncio
    async def test_retry_is_recorded_in_metrics(self) -> None:
        """Verify that retry events are recorded (through the orchestrator executing twice)."""
        goal = _goal()
        task = _task(goal.id, "t1")
        plan = _make_plan([task], goal.id)

        fail = _task_result("t1", TaskStatus.FAILED, error="timeout")
        success = _task_result("t1", TaskStatus.SUCCESS)

        orchestrator = _make_orchestrator(plan, [fail, success])
        await orchestrator.execute_goal(goal)

        # Two calls = original + 1 retry
        mock_router = orchestrator.router.route_task
        assert hasattr(mock_router, "call_count")
        assert mock_router.call_count == 2
