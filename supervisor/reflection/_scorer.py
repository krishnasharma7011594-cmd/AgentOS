"""
Reflection Scorer (Internal)

Deterministically calculates scores (0-100) for a completed execution based on
the ExecutionReport metrics and observations.

Architecture Layer: Supervisor / Reflection
"""

from core.models.domain import DecisionType, ExecutionReport
from core.models.reflection import ExecutionReview, ReflectionScore


class ReflectionScorer:
    """
    Internal engine for calculating deterministic reflection scores.
    """

    def score(self, report: ExecutionReport, review: ExecutionReview) -> ReflectionScore:
        """
        Calculate deterministic scores based on hard-coded rules.
        """
        total = report.metrics.total_tasks
        if total == 0:
            return ReflectionScore(
                planning_quality=0,
                execution_efficiency=0,
                failure_recovery=0,
                agent_selection=0,
                task_efficiency=0,
                overall_score=0,
            )

        # 1. Planning Quality (Penalty for missing capabilities, high skipped tasks)
        planning_score = 100
        capability_fails = sum(
            1 for obs in review.observations if obs.category.value == "capability_selection"
        )
        planning_score -= capability_fails * 20
        planning_score -= int((report.metrics.skipped_tasks / total) * 30)
        planning_score = max(0, min(100, planning_score))

        # 2. Execution Efficiency (Penalty for excessive retries)
        exec_score = 100
        retries = report.metrics.retry_count if hasattr(report.metrics, "retry_count") else 0
        exec_score -= retries * 5
        exec_score = max(0, min(100, exec_score))

        # 3. Failure Recovery (Reward for successful replanning, penalty for unrecovered failures)
        recovery_score = 100
        if report.metrics.failed_tasks > 0:
            recovery_score -= int((report.metrics.failed_tasks / total) * 50)
            decision_log = report.metrics.decision_log
            replans = sum(
                1 for entry in decision_log 
                if entry.decision.decision_type == DecisionType.REPLAN
            )
            recovery_score += replans * 10  # Reward dynamic recovery attempts
        recovery_score = max(0, min(100, recovery_score))

        # 4. Agent Selection (Penalty for tool failures or unknown errors)
        agent_score = 100
        fail_cats = report.metrics.failure_category_counts
        tool_fails = fail_cats.get("tool_failure", 0)
        unknown_fails = fail_cats.get("unknown", 0)
        agent_score -= tool_fails * 10
        agent_score -= unknown_fails * 10
        agent_score = max(0, min(100, agent_score))

        # 5. Task Efficiency (Penalty for high reasoning steps or tool calls per task)
        task_score = 100
        if report.metrics.completed_tasks > 0:
            avg_steps = report.metrics.total_reasoning_steps / report.metrics.completed_tasks
            if avg_steps > 10:
                task_score -= int((avg_steps - 10) * 2)
        task_score = max(0, min(100, task_score))

        # Overall Score
        overall_score = int(
            (planning_score + exec_score + recovery_score + agent_score + task_score) / 5
        )

        return ReflectionScore(
            planning_quality=planning_score,
            execution_efficiency=exec_score,
            failure_recovery=recovery_score,
            agent_selection=agent_score,
            task_efficiency=task_score,
            overall_score=overall_score,
        )
