"""
Supervisor Validator

Evaluates completed TaskResult objects and validates ExecutionPlans before execution.

Phase 4.5 additions:
  - validate_plan(): Graph-level validation with cycle detection, duplicate ID checks,
    missing capabilities, invalid dependency references, and state checks.

Architecture Layer: Supervisor / Validator
"""

from typing import Dict, List, Set

from core.logging.logger import logger
from core.models.domain import (
    ExecutionPlan,
    Goal,
    PlanValidationResult,
    TaskResult,
    TaskStatus,
    ValidationResult,
)
from registry.capability_registry import CapabilityRegistry


class SupervisorValidator:
    """
    Supervisor subcomponent responsible for task result and plan validation.

    Task result validation:
      - Execution status must be SUCCESS.
      - Generated summary must be non-empty.
      - Error payload must be clear.

    Plan validation (validate_plan):
      - Non-empty plan.
      - No duplicate task IDs.
      - No circular dependencies.
      - All dependency references point to existing task IDs.
      - All required capabilities are registered.
      - All tasks start in PENDING status.
    """

    def __init__(self, capability_registry: CapabilityRegistry | None = None) -> None:
        self._capability_registry = capability_registry

    # ------------------------------------------------------------------
    # Result Validation
    # ------------------------------------------------------------------

    async def validate_result(self, goal: Goal, result: TaskResult) -> ValidationResult:
        """
        Validate a single TaskResult against structural integrity criteria.

        Args:
            goal:   Target Goal associated with execution.
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
        if result.status not in (TaskStatus.SUCCESS, TaskStatus.SKIPPED):
            reason = f"Task status is '{result.status.value}', expected 'success'."
            if result.error:
                reason += f" Error: {result.error}"
            logger.warning(
                "SupervisorValidator: validation failed — bad status",
                task_id=result.task_id,
                reason=reason,
            )
            return ValidationResult(task_id=result.task_id, is_valid=False, reason=reason)

        # Skipped tasks are structurally valid (no further checks needed)
        if result.status == TaskStatus.SKIPPED:
            return ValidationResult(
                task_id=result.task_id,
                is_valid=True,
                reason="Task was skipped due to failed dependency.",
            )

        # Rule 2: Non-empty payload summary check
        if not result.summary or not result.summary.strip():
            reason = "Task result summary is empty."
            logger.warning(
                "SupervisorValidator: validation failed — empty summary",
                task_id=result.task_id,
            )
            return ValidationResult(task_id=result.task_id, is_valid=False, reason=reason)

        # Rule 3: Absence of error strings on successful status
        if result.error:
            reason = f"Task marked SUCCESS but error field is set: {result.error}"
            logger.warning(
                "SupervisorValidator: validation failed — error on success",
                task_id=result.task_id,
            )
            return ValidationResult(task_id=result.task_id, is_valid=False, reason=reason)

        logger.info("SupervisorValidator: validation passed", task_id=result.task_id)
        return ValidationResult(
            task_id=result.task_id,
            is_valid=True,
            reason="All validation checks passed.",
        )

    # ------------------------------------------------------------------
    # Plan Validation
    # ------------------------------------------------------------------

    def validate_plan(self, plan: ExecutionPlan) -> PlanValidationResult:
        """
        Validate an ExecutionPlan before execution begins.

        Checks performed:
          1. Plan is non-empty.
          2. No duplicate task IDs.
          3. All dependency task IDs reference existing tasks.
          4. No circular dependencies (DFS cycle detection).
          5. All required capabilities are registered (if registry available).
          6. All tasks start in PENDING status.

        Returns:
            PlanValidationResult: is_valid flag and list of error messages.
        """
        errors: List[str] = []
        task_ids: Set[str] = {t.id for t in plan.tasks}

        # Check 1: non-empty
        if not plan.tasks:
            errors.append("ExecutionPlan contains no tasks.")
            return PlanValidationResult(is_valid=False, errors=errors)

        # Check 2: duplicate IDs
        seen_ids: Set[str] = set()
        for task in plan.tasks:
            if task.id in seen_ids:
                errors.append(f"Duplicate task ID detected: '{task.id}'.")
            seen_ids.add(task.id)

        # Check 3: invalid dependency references
        for task in plan.tasks:
            for dep_id in task.dependencies:
                if dep_id not in task_ids:
                    errors.append(f"Task '{task.id}' depends on unknown task ID '{dep_id}'.")

        # Check 4: circular dependency detection (DFS)
        cycle_error = _detect_cycle(plan)
        if cycle_error:
            errors.append(cycle_error)

        # Check 5: missing capabilities
        if self._capability_registry is not None:
            for task in plan.tasks:
                if not self._capability_registry.is_capability_available(task.required_capability):
                    errors.append(
                        f"Task '{task.id}' requires capability "
                        f"'{task.required_capability}' which is not registered."
                    )

        # Check 6: initial task states
        for task in plan.tasks:
            if task.status != TaskStatus.PENDING:
                errors.append(
                    f"Task '{task.id}' has unexpected initial status '{task.status.value}'. "
                    f"Expected 'pending'."
                )

        is_valid = len(errors) == 0
        if is_valid:
            logger.info("SupervisorValidator: plan validation passed", plan_id=plan.id)
        else:
            logger.warning(
                "SupervisorValidator: plan validation failed",
                plan_id=plan.id,
                errors=errors,
            )
        return PlanValidationResult(is_valid=is_valid, errors=errors)


# ---------------------------------------------------------------------------
# Cycle Detection Helper
# ---------------------------------------------------------------------------


def _detect_cycle(plan: ExecutionPlan) -> str | None:
    """
    DFS-based cycle detection on the task dependency graph.

    Returns an error string if a cycle is found, None otherwise.
    """
    adjacency: Dict[str, List[str]] = {t.id: list(t.dependencies) for t in plan.tasks}

    visited: Set[str] = set()
    rec_stack: Set[str] = set()

    def dfs(node: str) -> bool:
        visited.add(node)
        rec_stack.add(node)
        for neighbour in adjacency.get(node, []):
            if neighbour not in visited:
                if dfs(neighbour):
                    return True
            elif neighbour in rec_stack:
                return True
        rec_stack.discard(node)
        return False

    for task_id in adjacency:
        if task_id not in visited:
            if dfs(task_id):
                return (
                    f"Circular dependency detected in ExecutionPlan '{plan.id}'. "
                    "Tasks form a dependency cycle."
                )
    return None
