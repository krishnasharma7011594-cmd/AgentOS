"""
Supervisor Orchestrator

Master coordinator for AgentOS multi-agent workflow execution.
Sequences execution across decomposed supervisor components:
Planner, Router, Validator, and ReportGenerator.

Architecture Layer: Supervisor / Orchestrator
"""

from core.exceptions.base import AgentOSError, PlanningError
from core.logging.logger import logger
from core.models.domain import ExecutionResult, Goal, TaskResult, TaskStatus
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
        3. Iterate through tasks and invoke SupervisorRouter.
        4. Validate outcomes via SupervisorValidator.
        5. Synthesize final response via SupervisorReportGenerator.

    Does NOT import concrete agent modules directly — discovers agents via CapabilityRegistry.
    Dependencies are injected via constructor.

    TODO: Support parallel task execution for independent tasks in Phase 3.
    TODO: Add automated task retries on recoverable agent failures.
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
        """
        Initializes SupervisorOrchestrator with injected supervisor services and registries.

        Args:
            agent_registry: AgentRegistry instance.
            capability_registry: CapabilityRegistry instance.
            planner: SupervisorPlanner instance.
            router: SupervisorRouter instance.
            validator: SupervisorValidator instance.
            report_generator: SupervisorReportGenerator instance.
        """
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

        # Step 1: Decompose goal into execution plan
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

        # Step 2: Route and execute tasks sequentially
        task_results: list[TaskResult] = []
        for task in plan.tasks:
            logger.info(
                "SupervisorOrchestrator: executing task",
                task_id=task.id,
                task_name=task.name,
                capability=task.required_capability,
            )
            try:
                result = await self.router.route_task(task)
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
            task_results.append(result)

        # Step 3: Validate task execution results
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

        # Step 4: Synthesize final execution report
        execution_result = await self.report_generator.generate_report(
            goal, task_results, validations
        )

        logger.info(
            "SupervisorOrchestrator: execution complete",
            goal_id=goal.id,
            status=execution_result.status,
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
