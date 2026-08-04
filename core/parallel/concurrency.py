"""
Concurrency Primitives

Provides abstractions over the underlying async concurrency backend (e.g. asyncio).
Allows AgentOS to run isolated async tasks and synchronize parallel execution batches
without leaking asyncio directly into higher-level execution components.

Architecture Layer: Core / Parallel
"""

import asyncio
from typing import Any, Awaitable, Callable, Coroutine, List


class ConcurrencyProvider:
    """
    Abstracts asyncio functions to keep the concurrency backend replaceable.
    """

    async def gather(
        self, *awaitables: Awaitable[Any], return_exceptions: bool = False
    ) -> List[Any]:
        """Run awaitables concurrently and wait for all to finish."""
        return await asyncio.gather(*awaitables, return_exceptions=return_exceptions)

    async def sleep(self, delay: float) -> None:
        """Non-blocking sleep."""
        await asyncio.sleep(delay)

    def create_task(self, coro: Coroutine[Any, Any, Any]) -> asyncio.Task[Any]:
        """Spawn a background task."""
        return asyncio.create_task(coro)

    def run_in_executor(self, func: Callable[..., Any], *args: Any) -> Awaitable[Any]:
        """Run a synchronous blocking function in a thread pool."""
        loop = asyncio.get_running_loop()
        return loop.run_in_executor(None, func, *args)


class ExecutionBarrier:
    """
    Synchronization primitive scoped strictly to an ExecutionBatch.
    Waits until all workers assigned to the batch have completed.
    """

    def __init__(self, concurrency: ConcurrencyProvider):
        self._concurrency = concurrency
        self._pending_tasks: List[asyncio.Task[Any]] = []

    def register_worker_task(self, coro: Coroutine[Any, Any, Any]) -> None:
        """Register a worker's execution coroutine to be waited upon."""
        task = self._concurrency.create_task(coro)
        self._pending_tasks.append(task)

    async def wait(self) -> List[Any]:
        """
        Wait for all registered worker tasks in the current batch to complete.
        Returns the results from the tasks.
        """
        if not self._pending_tasks:
            return []

        # Wait for all workers to finish. return_exceptions=True prevents
        # a single worker crash from aborting the entire batch wait process.
        results = await self._concurrency.gather(*self._pending_tasks, return_exceptions=True)
        self._pending_tasks.clear()
        return results
