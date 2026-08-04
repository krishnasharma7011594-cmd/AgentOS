"""
Parallel Workers

Defines the worker abstractions for executing tasks concurrently.
Workers are stateless wrappers around a TaskExecutor. They handle
lifecycle reporting and isolated exception capture.

Architecture Layer: Core / Parallel
"""

import traceback
from abc import ABC, abstractmethod

from core.models.domain import ExecutionContext, Task, TaskResult, TaskStatus
from core.models.parallel import ExecutionCancellationToken, ExecutionPolicy, WorkerException


class TaskExecutor(ABC):
    """
    Abstract interface for executing the actual task payload.
    The ParallelExecutionEngine does not know how to run tasks; it relies on
    an injected TaskExecutor (which might wrap the SupervisorRouter) to do the work.
    """

    @abstractmethod
    async def execute_task(
        self, task: Task, context: ExecutionContext, cancellation_token: ExecutionCancellationToken
    ) -> TaskResult:
        """Execute the task and return its TaskResult."""
        pass


class Worker:
    """
    A stateless isolation wrapper for a TaskExecutor.
    Handles the execution lifecycle, exception capture, and mapping failures to TaskResult.
    """

    def __init__(self, executor: TaskExecutor):
        self._executor = executor

    async def run(
        self, task: Task, context: ExecutionContext, cancellation_token: ExecutionCancellationToken
    ) -> TaskResult:
        """
        Runs the task safely. Any unhandled exception is caught and converted
        into a failed TaskResult containing the WorkerException details.
        """
        if cancellation_token.is_cancelled:
            return TaskResult(
                task_id=task.id,
                agent_id="worker",
                status=TaskStatus.SKIPPED,
                summary="Task cancelled before execution.",
                error="Cancelled",
            )

        try:
            return await self._executor.execute_task(task, context, cancellation_token)
        except Exception as e:
            # Capture isolated exception without crashing the pool
            tb_str = traceback.format_exc()
            worker_exc = WorkerException(
                task_id=task.id,
                error_type=e.__class__.__name__,
                message=str(e),
                traceback_str=tb_str,
            )
            return TaskResult(
                task_id=task.id,
                agent_id="worker",
                status=TaskStatus.FAILED,
                summary="Unhandled worker exception.",
                error=f"{worker_exc.error_type}: {worker_exc.message}",
                # Storing the full WorkerException inside the TaskResult metadata
                # so it can be extracted and aggregated by the FailureCollector/Engine.
                metadata={"worker_exception": worker_exc.model_dump()},
            )


class WorkerPool:
    """
    Manages a pool of workers adhering to the ExecutionPolicy.
    Since Workers are stateless, the pool primarily controls how many
    tasks can be dispatched simultaneously (bounded concurrency).
    """

    def __init__(self, executor: TaskExecutor, policy: ExecutionPolicy):
        self._executor = executor
        self._policy = policy
        # In a fully stateless model, the pool doesn't maintain persistent Worker objects.
        # Instead, it provides a method to acquire a Worker or dispatch a task.

    def create_worker(self) -> Worker:
        """
        Creates a new stateless Worker instance for executing a task.
        """
        return Worker(self._executor)

    @property
    def max_workers(self) -> int:
        return self._policy.max_workers
