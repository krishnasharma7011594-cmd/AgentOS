"""
ReportBuilder

Constructs structured ExecutionReport objects from raw execution data.

Keeps report assembly logic out of the orchestrator and report_generator,
following the single-responsibility principle.

Architecture Layer: Core / Execution
"""

from typing import Dict, List

from core.models.domain import (
    ExecutionMetrics,
    ExecutionReport,
    Goal,
    TaskResult,
    TaskStatus,
)


class ReportBuilder:
    """
    Assembles an ExecutionReport from the raw outputs of a goal execution.

    Usage::

        builder = ReportBuilder(goal)
        builder.add_results(task_results)
        builder.set_metrics(metrics)
        report = builder.build()
    """

    def __init__(self, goal: Goal) -> None:
        self._goal = goal
        self._results: List[TaskResult] = []
        self._metrics: ExecutionMetrics = ExecutionMetrics()

    def add_results(self, results: List[TaskResult]) -> "ReportBuilder":
        """Provide the list of TaskResult objects from execution."""
        self._results = results
        return self

    def set_metrics(self, metrics: ExecutionMetrics) -> "ReportBuilder":
        """Provide the ExecutionMetrics collected during execution."""
        self._metrics = metrics
        return self

    def build(self) -> ExecutionReport:
        """
        Assemble and return the structured ExecutionReport.

        Partitions results into completed / failed / skipped buckets,
        builds agent_contributions mapping, determines overall_status,
        and synthesizes the final_response text.
        """
        completed = [r for r in self._results if r.status == TaskStatus.SUCCESS]
        failed = [r for r in self._results if r.status == TaskStatus.FAILED]
        skipped = [r for r in self._results if r.status == TaskStatus.SKIPPED]

        overall_status = _derive_status(completed, failed, skipped, self._results)
        agent_contributions = _build_contributions(completed)
        final_response = _synthesize_response(completed, failed)

        return ExecutionReport(
            goal_id=self._goal.id,
            goal_description=self._goal.description,
            overall_status=overall_status,
            completed_tasks=completed,
            skipped_tasks=skipped,
            failed_tasks=failed,
            agent_contributions=agent_contributions,
            metrics=self._metrics,
            final_response=final_response,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _derive_status(
    completed: List[TaskResult],
    failed: List[TaskResult],
    skipped: List[TaskResult],
    all_results: List[TaskResult],
) -> str:
    if not all_results:
        return "failed"
    if len(completed) == len(all_results):
        return "success"
    if completed:
        return "partial"
    return "failed"


def _build_contributions(completed: List[TaskResult]) -> Dict[str, List[str]]:
    """Map agent_id → list of task summaries they produced."""
    contributions: Dict[str, List[str]] = {}
    for result in completed:
        contributions.setdefault(result.agent_id, []).append(result.summary)
    return contributions


def _synthesize_response(
    completed: List[TaskResult],
    failed: List[TaskResult],
) -> str:
    if completed:
        if len(completed) == 1:
            return completed[0].summary
        parts = []
        for idx, r in enumerate(completed, 1):
            parts.append(f"### Part {idx} by {r.agent_id}\n{r.summary}")
        return "\n\n".join(parts)

    errors = "; ".join(r.error or "unknown error" for r in failed)
    return f"The request could not be completed. Errors encountered: {errors}"
