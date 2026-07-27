"""
ExecutionGraph

Graph-based task execution state machine for AgentOS.

Wraps an ExecutionPlan and tracks the live status of every Task node,
enforcing valid state transitions and computing which tasks are ready
to execute based on dependency satisfaction.

Execution is currently sequential. The graph abstraction prepares the
architecture for future DAG / parallel execution without changing public APIs.

Architecture Layer: Core / Execution
"""

from typing import Dict, List, Optional

from core.models.domain import ExecutionPlan, Task, TaskResult, TaskStatus

# Valid state transitions:  current → allowed next states
_VALID_TRANSITIONS: Dict[TaskStatus, List[TaskStatus]] = {
    TaskStatus.PENDING: [TaskStatus.READY, TaskStatus.SKIPPED],
    TaskStatus.READY: [TaskStatus.RUNNING, TaskStatus.SKIPPED],
    TaskStatus.RUNNING: [TaskStatus.SUCCESS, TaskStatus.FAILED],
    TaskStatus.SUCCESS: [],  # terminal
    TaskStatus.FAILED: [],  # terminal
    TaskStatus.SKIPPED: [],  # terminal
}


class InvalidTaskTransitionError(Exception):
    """Raised when an illegal task state transition is attempted."""


class ExecutionGraph:
    """
    Stateful execution graph for a single goal lifecycle.

    Wraps the tasks from an ExecutionPlan and tracks their live statuses.
    Exposes query methods so the orchestrator can iterate through tasks
    without ever directly touching status fields on Task objects.

    Usage::

        graph = ExecutionGraph(plan)
        graph.initialize()

        while graph.get_remaining_tasks():
            for task in graph.get_ready_tasks():
                graph.mark_task_running(task.id)
                result = await router.route_task(task, context)
                if result.status == TaskStatus.SUCCESS:
                    graph.mark_task_success(task.id, result)
                else:
                    graph.mark_task_failed(task.id, result)
            graph.advance()
    """

    def __init__(self, plan: ExecutionPlan) -> None:
        self._plan = plan
        # task_id → Task (immutable source)
        self._tasks: Dict[str, Task] = {t.id: t for t in plan.tasks}
        # task_id → live TaskStatus (mutable)
        self._statuses: Dict[str, TaskStatus] = {}
        # task_id → TaskResult (populated after terminal state)
        self._results: Dict[str, TaskResult] = {}

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """
        Set initial statuses.

        Tasks with no dependencies start as READY.
        Tasks with dependencies start as PENDING.
        """
        for task in self._tasks.values():
            if task.dependencies:
                self._statuses[task.id] = TaskStatus.PENDING
            else:
                self._statuses[task.id] = TaskStatus.READY

    # ------------------------------------------------------------------
    # State Transition API
    # ------------------------------------------------------------------

    def _transition(self, task_id: str, new_status: TaskStatus) -> None:
        """Apply a status transition, raising on invalid moves."""
        current = self._statuses[task_id]
        allowed = _VALID_TRANSITIONS.get(current, [])
        if new_status not in allowed:
            raise InvalidTaskTransitionError(
                f"Task '{task_id}': cannot transition {current} → {new_status}. "
                f"Allowed: {[s.value for s in allowed]}"
            )
        self._statuses[task_id] = new_status

    def mark_task_running(self, task_id: str) -> None:
        """PENDING/READY → RUNNING."""
        self._transition(task_id, TaskStatus.RUNNING)

    def mark_task_success(self, task_id: str, result: TaskResult) -> None:
        """RUNNING → SUCCESS. Stores the result for dependency checks."""
        self._transition(task_id, TaskStatus.SUCCESS)
        self._results[task_id] = result

    def mark_task_failed(self, task_id: str, result: TaskResult) -> None:
        """RUNNING → FAILED. Stores the result for reporting."""
        self._transition(task_id, TaskStatus.FAILED)
        self._results[task_id] = result

    def mark_task_skipped(self, task_id: str) -> None:
        """PENDING/READY → SKIPPED (dependency failed/skipped)."""
        self._transition(task_id, TaskStatus.SKIPPED)

    # ------------------------------------------------------------------
    # Graph Advancement
    # ------------------------------------------------------------------

    def advance(self) -> None:
        """
        Recalculate PENDING task readiness after a round of execution.

        A PENDING task becomes READY when ALL its dependencies are SUCCESS.
        A PENDING task becomes SKIPPED when ANY dependency is FAILED or SKIPPED.
        """
        for task_id, status in list(self._statuses.items()):
            if status != TaskStatus.PENDING:
                continue

            task = self._tasks[task_id]
            dep_statuses = [self._statuses.get(d, TaskStatus.PENDING) for d in task.dependencies]

            # Any failed or skipped dependency cascades to SKIPPED
            if any(s in (TaskStatus.FAILED, TaskStatus.SKIPPED) for s in dep_statuses):
                self._statuses[task_id] = TaskStatus.SKIPPED

            # All dependencies satisfied → task is ready
            elif all(s == TaskStatus.SUCCESS for s in dep_statuses):
                self._statuses[task_id] = TaskStatus.READY

    # ------------------------------------------------------------------
    # Query Methods
    # ------------------------------------------------------------------

    def get_ready_tasks(self) -> List[Task]:
        """Return tasks currently in READY state."""
        return [
            self._tasks[tid] for tid, status in self._statuses.items() if status == TaskStatus.READY
        ]

    def get_running_tasks(self) -> List[Task]:
        """Return tasks currently in RUNNING state."""
        return [
            self._tasks[tid]
            for tid, status in self._statuses.items()
            if status == TaskStatus.RUNNING
        ]

    def get_completed_tasks(self) -> List[Task]:
        """Return tasks in SUCCESS state."""
        return [
            self._tasks[tid]
            for tid, status in self._statuses.items()
            if status == TaskStatus.SUCCESS
        ]

    def get_failed_tasks(self) -> List[Task]:
        """Return tasks in FAILED state."""
        return [
            self._tasks[tid]
            for tid, status in self._statuses.items()
            if status == TaskStatus.FAILED
        ]

    def get_skipped_tasks(self) -> List[Task]:
        """Return tasks in SKIPPED state."""
        return [
            self._tasks[tid]
            for tid, status in self._statuses.items()
            if status == TaskStatus.SKIPPED
        ]

    def get_remaining_tasks(self) -> List[Task]:
        """Return tasks still in PENDING or READY state (not yet terminal)."""
        return [
            self._tasks[tid]
            for tid, status in self._statuses.items()
            if status in (TaskStatus.PENDING, TaskStatus.READY)
        ]

    def get_result(self, task_id: str) -> Optional[TaskResult]:
        """Return the stored TaskResult for a task, or None if not yet complete."""
        return self._results.get(task_id)

    def all_results(self) -> Dict[str, TaskResult]:
        """Return all stored task results keyed by task ID."""
        return dict(self._results)

    def get_status(self, task_id: str) -> TaskStatus:
        """Return the current status of a task."""
        return self._statuses[task_id]

    def is_complete(self) -> bool:
        """True when no tasks remain in PENDING or READY state."""
        return not self.get_remaining_tasks()

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def task_count(self) -> int:
        """Total number of tasks in the graph."""
        return len(self._tasks)

    @property
    def plan_id(self) -> str:
        return self._plan.id

    @property
    def goal_id(self) -> str:
        return self._plan.goal_id
