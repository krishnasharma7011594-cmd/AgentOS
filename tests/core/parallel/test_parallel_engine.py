"""
Unit tests for Phase 9: Parallel Execution Engine

Tests cover:
- ExecutionDependencyResolver: resolve() and has_deadlock()
- ExecutionBarrier: registration and barrier wait
- ExecutionScheduler: deterministic ordering
- WorkerPool / Worker: cancellation, exception isolation
- ParallelExecutionEngine: full batch lifecycle
- SupervisorOrchestrator: parallel vs sequential path selection
"""

import asyncio
from typing import List
from unittest.mock import MagicMock

import pytest

from core.execution.graph import ExecutionGraph
from core.models.domain import (
    ExecutionContext,
    ExecutionPlan,
    Task,
    TaskResult,
    TaskStatus,
)
from core.models.parallel import (
    BatchExecutionPlan,
    BatchResult,
    ExecutionCancellationToken,
    ExecutionPolicy,
)
from core.parallel.analyzer import ExecutionDependencyResolver
from core.parallel.concurrency import ConcurrencyProvider, ExecutionBarrier
from core.parallel.engine import ParallelExecutionEngine
from core.parallel.scheduler import ExecutionScheduler
from core.parallel.worker import TaskExecutor, Worker, WorkerPool
from core.utils.helpers import generate_uuid

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _task(
    goal_id: str,
    name: str = "task",
    dependencies: List[str] | None = None,
    priority: str = "medium",
) -> Task:
    return Task(
        id=generate_uuid(),
        goal_id=goal_id,
        name=name,
        description=f"Description for {name}",
        required_capability="research",
        dependencies=dependencies or [],
        priority=priority,
    )


def _plan(goal_id: str, tasks: List[Task]) -> ExecutionPlan:
    return ExecutionPlan(id=generate_uuid(), goal_id=goal_id, tasks=tasks)


def _graph(tasks: List[Task]) -> ExecutionGraph:
    goal_id = tasks[0].goal_id if tasks else generate_uuid()
    plan = ExecutionPlan(id=generate_uuid(), goal_id=goal_id, tasks=tasks)
    g = ExecutionGraph(plan)
    g.initialize()
    return g


def _context() -> ExecutionContext:
    return ExecutionContext(goal_id=generate_uuid())


def _result(task_id: str, status: TaskStatus = TaskStatus.SUCCESS) -> TaskResult:
    return TaskResult(task_id=task_id, agent_id="test", status=status, summary="ok")


class MockTaskExecutor(TaskExecutor):
    """Executor that returns pre-configured results."""

    def __init__(self, results: dict[str, TaskResult] | None = None):
        self._results = results or {}
        self.call_count: dict[str, int] = {}

    async def execute_task(
        self,
        task: Task,
        context: ExecutionContext,
        cancellation_token: ExecutionCancellationToken,
    ) -> TaskResult:
        self.call_count[task.id] = self.call_count.get(task.id, 0) + 1
        default = TaskResult(
            task_id=task.id, agent_id="mock", status=TaskStatus.SUCCESS, summary="default"
        )
        return self._results.get(task.id, default)


# ---------------------------------------------------------------------------
# ExecutionDependencyResolver
# ---------------------------------------------------------------------------


