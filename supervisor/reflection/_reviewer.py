"""
Execution Reviewer (Internal)

Deterministic rule-based engine that inspects a completed ExecutionReport
to produce ReflectionObservations.

It analyzes metrics, task results, and decision logs to identify patterns.

Architecture Layer: Supervisor / Reflection
"""

from typing import List

from core.models.domain import DecisionType, ExecutionReport
from core.models.reflection import (
    ExecutionReview,
    ReflectionCategory,
    ReflectionObservation,
    ReflectionSeverity,
)


class ExecutionReviewer:
    """
    Internal engine for generating observations from an ExecutionReport.
    """

    def review(self, report: ExecutionReport) -> ExecutionReview:
        """
        Produce structured observations based on the execution report.
        """
        observations: List[ReflectionObservation] = []

        # 1. Evaluate Overall Success & Planning Quality
        if report.overall_status == "success":
            if report.metrics.failed_tasks == 0 and report.metrics.skipped_tasks == 0:
                observations.append(
                    ReflectionObservation(
                        category=ReflectionCategory.PLANNING,
                        severity=ReflectionSeverity.INFO,
                        description="Plan executed perfectly with no failures or skipped tasks.",
                        evidence=f"Total tasks: {report.metrics.total_tasks}",
                    )
                )
            else:
                observations.append(
                    ReflectionObservation(
                        category=ReflectionCategory.FAILURE_RECOVERY,
                        severity=ReflectionSeverity.INFO,
                        description="Execution succeeded despite encountering task failures.",
                        evidence=f"Failed tasks: {report.metrics.failed_tasks}, Skipped: {report.metrics.skipped_tasks}",
                    )
                )
        else:
            observations.append(
                ReflectionObservation(
                    category=ReflectionCategory.EXECUTION,
                    severity=ReflectionSeverity.HIGH,
                    description=f"Execution ended with status '{report.overall_status}'.",
                    evidence=f"Failed tasks: {report.metrics.failed_tasks}",
                )
            )

        # 2. Evaluate Retry Behavior
        decision_log = report.metrics.decision_log
        retries = [
            entry for entry in decision_log
            if entry.decision.decision_type == DecisionType.RETRY
        ]
        if retries:
            observations.append(
                ReflectionObservation(
                    category=ReflectionCategory.RETRY,
                    severity=(
                        ReflectionSeverity.LOW
                        if len(retries) <= 3
                        else ReflectionSeverity.MEDIUM
                    ),
                    description="Tasks were retried during execution.",
                    evidence=f"Retry count: {len(retries)}",
                )
            )
            # Check for excessive retries on a single task
            from typing import Dict
            task_retry_counts: Dict[str, int] = {}
            for r in retries:
                task_retry_counts[r.task_id] = task_retry_counts.get(r.task_id, 0) + 1

            for task_id, count in task_retry_counts.items():
                if count >= 3:
                    observations.append(
                        ReflectionObservation(
                            category=ReflectionCategory.RETRY,
                            severity=ReflectionSeverity.HIGH,
                            description=f"Task {task_id} experienced high retry churn.",
                            evidence=f"{count} retries on single task.",
                        )
                    )

        # 3. Evaluate Replanning Effectiveness
        replans = [
            entry for entry in decision_log
            if entry.decision.decision_type == DecisionType.REPLAN
        ]
        if replans:
            observations.append(
                ReflectionObservation(
                    category=ReflectionCategory.REPLAN,
                    severity=ReflectionSeverity.INFO,
                    description="Execution graph was dynamically mutated via replanning.",
                    evidence=f"Replan count: {len(replans)}",
                )
            )

        # 4. Evaluate Capability / Agent Selection
        if report.metrics.failed_tasks > 0:
            for task in report.failed_tasks:
                if "capability unavailable" in str(task.error).lower():
                    observations.append(
                        ReflectionObservation(
                            category=ReflectionCategory.CAPABILITY_SELECTION,
                            severity=ReflectionSeverity.HIGH,
                            description="Planner requested a capability that no agent provides.",
                            evidence=f"Task {task.task_id} failed due to missing capability.",
                        )
                    )

        return ExecutionReview(
            goal_id=report.goal_id,
            observations=observations,
        )
