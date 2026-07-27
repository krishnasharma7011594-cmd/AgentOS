"""Tests for ReflectionScorer (Phase 6)."""

from core.models.domain import (
    Decision,
    DecisionLogEntry,
    DecisionType,
    ExecutionMetrics,
    ExecutionReport,
    TaskEvaluation,
)
from core.models.reflection import (
    ExecutionReview,
    ReflectionCategory,
    ReflectionObservation,
    ReflectionSeverity,
)
from supervisor.reflection._scorer import ReflectionScorer


def _mock_report(
    total: int = 3,
    skipped: int = 0,
    failed: int = 0,
    completed: int = 3,
    retries: int = 0,
    replans: int = 0,
    tool_fails: int = 0,
    avg_steps: float = 3.0,
) -> ExecutionReport:
    entries = []
    for _ in range(replans):
        entries.append(
            DecisionLogEntry(
                task_id="t1",
                decision=Decision(decision_type=DecisionType.REPLAN, reason="test"),
                evaluation=TaskEvaluation(task_id="t1", is_success=False),
            )
        )

    metrics = ExecutionMetrics(
        total_tasks=total,
        skipped_tasks=skipped,
        failed_tasks=failed,
        completed_tasks=completed,
        total_reasoning_steps=int(avg_steps * completed),
        retry_count=retries,
        failure_category_counts={"tool_failure": tool_fails},
        decision_log=entries,
    )

    return ExecutionReport(
        goal_id="g1",
        goal_description="test",
        overall_status="success",
        metrics=metrics,
        final_response="done",
    )


def test_perfect_score() -> None:
    scorer = ReflectionScorer()
    report = _mock_report()
    review = ExecutionReview(goal_id="g1", observations=[])

    score = scorer.score(report, review)
    assert score.overall_score == 100
    assert score.planning_quality == 100
    assert score.execution_efficiency == 100
    assert score.task_efficiency == 100
    assert score.failure_recovery == 100
    assert score.agent_selection == 100


def test_penalties() -> None:
    scorer = ReflectionScorer()
    report = _mock_report(
        skipped=1,  # Penalty on planning (33% of 3 = -10)
        retries=2,  # Penalty on exec efficiency (-10)
        failed=1,  # Penalty on recovery (33% = -16)
        tool_fails=1,  # Penalty on agent (-10)
        avg_steps=12.0,  # Penalty on task (-4)
    )
    obs = ReflectionObservation(
        category=ReflectionCategory.CAPABILITY_SELECTION,
        severity=ReflectionSeverity.HIGH,
        description="Missing capability",
        evidence="None",
    )
    review = ExecutionReview(goal_id="g1", observations=[obs])

    score = scorer.score(report, review)

    # Planning: 100 - (1 * 20) - 10 = 70
    assert score.planning_quality == 70
    # Exec: 100 - (2 * 5) = 90
    assert score.execution_efficiency == 90
    # Agent: 100 - (1 * 10) = 90
    assert score.agent_selection == 90
    # Task: 100 - (2 * 2) = 96
    assert score.task_efficiency == 96
    # Recovery: 100 - (1/3 * 50 = 16) + 0 replans = 84
    assert score.failure_recovery == 84

    # Overall = (70 + 90 + 90 + 96 + 84) / 5 = 430 / 5 = 86
    assert score.overall_score == 86