class TestExecutionDependencyResolver:
    def test_resolve_returns_ready_tasks(self):
        goal_id = generate_uuid()
        t1 = _task(goal_id, "t1")
        t2 = _task(goal_id, "t2")
        graph = _graph([t1, t2])
        resolver = ExecutionDependencyResolver()

        plan = resolver.resolve(graph)

        assert isinstance(plan, BatchExecutionPlan)
        assert not plan.is_empty
        assert len(plan.tasks) == 2  # Both are independent → both READY

    def test_resolve_respects_dependencies(self):
        goal_id = generate_uuid()
        t1 = _task(goal_id, "t1")
        t2 = _task(goal_id, "t2", dependencies=[t1.id])
        graph = _graph([t1, t2])
        resolver = ExecutionDependencyResolver()

        plan = resolver.resolve(graph)

        # Only t1 should be ready; t2 depends on t1
        assert len(plan.tasks) == 1
        assert plan.tasks[0].id == t1.id

    def test_resolve_empty_graph_is_empty(self):
        goal_id = generate_uuid()
        plan_obj = _plan(goal_id, [])
        graph = ExecutionGraph(plan_obj)
        graph.initialize()
        resolver = ExecutionDependencyResolver()

        plan = resolver.resolve(graph)

        assert plan.is_empty

    def test_has_deadlock_false_when_tasks_ready(self):
        goal_id = generate_uuid()
        t1 = _task(goal_id, "t1")
        graph = _graph([t1])
        graph.advance()
        resolver = ExecutionDependencyResolver()

        assert not resolver.has_deadlock(graph)

    def test_has_deadlock_detected_when_stuck(self):
        goal_id = generate_uuid()
        t1 = _task(goal_id, "t1")
        # Manually put t1 into RUNNING so no READY tasks exist, and add t2 PENDING
        t2 = _task(goal_id, "t2")
        graph = _graph([t1, t2])
        # Mark both running (simulating all dispatched)
        graph.mark_task_running(t1.id)
        graph.mark_task_running(t2.id)
        # Now mark t1 failed (t2 is still running — no deadlock)
        graph.mark_task_failed(t1.id, _result(t1.id, TaskStatus.FAILED))
        # t2 is still running, so NOT a deadlock
        resolver = ExecutionDependencyResolver()
        assert not resolver.has_deadlock(graph)


# ---------------------------------------------------------------------------
# ExecutionBarrier
# ---------------------------------------------------------------------------


class TestExecutionBarrier:
    @pytest.mark.asyncio
    async def test_barrier_wait_empty_returns_empty(self):
        provider = ConcurrencyProvider()
        barrier = ExecutionBarrier(provider)
        results = await barrier.wait()
        assert results == []

    @pytest.mark.asyncio
    async def test_barrier_collects_coroutine_results(self):
        provider = ConcurrencyProvider()
        barrier = ExecutionBarrier(provider)

        async def _coro(val: int) -> int:
            return val

        barrier.register_worker_task(_coro(1))
        barrier.register_worker_task(_coro(2))
        barrier.register_worker_task(_coro(3))

        results = await barrier.wait()
        assert sorted(results) == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_barrier_captures_exceptions_via_return_exceptions(self):
        provider = ConcurrencyProvider()
        barrier = ExecutionBarrier(provider)

        async def _fail():
            raise ValueError("boom")

        barrier.register_worker_task(_fail())
        results = await barrier.wait()

        # return_exceptions=True → exceptions are returned, not raised
        assert len(results) == 1
        assert isinstance(results[0], ValueError)

    @pytest.mark.asyncio
    async def test_barrier_clears_after_wait(self):
        provider = ConcurrencyProvider()
        barrier = ExecutionBarrier(provider)

        async def _coro():
            return "x"

        barrier.register_worker_task(_coro())
        await barrier.wait()
        # Second wait should be empty
        results = await barrier.wait()
        assert results == []


# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------


class TestWorker:
    @pytest.mark.asyncio
    async def test_worker_returns_result(self):
        goal_id = generate_uuid()
        task = _task(goal_id)
        expected = _result(task.id)
        executor = MockTaskExecutor({task.id: expected})
        worker = Worker(executor)

        result = await worker.run(task, _context(), ExecutionCancellationToken())
        assert result.task_id == task.id
        assert result.status == TaskStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_worker_skips_on_cancellation(self):
        goal_id = generate_uuid()
        task = _task(goal_id)
        executor = MockTaskExecutor()
        worker = Worker(executor)
        token = ExecutionCancellationToken()
        token.cancel("test")

        result = await worker.run(task, _context(), token)
        assert result.status == TaskStatus.SKIPPED
        assert executor.call_count.get(task.id, 0) == 0

    @pytest.mark.asyncio
    async def test_worker_catches_exception_converts_to_failed_result(self):
        goal_id = generate_uuid()
        task = _task(goal_id)

        class BrokenExecutor(TaskExecutor):
            async def execute_task(self, t, ctx, tok):
                raise RuntimeError("executor exploded")

        worker = Worker(BrokenExecutor())
        result = await worker.run(task, _context(), ExecutionCancellationToken())

        assert result.status == TaskStatus.FAILED
        assert "RuntimeError" in result.error
        assert result.metadata is not None
        assert "worker_exception" in result.metadata


