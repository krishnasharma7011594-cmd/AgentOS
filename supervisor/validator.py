"""
Supervisor Validator

Evaluates completed TaskResult objects against structural and quality constraints.
Ensures failed or empty agent results are caught before report generation.

Architecture Layer: Supervisor / Validator
"""

from core.logging.logger import logger
from core.models.domain import Goal, TaskResult, TaskStatus, ValidationResult


class SupervisorValidator:
    """
    Supervisor subcomponent responsible for task result validation.

    Evaluates TaskResult outputs against integrity rules:
      - Execution status must be SUCCESS.
      - Generated summary must be non-empty.
      - Error payload must be clear.

    Does NOT re-execute tasks or alter plans directly.
    TODO: Add LLM-as-a-Judge semantic quality verification in Phase 3.
    """

    async def validate_result(self, goal: Goal, result: TaskResult) -> ValidationResult:
        """
        Validates a single TaskResult against structural integrity criteria.

        Args:
            goal: Target Goal associated with execution.
            result: TaskResult produced by an agent.

        Returns:
            ValidationResult: Validation outcome and status.
        """
        logger.info(
            "SupervisorValidator: validating result",
            task_id=result.task_id,
            status=result.status,
        )

        # Rule 1: Task execution status check
        if result.status != TaskStatus.SUCCESS:
            reason = f"Task status is '{result.status.value}', expected 'success'."
            if result.error:
                reason += f" Error: {result.error}"
            logger.warning(
                "SupervisorValidator: validation failed — bad status",
                task_id=result.task_id,
                reason=reason,
            )
            return ValidationResult(
                task_id=result.task_id,
                is_valid=False,
                reason=reason,
            )

        # Rule 2: Non-empty payload summary check
        if not result.summary or not result.summary.strip():
            reason = "Task result summary is empty."
            logger.warning(
                "SupervisorValidator: validation failed — empty summary",
                task_id=result.task_id,
            )
            return ValidationResult(
                task_id=result.task_id,
                is_valid=False,
                reason=reason,
            )

        # Rule 3: Absence of error strings on successful status
        if result.error:
            reason = f"Task marked SUCCESS but error field is set: {result.error}"
            logger.warning(
                "SupervisorValidator: validation failed — error on success",
                task_id=result.task_id,
            )
            return ValidationResult(
                task_id=result.task_id,
                is_valid=False,
                reason=reason,
            )

        logger.info(
            "SupervisorValidator: validation passed",
            task_id=result.task_id,
        )
        return ValidationResult(
            task_id=result.task_id,
            is_valid=True,
            reason="All validation checks passed.",
        )
