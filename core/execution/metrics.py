"""
MetricsCollector

Collects and aggregates execution telemetry during one goal lifecycle.

Records per-task timing and extracts tool call / reasoning step counts
from TaskResult metadata produced by the ReAct lifecycle.

Architecture Layer: Core / Execution
"""

import time
from typing import Any, Dict, Optional

from core.models.domain import ExecutionMetrics, TaskResult, TaskStatus


class MetricsCollector:
    """
    Collects timing and telemetry for one goal execution.

    Usage::

        collector = MetricsCollector()
        collector.start_goal()

        token = collector.start_task(task_id, agent_id)
        # ... execute task ...
        collector.end_task(token, result)

        metrics = collector.finalize()
    """

    def __init__(self) -> None:
        self._goal_start: float = 0.0
        self._task_starts: Dict[str, float] = {}  # task_id → start time
        self._agent_times: Dict[str, float] = {}  # agent_id → cumulative ms
        self._results: list[TaskResult] = []

    # ------------------------------------------------------------------
    # Goal lifecycle
    # ------------------------------------------------------------------

    def start_goal(self) -> None:
        """Record the goal start wall-clock time."""
        self._goal_start = time.monotonic()

    # ------------------------------------------------------------------
    # Task lifecycle
    # ------------------------------------------------------------------

    def start_task(self, task_id: str) -> None:
        """Record start time for a task."""
        self._task_starts[task_id] = time.monotonic()

    def end_task(self, task_id: str, agent_id: str, result: TaskResult) -> None:
        """
        Record task completion and accumulate agent execution time.

        Args:
            task_id:  ID of the completed task.
            agent_id: Agent that executed the task.
            result:   Completed TaskResult (used for metadata extraction).
        """
        start = self._task_starts.pop(task_id, time.monotonic())
        elapsed_ms = (time.monotonic() - start) * 1000.0
        self._agent_times[agent_id] = self._agent_times.get(agent_id, 0.0) + elapsed_ms
        self._results.append(result)

    # ------------------------------------------------------------------
    # Finalization
    # ------------------------------------------------------------------

    def finalize(self, total_tasks: Optional[int] = None) -> ExecutionMetrics:
        """
        Compute and return the final ExecutionMetrics.

        Args:
            total_tasks: Override total task count (defaults to len(results)).

        Returns:
            ExecutionMetrics: Populated metrics object.
        """
        goal_elapsed_ms = (time.monotonic() - self._goal_start) * 1000.0

        completed = sum(1 for r in self._results if r.status == TaskStatus.SUCCESS)
        failed = sum(1 for r in self._results if r.status == TaskStatus.FAILED)
        skipped = sum(1 for r in self._results if r.status == TaskStatus.SKIPPED)

        tool_calls = 0
        reasoning_steps = 0
        for result in self._results:
            meta = result.metadata or {}
            tool_calls += _count_tool_calls(meta)
            reasoning_steps += _count_reasoning_steps(meta)

        return ExecutionMetrics(
            total_tasks=total_tasks if total_tasks is not None else len(self._results),
            completed_tasks=completed,
            failed_tasks=failed,
            skipped_tasks=skipped,
            execution_time_ms=round(goal_elapsed_ms, 2),
            agent_execution_times={k: round(v, 2) for k, v in self._agent_times.items()},
            total_tool_calls=tool_calls,
            total_reasoning_steps=reasoning_steps,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _count_tool_calls(meta: Dict[str, Any]) -> int:
    """Extract tool call count from TaskResult.metadata."""
    steps = meta.get("reasoning_steps", [])
    if isinstance(steps, list):
        return sum(1 for s in steps if isinstance(s, dict) and s.get("action"))
    return 0


def _count_reasoning_steps(meta: Dict[str, Any]) -> int:
    """Extract reasoning step count from TaskResult.metadata."""
    steps = meta.get("reasoning_steps", [])
    if isinstance(steps, list):
        return len(steps)
    return 0