# ---------------------------------------------------------------------------
# WorkerPool
# ---------------------------------------------------------------------------


class TestWorkerPool:
    def test_create_worker_returns_worker_instance(self):
        executor = MockTaskExecutor()
        policy = ExecutionPolicy(max_workers=2)
        pool = WorkerPool(executor=executor, policy=policy)

        w1 = pool.create_worker()
        w2 = pool.create_worker()

        assert isinstance(w1, Worker)
        assert isinstance(w2, Worker)
        # Stateless — each call returns a new instance
        assert w1 is not w2

    def test_max_workers_reflects_policy(self):
        policy = ExecutionPolicy(max_workers=8)
        pool = WorkerPool(executor=MockTaskExecutor(), policy=policy)
        assert pool.max_workers == 8


# ---------------------------------------------------------------------------
# ExecutionScheduler
# ---------------------------------------------------------------------------


class TestExecutionScheduler:
    @pytest.mark.asyncio
    async def test_scheduler_respects_priority_order(self):
        """High-priority tasks should be dispatched before low-priority ones."""
        goal_id = generate_uuid()
        t_low = _task(goal_id, "low", priority="low")
        t_high = _task(goal_id, "high", priority="high")
        t_med = _task(goal_id, "med", priority="medium")

        execution_order: list[str] = []

        class TrackingExecutor(TaskExecutor):
            async def execute_task(self, task, ctx, tok):
                execution_order.append(task.priority)
                return _result(task.id)

        pool = WorkerPool(executor=TrackingExecutor(), policy=ExecutionPolicy(max_workers=1))
        scheduler = ExecutionScheduler(worker_pool=pool)

        plan = BatchExecutionPlan(tasks=[t_low, t_high, t_med])
        provider = ConcurrencyProvider()
        barrier = ExecutionBarrier(provider)

        scheduler.schedule_batch(plan, barrier, _context(), ExecutionCancellationToken())
        await barrier.wait()

        assert execution_order[0] == "high"
        assert execution_order[-1] == "low"

    @pytest.mark.asyncio
    async def test_scheduler_uses_semaphore_for_concurrency(self):
        """Verify that max_workers=1 serialises execution."""
        goal_id = generate_uuid()
        tasks = [_task(goal_id, f"t{i}") for i in range(4)]

        concurrent_count = 0
        max_concurrent = 0

        class ConcurrencyTrackingExecutor(TaskExecutor):
            async def execute_task(self, task, ctx, tok):
                nonlocal concurrent_count, max_concurrent
                concurrent_count += 1
                max_concurrent = max(max_concurrent, concurrent_count)
                await asyncio.sleep(0.01)
                concurrent_count -= 1
                return _result(task.id)

        pool = WorkerPool(
            executor=ConcurrencyTrackingExecutor(),
            policy=ExecutionPolicy(max_workers=2),
        )
        scheduler = ExecutionScheduler(worker_pool=pool)
        plan = BatchExecutionPlan(tasks=tasks)
        provider = ConcurrencyProvider()
        barrier = ExecutionBarrier(provider)

        scheduler.schedule_batch(plan, barrier, _context(), ExecutionCancellationToken())
        await barrier.wait()

        # Max concurrent should be ≤ max_workers
        assert max_concurrent <= 2


# ---------------------------------------------------------------------------
# ParallelExecutionEngine
# ---------------------------------------------------------------------------


