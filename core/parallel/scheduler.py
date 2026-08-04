"""
Execution Scheduler

Assigns ready tasks to available workers from the WorkerPool.
Ensures deterministic ordering and respects execution constraints
(e.g. max_workers).

Architecture Layer: Core / Parallel
"""

from typing import List

from core.models.domain import ExecutionContext, Task, TaskResult
from core.models.parallel import BatchExecutionPlan, ExecutionCancellationToken
from core.parallel.concurrency import ExecutionBarrier
from core.parallel.worker import WorkerPool


class ExecutionScheduler:
    """
    Manages the deterministic assignment of tasks to workers.
    """

    def __init__(self, worker_pool: WorkerPool):
        self._worker_pool = worker_pool

    def _sort_tasks_deterministically(self, tasks: List[Task]) -> List[Task]:
        """
        Sort tasks deterministically to ensure reproducible execution order.
        Sorts primarily by priority (high > medium > low) and secondarily by task ID.
        """
        priority_map = {"high": 0, "medium": 1, "low": 2}
        return sorted(
            tasks,
            key=lambda t: (priority_map.get(t.priority.lower(), 1), t.id)
        )

    def schedule_batch(
        self,
        plan: BatchExecutionPlan,
        barrier: ExecutionBarrier,
        context: ExecutionContext,
        cancellation_token: ExecutionCancellationToken
    ) -> None:
        """
        Takes the tasks from the BatchExecutionPlan, sorts them deterministically,
        and registers their worker execution coroutines with the ExecutionBarrier.

        Note: Concurrency limits (max_workers) could be enforced here using a semaphore
        wrapped around the worker coroutine, or via a bounded queue. For simplicity,
        we register all tasks with a concurrency limiting wrapper.
        """
        sorted_tasks = self._sort_tasks_deterministically(plan.tasks)
        max_workers = self._worker_pool.max_workers

        # To limit concurrency, we could use an asyncio.Semaphore.
        # But we want to hide asyncio. Let's create a wrapper that uses
        # an async semaphore without exposing it in the domain models,
        # or we just rely on the backend via ConcurrencyProvider.
        # Here we just register the coroutines. If max_workers is needed, 
        # we can wrap it. Let's assume the ConcurrencyProvider or the barrier handles it,
        # or we just use asyncio.Semaphore internally here as it's an implementation detail.
        
        import asyncio
        semaphore = asyncio.Semaphore(max_workers)

        async def worker_wrapper(task: Task) -> TaskResult:
            async with semaphore:
                worker = self._worker_pool.create_worker()
                return await worker.run(task, context, cancellation_token)

        for task in sorted_tasks:
            coro = worker_wrapper(task)
            barrier.register_worker_task(coro)
