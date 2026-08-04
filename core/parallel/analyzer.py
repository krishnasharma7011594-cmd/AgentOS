"""
Execution Dependency Resolver

Analyzes the ExecutionGraph to determine the frontier of ready tasks that can
be executed safely in parallel. Ensures no dependency violations.

Architecture Layer: Core / Parallel
"""


from core.execution.graph import ExecutionGraph
from core.models.domain import TaskStatus
from core.models.parallel import BatchExecutionPlan


class ExecutionDependencyResolver:
    """
    Extracts an immutable snapshot of tasks ready for parallel execution.
    Acts as the bridge between the stateful ExecutionGraph and the ParallelExecutionEngine.
    """

    def resolve(self, graph: ExecutionGraph) -> BatchExecutionPlan:
        """
        Determines the next logical execution batch.

        Args:
            graph: The stateful ExecutionGraph.

        Returns:
            An immutable BatchExecutionPlan containing ready tasks.
        """
        # Graph must be advanced to ensure PENDING tasks whose dependencies
        # are met are promoted to READY, and failed dependencies propagate SKIPPED.
        graph.advance()

        ready_tasks = graph.get_ready_tasks()

        # Build the immutable snapshot
        return BatchExecutionPlan(tasks=ready_tasks)

    def has_deadlock(self, graph: ExecutionGraph) -> bool:
        """
        Detect if the graph is stalled (unresolved dependencies but no ready tasks).
        A true deadlock means there are PENDING tasks, but NO tasks are RUNNING or READY.
        """
        has_pending = any(s == TaskStatus.PENDING for s in graph._statuses.values())
        has_running = len(graph.get_running_tasks()) > 0
        has_ready = len(graph.get_ready_tasks()) > 0

        # If we have tasks waiting, but nothing is currently running and nothing is ready,
        # the graph is deadlocked (usually due to a cycle that bypassed validation
        # or an orphaned dependency).
        if has_pending and not has_running and not has_ready:
            return True

        return False
