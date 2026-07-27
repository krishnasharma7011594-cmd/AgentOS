"""
Supervisor Report Generator

Synthesizes validated TaskResult outputs into a cohesive ExecutionResult payload
returned to the calling client.

Phase 4.5: Delegates report assembly to ReportBuilder and populates
ExecutionResult.report with the rich ExecutionReport for structured consumers.

Architecture Layer: Supervisor / ReportGenerator
"""

from typing import List

from core.execution.report import ReportBuilder
from core.logging.logger import logger
from core.models.domain import (
    ExecutionMetrics,
    ExecutionResult,
    Goal,
    TaskResult,
    ValidationResult,
)


class SupervisorReportGenerator:
    """
    Supervisor subcomponent owning final output synthesis.

    Phase 4.5: Delegates to ReportBuilder for structured report assembly.
    Returns a backward-compatible ExecutionResult enriched with an optional
    ExecutionReport in the .report field.
    """

    async def generate_report(
        self,
        goal: Goal,
        results: List[TaskResult],
        validations: List[ValidationResult],
        metrics: ExecutionMetrics | None = None,
    ) -> ExecutionResult:
        """
        Synthesize task outputs into a unified ExecutionResult.

        Args:
            goal:        Original Goal entity.
            results:     List of completed TaskResult objects.
            validations: List of ValidationResult objects.
            metrics:     Optional ExecutionMetrics collected during execution.

        Returns:
            ExecutionResult: Backward-compatible result enriched with ExecutionReport.
        """
        logger.info(
            "ReportGenerator: generating report",
            goal_id=goal.id,
            result_count=len(results),
        )

        # Build the rich structured report
        builder = (
            ReportBuilder(goal).add_results(results).set_metrics(metrics or ExecutionMetrics())
        )
        report = builder.build()

        execution_result = ExecutionResult(
            goal_id=goal.id,
            status=report.overall_status,
            response=report.final_response,
            tasks=results,
            report=report,
        )

        logger.info(
            "ReportGenerator: report generated",
            goal_id=goal.id,
            status=report.overall_status,
            completed=report.metrics.completed_tasks,
            failed=report.metrics.failed_tasks,
            skipped=report.metrics.skipped_tasks,
            response_chars=len(report.final_response),
        )
        return execution_result
