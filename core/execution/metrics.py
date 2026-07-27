"""
MetricsCollector

Collects and aggregates execution telemetry during one goal lifecycle.

Records per-task timing and extracts tool call / reasoning step counts
from TaskResult metadata produced by the ReAct lifecycle.

Phase 5 adds:
  - retry_count, inserted_task_count tracking
  - failure_category_counts distribution
  - DecisionLog for full supervisor decision audit trail

Architecture Layer: Core / Execution
"""

import time
from typing import Any, Dict, List, Optional

from core.models.domain import (
    DecisionLogEntry,
    ExecutionMetrics,
    FailureCategory,
    TaskResult,
    TaskStatus,
)


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
        # Phase 5 adaptive supervisor counters
        self._retry_count: int = 0
        self._inserted_task_count: int = 0
        self._failure_category_counts: Dict[str, int] = {}
        self._decision_log: List[DecisionLogEntry] = []

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
            retry_count=self._retry_count,
            inserted_task_count=self._inserted_task_count,
            failure_category_counts=dict(self._failure_category_counts),
            decision_log=list(self._decision_log),
        )

    # ------------------------------------------------------------------
    # Phase 5 — Adaptive Supervisor Tracking
    # ------------------------------------------------------------------

    def record_retry(self, task_id: str, category: FailureCategory) -> None:
        """Record that a task was retried due to a classified failure."""
        self._retry_count += 1
        key = category.value
        self._failure_category_counts[key] = self._failure_category_counts.get(key, 0) + 1

    def record_inserted_task(self, task_id: str) -> None:
        """Record that a new task was dynamically inserted into the graph."""
        self._inserted_task_count += 1

    def record_decision(self, entry: DecisionLogEntry) -> None:
        """Append a supervisor decision to the DecisionLog."""
        self._decision_log.append(entry)

    @property
    def retry_count(self) -> int:
        """Total number of retries issued during execution."""
        return self._retry_count

    @property
    def inserted_task_count(self) -> int:
        """Total number of tasks dynamically inserted via replanning."""
        return self._inserted_task_count

    @property
    def failure_category_counts(self) -> Dict[str, int]:
        """Failure category distribution (category value → count)."""
        return dict(self._failure_category_counts)

    def get_decision_log(self) -> List[DecisionLogEntry]:
        """Return the full ordered supervisor decision audit trail."""
        return list(self._decision_log)


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
