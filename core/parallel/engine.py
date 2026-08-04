"""
Parallel Execution Engine

The core orchestrator for parallel batch execution.
Coordinates the Scheduler, Barrier, and Concurrency provider to execute
an immutable BatchExecutionPlan safely and deterministically.

Architecture Layer: Core / Parallel
"""

from typing import List

from core.execution.events import EventEmitter
from core.models.domain import EventType, ExecutionContext, TaskResult
from core.models.parallel import (
    BatchExecutionPlan,
    BatchResult,
    BatchStatus,
    ExecutionBatch,
    ExecutionCancellationToken,
)
from core.parallel.concurrency import ConcurrencyProvider, ExecutionBarrier
from core.parallel.scheduler import ExecutionScheduler


class ParallelExecutionEngine:
    """
    Facade for executing a batch of independent tasks concurrently.
    """

    def __init__(
        self,
        scheduler: ExecutionScheduler,
        concurrency_provider: ConcurrencyProvider,
    ):
        self._scheduler = scheduler
        self._concurrency = concurrency_provider

    async def execute_batch(
        self,
        plan: BatchExecutionPlan,
        context: ExecutionContext,
        cancellation_token: ExecutionCancellationToken,
        event_emitter: EventEmitter,
    ) -> BatchResult:
        """
        Executes an immutable batch plan concurrently.

        Args:
            plan: The immutable BatchExecutionPlan containing ready tasks.
            cancellation_token: Token to cooperatively cancel tasks.

        Returns:
            A BatchResult containing successful results, failed results, and exceptions.
        """
        batch = ExecutionBatch(plan=plan, status=BatchStatus.RUNNING)

        event_emitter.emit(
            EventType.BATCH_STARTED,
            details=f"Starting batch {batch.id} with {len(plan.tasks)} tasks.",
        )

        for task in plan.tasks:
            event_emitter.emit(
                EventType.TASK_QUEUED, task_id=task.id, details=f"Task queued in batch {batch.id}."
            )

        barrier = ExecutionBarrier(self._concurrency)

        # Scheduler assigns tasks to workers and registers them with the barrier
        self._scheduler.schedule_batch(plan, barrier, context, cancellation_token)

        # Wait for all workers to finish
        raw_results = await barrier.wait()

        # Collect and partition results
        successful_results: List[TaskResult] = []
        failed_results: List[TaskResult] = []
        exceptions = []

        for res in raw_results:
            if isinstance(res, Exception):
                # A hard crash that escaped the Worker's try-except block (should be rare)
                import traceback

                from core.models.parallel import WorkerException

                tb = "".join(traceback.format_exception(type(res), res, res.__traceback__))
                we = WorkerException(
                    task_id="unknown",
                    error_type=res.__class__.__name__,
                    message=str(res),
                    traceback_str=tb,
                )
                exceptions.append(we)
            elif isinstance(res, TaskResult):
                if res.status.value == "success":
                    successful_results.append(res)
                else:
                    failed_results.append(res)
                    # Check if the failure was a WorkerException payload
                    if res.metadata and "worker_exception" in res.metadata:
                        from core.models.parallel import WorkerException

                        exceptions.append(WorkerException(**res.metadata["worker_exception"]))

        batch_result = BatchResult(
            batch_id=batch.id,
            successful_results=successful_results,
            failed_results=failed_results,
            exceptions=exceptions,
        )

        batch.status = BatchStatus.FAILED if batch_result.has_failures else BatchStatus.COMPLETED
        batch.result = batch_result

        from datetime import datetime, timezone

        batch.completed_at = datetime.now(timezone.utc)

        event_type = (
            EventType.BATCH_FAILED if batch_result.has_failures else EventType.BATCH_COMPLETED
        )
        event_emitter.emit(
            event_type,
            details=(
                f"Batch {batch.id} finished:"
                f" {len(successful_results)} success, {len(failed_results)} failed."
            ),
        )

        return batch_result
