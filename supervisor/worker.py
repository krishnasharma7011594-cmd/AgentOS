"""
Supervisor Worker

Implements the TaskExecutor protocol for the ParallelExecutionEngine.
Bridges the parallel concurrency boundary with the SupervisorRouter.
"""

from core.models.domain import ExecutionContext, Task, TaskResult
from core.models.parallel import ExecutionCancellationToken
from core.parallel.worker import TaskExecutor
from supervisor.router import SupervisorRouter


class SupervisorTaskExecutor(TaskExecutor):
    """
    Executes a task by routing it to an agent via the SupervisorRouter.
    """

    def __init__(self, router: SupervisorRouter):
        self._router = router

    async def execute_task(
        self, 
        task: Task, 
        context: ExecutionContext,
        cancellation_token: ExecutionCancellationToken
    ) -> TaskResult:
        """
        Executes a task by routing it.
        Checks for cancellation before and during execution (if router supports it).
        """
        # In the future, router.route_task could accept the cancellation_token
        # to abort long-running LLM calls. For now, we just pass the context.
        return await self._router.route_task(task, context)
