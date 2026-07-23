"""
Supervisor Report Generator

Synthesizes validated TaskResult outputs into a cohesive ExecutionResult payload
returned to the calling client.

Architecture Layer: Supervisor / ReportGenerator
"""

from typing import List

from core.logging.logger import logger
from core.models.domain import ExecutionResult, Goal, TaskResult, TaskStatus, ValidationResult


class SupervisorReportGenerator:
    """
    Supervisor subcomponent owning final output synthesis.

    Aggregates task outputs, determines overall execution status (success, partial, failed),
    and formats the final textual response.

    Does NOT execute tasks or interact with providers directly.
    TODO: Add multi-task formatting and markdown report templates in Phase 3.
    """

    async def generate_report(
        self,
        goal: Goal,
        results: List[TaskResult],
        validations: List[ValidationResult],
    ) -> ExecutionResult:
        """
        Synthesizes task outputs into a unified ExecutionResult object.

        Args:
            goal: Original Goal entity.
            results: List of completed TaskResult objects.
            validations: List of ValidationResult objects.

        Returns:
            ExecutionResult: Aggregated result payload returned to caller.
        """
        logger.info(
            "ReportGenerator: generating report",
            goal_id=goal.id,
            result_count=len(results),
        )

        successful = [r for r in results if r.status == TaskStatus.SUCCESS]
        failed = [r for r in results if r.status == TaskStatus.FAILED]

        # Determine overall execution status across tasks
        if len(successful) == len(results) and results:
            overall_status = "success"
        elif successful:
            overall_status = "partial"
        else:
            overall_status = "failed"

        # Build response text from task summaries
        if successful:
            response_text = successful[0].summary
        else:
            errors = "; ".join(r.error or "unknown error" for r in failed)
            response_text = f"The request could not be completed. Errors encountered: {errors}"

        report = ExecutionResult(
            goal_id=goal.id,
            status=overall_status,
            response=response_text,
            tasks=results,
        )

        logger.info(
            "ReportGenerator: report generated",
            goal_id=goal.id,
            status=overall_status,
            response_chars=len(response_text),
        )
        return report
