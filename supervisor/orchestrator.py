"""
Supervisor Orchestrator

Master coordinator for AgentOS multi-agent workflow execution.
Sequences execution across decomposed supervisor components:
Planner, Router, Validator, and ReportGenerator.

Phase 4.5:
  - Uses ExecutionGraph for task state machine instead of a raw task loop.
  - Calls SupervisorValidator.validate_plan() before execution.
  - Collects ExecutionMetrics via MetricsCollector.
  - Passes metrics to ReportGenerator for rich ExecutionReport.
  - Uses SKIPPED (not FAILED) for dependency-cascade tasks.

Architecture Layer: Supervisor / Orchestrator
"""

from core.exceptions.base import AgentOSError, PlanningError
from core.execution.graph import ExecutionGraph
from core.execution.metrics import MetricsCollector
from core.logging.logger import logger
from core.models.domain import (
    ExecutionContext,
    ExecutionResult,
    Goal,
    TaskResult,
    TaskStatus,
)
from registry.agent_registry import AgentRegistry
from registry.capability_registry import CapabilityRegistry
from supervisor.planner import SupervisorPlanner
from supervisor.report_generator import SupervisorReportGenerator
from supervisor.router import SupervisorRouter
from supervisor.validator import SupervisorValidator


class SupervisorOrchestrator:
    """
    Central orchestrator coordinating goal fulfillment across AgentOS.

    Owns the high-level workflow state machine:
        1. Receive Goal from API layer.
        2. Invoke SupervisorPlanner to generate ExecutionPlan.
        3. Validate the plan via SupervisorValidator.validate_plan().
        4. Build ExecutionGraph from the validated plan.
        5. Iterate through READY tasks, executing via SupervisorRouter.
        6. Update graph state after each task (SUCCESS / FAILED / SKIPPED).
        7. Collect metrics throughout execution.
        8. Validate outcomes via SupervisorValidator.validate_result().
        9. Synthesize final response via SupervisorReportGenerator.

    Does NOT import concrete agent modules directly — discovers agents via CapabilityRegistry.
    Dependencies are injected via constructor.
    """

    def __init__(
        self,
        agent_registry: AgentRegistry,
        capability_registry: CapabilityRegistry,
        planner: SupervisorPlanner,
        router: SupervisorRouter,
        validator: SupervisorValidator,
        report_generator: SupervisorReportGenerator,
    ) -> None:
        self.agent_registry = agent_registry
        self.capability_registry = capability_registry
        self.planner = planner
        self.router = router
        self.validator = validator
        self.report_generator = report_generator
        logger.info("SupervisorOrchestrator: initialized")

    async def execute_goal(self, goal: Goal) -> ExecutionResult:
        """
        Main orchestration pipeline entry point called by the API app layer.

        Args:
            goal: Goal entity containing user objective.

        Returns:
            ExecutionResult: Synthesized final output payload.
        """
        logger.info(
            "SupervisorOrchestrator: received goal",
            goal_id=goal.id,
            description=goal.description,
        )

        # ── Step 1: Decompose goal into execution plan ───────────────────
        try:
            plan = await self.planner.create_plan(goal)
        except PlanningError as exc:
            logger.error(
                "SupervisorOrchestrator: planning failed",
                goal_id=goal.id,
                error=str(exc),
            )
            return self._error_result(goal, f"Planning failed: {exc}")

        logger.info(
            "SupervisorOrchestrator: plan ready",
            goal_id=goal.id,
            plan_id=plan.id,
            task_count=len(plan.tasks),
        )

        # ── Step 2: Validate the plan ────────────────────────────────────
        plan_validation = self.validator.validate_plan(plan)
        if not plan_validation.is_valid:
            errors_text = "; ".join(plan_validation.errors)
            logger.error(
                "SupervisorOrchestrator: plan validation failed",
                goal_id=goal.id,
                errors=plan_validation.errors,
            )
            return self._error_result(goal, f"Plan validation failed: {errors_text}")

        # ── Step 3: Build execution graph and start metrics ──────────────
        graph = ExecutionGraph(plan)
        graph.initialize()

        collector = MetricsCollector()
        collector.start_goal()

        context = ExecutionContext(goal_id=goal.id)
        task_results: list[TaskResult] = []

        # ── Step 4: Execute tasks via the graph ──────────────────────────
        # Sequential execution: process all READY tasks each round, then advance.
        while not graph.is_complete():
            ready_tasks = graph.get_ready_tasks()
            if not ready_tasks:
                # No ready tasks and graph not complete = stuck (shouldn't happen
                # after validate_plan, but guard against unexpected states)
                logger.warning(
                    "SupervisorOrchestrator: no ready tasks but graph not complete",
                    goal_id=goal.id,
                )
                break

            for task in ready_tasks:
                logger.info(
                    "SupervisorOrchestrator: executing task",
                    task_id=task.id,
                    task_name=task.name,
                    capability=task.required_capability,
                )
                graph.mark_task_running(task.id)
                collector.start_task(task.id)

                try:
                    result = await self.router.route_task(task, context)
                except AgentOSError as exc:
                    logger.error(
                        "SupervisorOrchestrator: task routing failed",
                        task_id=task.id,
                        error=str(exc),
                    )
                    result = TaskResult(
                        task_id=task.id,
                        agent_id="supervisor",
                        status=TaskStatus.FAILED,
                        summary="",
                        error=str(exc),
                    )

                # Record result in collector and context
                collector.end_task(task.id, result.agent_id, result)
                context.results[task.id] = result
                task_results.append(result)

                # Update graph state
                if result.status == TaskStatus.SUCCESS:
                    graph.mark_task_success(task.id, result)
                else:
                    graph.mark_task_failed(task.id, result)

            # Advance: promote PENDING tasks whose deps are now resolved
            graph.advance()

            # Mark any newly-skipped tasks in results
            for skipped_task in graph.get_skipped_tasks():
                if skipped_task.id not in context.results:
                    skip_result = TaskResult(
                        task_id=skipped_task.id,
                        agent_id="supervisor",
                        status=TaskStatus.SKIPPED,
                        summary="Skipped: a required dependency failed or was skipped.",
                    )
                    context.results[skipped_task.id] = skip_result
                    task_results.append(skip_result)
                    collector.start_task(skipped_task.id)
                    collector.end_task(skipped_task.id, "supervisor", skip_result)

        # ── Step 5: Finalise metrics ─────────────────────────────────────
        metrics = collector.finalize(total_tasks=graph.task_count)

        # ── Step 6: Validate individual task results ─────────────────────
        validations = []
        for result in task_results:
            validation = await self.validator.validate_result(goal, result)
            validations.append(validation)
            logger.info(
                "SupervisorOrchestrator: validation",
                task_id=result.task_id,
                is_valid=validation.is_valid,
                reason=validation.reason,
            )

        # ── Step 7: Synthesize final report ─────────────────────────────
        execution_result = await self.report_generator.generate_report(
            goal, task_results, validations, metrics
        )

        logger.info(
            "SupervisorOrchestrator: execution complete",
            goal_id=goal.id,
            status=execution_result.status,
            execution_time_ms=metrics.execution_time_ms,
        )
        return execution_result

    @staticmethod
    def _error_result(goal: Goal, message: str) -> ExecutionResult:
        """Helper constructing a failed ExecutionResult fallback payload."""
        return ExecutionResult(
            goal_id=goal.id,
            status="failed",
            response=message,
            tasks=[],
        )
