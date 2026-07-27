"""Tests for ExecutionReviewer (Phase 6)."""

from core.models.domain import (
    Decision,
    DecisionLogEntry,
    DecisionType,
    ExecutionMetrics,
    ExecutionReport,
    TaskEvaluation,
    TaskResult,
    TaskStatus,
)
from core.models.reflection import ReflectionCategory, ReflectionSeverity
from supervisor.reflection._reviewer import ExecutionReviewer


def _mock_report(
    status: str = "success",
    failed_count: int = 0,
    skipped_count: int = 0,
    decisions: list[DecisionType] | None = None,
    failed_tasks: list[TaskResult] | None = None,
) -> ExecutionReport:
    entries = []
    if decisions:
        for d in decisions:
            entries.append(
                DecisionLogEntry(
                    task_id="t1",
                    decision=Decision(decision_type=d, reason="test"),
                    evaluation=TaskEvaluation(task_id="t1", is_success=False),
                )
            )

    metrics = ExecutionMetrics(
        total_tasks=3,
        completed_tasks=3 - failed_count - skipped_count,
        failed_tasks=failed_count,
        skipped_tasks=skipped_count,
        decision_log=entries,
    )

    return ExecutionReport(
        goal_id="g1",
        goal_description="test",
        overall_status=status,
        metrics=metrics,
        failed_tasks=failed_tasks or [],
        final_response="done",
    )


def test_perfect_execution_observation() -> None:
    reviewer = ExecutionReviewer()
    report = _mock_report()
    review = reviewer.review(report)

    obs = next((o for o in review.observations if o.category == ReflectionCategory.PLANNING), None)
    assert obs is not None
    assert obs.severity == ReflectionSeverity.INFO
    assert "perfectly" in obs.description


def test_failure_recovery_observation() -> None:
    reviewer = ExecutionReviewer()
    report = _mock_report(status="success", failed_count=1)
    review = reviewer.review(report)

    obs = next(
        (o for o in review.observations if o.category == ReflectionCategory.FAILURE_RECOVERY), None
    )
    assert obs is not None
    assert obs.severity == ReflectionSeverity.INFO


def test_failed_execution_observation() -> None:
    reviewer = ExecutionReviewer()
    report = _mock_report(status="failed", failed_count=2)
    review = reviewer.review(report)

    obs = next((o for o in review.observations if o.category == ReflectionCategory.EXECUTION), None)
    assert obs is not None
    assert obs.severity == ReflectionSeverity.HIGH


def test_retry_observations() -> None:
    reviewer = ExecutionReviewer()
    report = _mock_report(
        decisions=[DecisionType.RETRY, DecisionType.RETRY, DecisionType.RETRY, DecisionType.RETRY]
    )
    review = reviewer.review(report)

    retry_obs = [o for o in review.observations if o.category == ReflectionCategory.RETRY]
    assert len(retry_obs) == 2  # One general, one for high churn on task 't1'
    assert any(o.severity == ReflectionSeverity.MEDIUM for o in retry_obs)
    assert any(o.severity == ReflectionSeverity.HIGH for o in retry_obs)


def test_capability_selection_observation() -> None:
    reviewer = ExecutionReviewer()
    failed_task = TaskResult(
        task_id="t1",
        agent_id="supervisor",
        status=TaskStatus.FAILED,
        summary="",
        error="Capability unavailable for this request",
    )
    report = _mock_report(status="failed", failed_count=1, failed_tasks=[failed_task])
    review = reviewer.review(report)

    obs = next(
        (o for o in review.observations if o.category == ReflectionCategory.CAPABILITY_SELECTION),
        None,
    )
    assert obs is not None
    assert obs.severity == ReflectionSeverity.HIGH
