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

Phase 5 (Adaptive Supervisor):
  - Integrates TaskEvaluator for structured TaskEvaluation after every task.
  - Integrates DecisionEngine (pure) to produce structured Decision objects.
  - Integrates EventEmitter to emit and log execution lifecycle events.
  - Implements CONTINUE, RETRY, SKIP, REPLAN, TERMINATE decision branches.
  - Applies GraphMutation via ExecutionGraph.apply_mutation() for replanning.
  - Records every decision in MetricsCollector.DecisionLog.
  - Tracks retry attempts per task using an internal counter dictionary.

Architecture Layer: Supervisor / Orchestrator
"""

from core.context.engine import ContextEngine
from core.exceptions.base import PlanningError
from core.execution.events import EventEmitter
from core.execution.graph import ExecutionGraph
from core.execution.metrics import MetricsCollector
from core.logging.logger import logger
from core.memory.service import MemoryService
from core.models.context import PlannerInput
from core.models.domain import (
    EventType,
    ExecutionContext,
    ExecutionResult,
    Goal,
    TaskResult,
)
from core.parallel.analyzer import ExecutionDependencyResolver
from core.parallel.engine import ParallelExecutionEngine
from registry.agent_registry import AgentRegistry
from registry.capability_registry import CapabilityRegistry
from supervisor.decision_engine import DecisionEngine
from supervisor.decision_handler import SupervisorDecisionHandler
from supervisor.evaluator import TaskEvaluator
from supervisor.memory_bridge import SupervisorMemoryBridge
from supervisor.planner import SupervisorPlanner
from supervisor.policies import RetryPolicy
from supervisor.reflection.engine import ReflectionEngine
from supervisor.report_generator import SupervisorReportGenerator
from supervisor.router import SupervisorRouter
from supervisor.runner import SupervisorTaskRunner
from supervisor.validator import SupervisorValidator


class SupervisorOrchestrator:
    """
    Central orchestrator coordinating goal fulfillment across AgentOS.

    Owns the high-level workflow state machine:
        1. Receive Goal from API layer.
        2. Invoke SupervisorPlanner to generate ExecutionPlan.
        3. Validate the plan via SupervisorValidator.validate_plan().
        4. Build ExecutionGraph from the validated plan.
        5. Iterate through READY tasks, executing via SupervisorTaskRunner.
        6. Validate individual task results.
        7. Synthesize final report via SupervisorReportGenerator.
        8. Reflect on execution.
        9. Persist to Memory subsystem.

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
        retry_policy: RetryPolicy | None = None,
        memory_service: MemoryService | None = None,
        context_engine: ContextEngine | None = None,
        parallel_engine: ParallelExecutionEngine | None = None,
        dependency_resolver: ExecutionDependencyResolver | None = None,
    ) -> None:
        self.agent_registry = agent_registry
        self.capability_registry = capability_registry
        self.planner = planner
        self.router = router
        self.validator = validator
        self.report_generator = report_generator

        # Core engines
        self._context_engine = context_engine
        self._reflection_engine = ReflectionEngine()

        # Memory Bridge
        self._memory_bridge = None
        if memory_service:
            self._memory_bridge = SupervisorMemoryBridge(memory_service)

        # Decision Handling
        self._decision_handler = SupervisorDecisionHandler(
            planner=planner,
            context_engine=context_engine,
        )

        # Task Runner
        self._runner = SupervisorTaskRunner(
            router=router,
            evaluator=TaskEvaluator(),
            decision_engine=DecisionEngine(retry_policy=retry_policy or RetryPolicy()),
            decision_handler=self._decision_handler,
            parallel_engine=parallel_engine,
            dependency_resolver=dependency_resolver,
        )

        logger.info(
            "SupervisorOrchestrator: initialized"
            " (Phase 5+6+7+9 — Adaptive+Reflective+Memory+Parallel)"
        )

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

        # ── Step 1: Generate Planner Context & Decompose Goal ─────────────
        planner_context = None
        if self._context_engine:
            from core.models.context import ContextRequest, ContextScope

            planner_context = self._context_engine.build_context(
                ContextRequest(
                    goal_id=goal.id,
                    goal_description=goal.description,
                    scope=ContextScope.PLANNER,
                )
            )

        planner_input = PlannerInput(
            goal_id=goal.id,
            goal_description=goal.description,
            context=planner_context,
        )

        try:
            plan = await self.planner.create_plan(planner_input)
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

        # ── Step 2: Validate the plan ─────────────────────────────────────
        plan_validation = self.validator.validate_plan(plan)
        if not plan_validation.is_valid:
            errors_text = "; ".join(plan_validation.errors)
            logger.error(
                "SupervisorOrchestrator: plan validation failed",
                goal_id=goal.id,
                errors=plan_validation.errors,
            )
            return self._error_result(goal, f"Plan validation failed: {errors_text}")

        # ── Step 3: Build execution graph, metrics, and event emitter ─────
        graph = ExecutionGraph(plan)
        graph.initialize()

        collector = MetricsCollector()
        collector.start_goal()
        emitter = EventEmitter(goal_id=goal.id)

        agent_context = None
        if self._context_engine:
            from core.models.context import ContextRequest, ContextScope

            agent_context = self._context_engine.build_context(
                ContextRequest(
                    goal_id=goal.id,
                    goal_description=goal.description,
                    scope=ContextScope.AGENT,
                )
            )

        context = ExecutionContext(goal_id=goal.id, context_bundle=agent_context)
        task_results: list[TaskResult] = []

        # attempt_counts tracks how many times each task has been retried
        attempt_counts: dict[str, int] = {}

        # ── Step 4: Adaptive execution loop ──────────────────────────────
        if self._runner._parallel_engine and self._runner._dependency_resolver:
            await self._runner.run_parallel_loop(
                goal=goal,
                graph=graph,
                context=context,
                collector=collector,
                emitter=emitter,
                task_results=task_results,
                attempt_counts=attempt_counts,
            )
        else:
            await self._runner.run_sequential_loop(
                goal=goal,
                graph=graph,
                context=context,
                collector=collector,
                emitter=emitter,
                task_results=task_results,
                attempt_counts=attempt_counts,
            )

        # ── Step 5: Emit execution finished, finalise metrics ─────────────

        emitter.emit(EventType.EXECUTION_FINISHED, details=f"goal_id={goal.id}")
        metrics = collector.finalize(total_tasks=graph.task_count)

        # ── Step 6: Validate individual task results ──────────────────────
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

        # ── Step 7: Synthesize final report ───────────────────────────────
        execution_result = await self.report_generator.generate_report(
            goal, task_results, validations, metrics
        )

        # ── Step 8: Reflect on execution (Phase 6) ────────────────────────
        if execution_result.report:
            reflection_report = self._reflection_engine.reflect(execution_result.report)
            execution_result.report.reflection_report = reflection_report

        # ── Step 9: Persist to Memory subsystem (Phase 7) ─────────────────
        if self._memory_bridge:
            self._memory_bridge.persist_to_memory(goal, execution_result, metrics)

        logger.info(
            "SupervisorOrchestrator: execution complete",
            goal_id=goal.id,
            status=execution_result.status,
            execution_time_ms=metrics.execution_time_ms,
            retries=collector.retry_count,
            inserted_tasks=collector.inserted_task_count,
            decisions=len(collector.get_decision_log()),
            reflection_score=(
                execution_result.report.reflection_report.scores.overall_score
                if execution_result.report and execution_result.report.reflection_report
                else None
            ),
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