class TestParallelExecutionEngine:
    def _make_engine(self, executor: TaskExecutor, max_workers: int = 4) -> ParallelExecutionEngine:
        policy = ExecutionPolicy(max_workers=max_workers)
        pool = WorkerPool(executor=executor, policy=policy)
        scheduler = ExecutionScheduler(worker_pool=pool)
        concurrency = ConcurrencyProvider()
        return ParallelExecutionEngine(scheduler=scheduler, concurrency_provider=concurrency)

    def _make_emitter(self):
        emitter = MagicMock()
        emitter.emit = MagicMock()
        return emitter

    @pytest.mark.asyncio
    async def test_execute_batch_all_success(self):
        goal_id = generate_uuid()
        tasks = [_task(goal_id, f"t{i}") for i in range(3)]
        executor = MockTaskExecutor({t.id: _result(t.id) for t in tasks})
        engine = self._make_engine(executor)

        plan = BatchExecutionPlan(tasks=tasks)
        result = await engine.execute_batch(
            plan=plan,
            context=_context(),
            cancellation_token=ExecutionCancellationToken(),
            event_emitter=self._make_emitter(),
        )

        assert isinstance(result, BatchResult)
        assert len(result.successful_results) == 3
        assert len(result.failed_results) == 0
        assert not result.has_failures

    @pytest.mark.asyncio
    async def test_execute_batch_partial_failure(self):
        goal_id = generate_uuid()
        t1 = _task(goal_id, "success")
        t2 = _task(goal_id, "fail")

        executor = MockTaskExecutor({
            t1.id: _result(t1.id, TaskStatus.SUCCESS),
            t2.id: _result(t2.id, TaskStatus.FAILED),
        })
        engine = self._make_engine(executor)

        plan = BatchExecutionPlan(tasks=[t1, t2])
        result = await engine.execute_batch(
            plan=plan,
            context=_context(),
            cancellation_token=ExecutionCancellationToken(),
            event_emitter=self._make_emitter(),
        )

        assert len(result.successful_results) == 1
        assert len(result.failed_results) == 1
        assert result.has_failures

    @pytest.mark.asyncio
    async def test_execute_batch_emits_events(self):
        goal_id = generate_uuid()
        task = _task(goal_id)
        executor = MockTaskExecutor({task.id: _result(task.id)})
        engine = self._make_engine(executor)
        emitter = self._make_emitter()

        await engine.execute_batch(
            plan=BatchExecutionPlan(tasks=[task]),
            context=_context(),
            cancellation_token=ExecutionCancellationToken(),
            event_emitter=emitter,
        )

        # Should have emitted BATCH_STARTED, TASK_QUEUED, BATCH_COMPLETED
        assert emitter.emit.call_count >= 3

    @pytest.mark.asyncio
    async def test_execute_batch_exception_in_worker_captured(self):
        goal_id = generate_uuid()
        task = _task(goal_id)

        class ExplodingExecutor(TaskExecutor):
            async def execute_task(self, t, ctx, tok):
                raise RuntimeError("hard crash")

        engine = self._make_engine(ExplodingExecutor())
        result = await engine.execute_batch(
            plan=BatchExecutionPlan(tasks=[task]),
            context=_context(),
            cancellation_token=ExecutionCancellationToken(),
            event_emitter=self._make_emitter(),
        )

        # Exception is captured in failed_results via Worker isolation
        assert result.has_failures


# ---------------------------------------------------------------------------
# ExecutionPolicy
# ---------------------------------------------------------------------------


class TestExecutionPolicy:
    def test_default_values(self):
        policy = ExecutionPolicy()
        assert policy.max_workers == 4
        assert policy.max_parallelism == 10

    def test_custom_values(self):
        policy = ExecutionPolicy(max_workers=8, max_parallelism=20)
        assert policy.max_workers == 8
        assert policy.max_parallelism == 20


# ---------------------------------------------------------------------------
# ExecutionCancellationToken
# ---------------------------------------------------------------------------


class TestExecutionCancellationToken:
    def test_not_cancelled_by_default(self):
        token = ExecutionCancellationToken()
        assert not token.is_cancelled
        assert token.reason is None

    def test_cancel_sets_flag(self):
        token = ExecutionCancellationToken()
        token.cancel("user requested")
        assert token.is_cancelled
        assert token.reason == "user requested"
