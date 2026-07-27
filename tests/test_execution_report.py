"""Tests for MetricsCollector and ReportBuilder (Phase 4.5)."""

import uuid

from core.execution.metrics import MetricsCollector
from core.execution.report import ReportBuilder
from core.models.domain import Goal, TaskResult, TaskStatus


def _make_goal() -> Goal:
    return Goal(id=str(uuid.uuid4()), description="Report test goal")


def _make_result(
    task_id: str,
    status: TaskStatus,
    agent_id: str = "Agent1",
    summary: str = "Done.",
    error: str | None = None,
) -> TaskResult:
    return TaskResult(
        task_id=task_id,
        agent_id=agent_id,
        status=status,
        summary=summary,
        error=error,
    )


class TestMetricsCollector:
    def test_finalize_counts_statuses(self) -> None:
        collector = MetricsCollector()
        collector.start_goal()

        results = [
            _make_result("t1", TaskStatus.SUCCESS),
            _make_result("t2", TaskStatus.FAILED, error="oops"),
            _make_result("t3", TaskStatus.SKIPPED, summary=""),
        ]

        for r in results:
            collector.start_task(r.task_id)
            collector.end_task(r.task_id, "Agent1", r)

        metrics = collector.finalize(total_tasks=3)

        assert metrics.total_tasks == 3
        assert metrics.completed_tasks == 1
        assert metrics.failed_tasks == 1
        assert metrics.skipped_tasks == 1

    def test_execution_time_is_positive(self) -> None:
        collector = MetricsCollector()
        collector.start_goal()
        r = _make_result("t1", TaskStatus.SUCCESS)
        collector.start_task("t1")
        collector.end_task("t1", "Agent1", r)
        metrics = collector.finalize()
        assert metrics.execution_time_ms >= 0.0


class TestReportBuilder:
    def test_all_success_report(self) -> None:
        goal = _make_goal()
        results = [
            _make_result("t1", TaskStatus.SUCCESS, summary="Part 1"),
            _make_result("t2", TaskStatus.SUCCESS, summary="Part 2"),
        ]
        report = ReportBuilder(goal).add_results(results).build()

        assert report.overall_status == "success"
        assert len(report.completed_tasks) == 2
        assert len(report.failed_tasks) == 0
        assert len(report.skipped_tasks) == 0

    def test_partial_success_report(self) -> None:
        goal = _make_goal()
        results = [
            _make_result("t1", TaskStatus.SUCCESS, summary="Part 1"),
            _make_result("t2", TaskStatus.FAILED, error="boom"),
        ]
        report = ReportBuilder(goal).add_results(results).build()

        assert report.overall_status == "partial"
        assert len(report.completed_tasks) == 1
        assert len(report.failed_tasks) == 1

    def test_all_failed_report(self) -> None:
        goal = _make_goal()
        results = [_make_result("t1", TaskStatus.FAILED, error="err")]
        report = ReportBuilder(goal).add_results(results).build()

        assert report.overall_status == "failed"
        assert "err" in report.final_response
