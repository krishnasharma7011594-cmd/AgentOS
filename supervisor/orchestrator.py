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

from core.exceptions.base import AgentOSError, PlanningError
from core.execution.events import EventEmitter
from core.execution.graph import ExecutionGraph
from core.execution.metrics import MetricsCollector
from core.logging.logger import logger
from core.models.domain import (
    Decision,
    DecisionContext,
    DecisionLogEntry,
    DecisionType,
    EventType,
    ExecutionContext,
    ExecutionResult,
    FailureCategory,
    Goal,
    GraphMutation,
    ReplanRequest,
    Task,
    TaskEvaluation,
    TaskResult,
    TaskStatus,
)
from registry.agent_registry import AgentRegistry
from registry.capability_registry import CapabilityRegistry
from supervisor.decision_engine import DecisionEngine
from supervisor.evaluator import TaskEvaluator
from supervisor.planner import SupervisorPlanner
from supervisor.policies import RetryPolicy
from supervisor.report_generator import SupervisorReportGenerator
from supervisor.router import SupervisorRouter
from supervisor.validator import SupervisorValidator

# Maximum retry budget as a hard safety cap (independent of per-category policy)
_GLOBAL_MAX_RETRIES = 10


class SupervisorOrchestrator:
    """
    Central orchestrator coordinating goal fulfillment across AgentOS.

    Owns the high-level workflow state machine:
        1. Receive Goal from API layer.
        2. Invoke SupervisorPlanner to generate ExecutionPlan.
        3. Validate the plan via SupervisorValidator.validate_plan().
        4. Build ExecutionGraph from the validated plan.
        5. Iterate through READY tasks, executing via SupervisorRouter.
        6. Evaluate each TaskResult via TaskEvaluator.
        7. Make structured Decision via DecisionEngine.
        8. Apply the decision (CONTINUE/RETRY/SKIP/REPLAN/TERMINATE).
        9. Collect metrics and decision log throughout execution.
       10. Validate outcomes via SupervisorValidator.validate_result().
       11. Synthesize final response via SupervisorReportGenerator.

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
    ) -> None:
        self.agent_registry = agent_registry
        self.capability_registry = capability_registry
        self.planner = planner
        self.router = router
        self.validator = validator
        self.report_generator = report_generator
        self._evaluator = TaskEvaluator()
        self._decision_engine = DecisionEngine(retry_policy=retry_policy or RetryPolicy())
        logger.info("SupervisorOrchestrator: initialized (Phase 5 — Adaptive)")

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

        # ── Step 1: Decompose goal into execution plan ────────────────────
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

        context = ExecutionContext(goal_id=goal.id)
        task_results: list[TaskResult] = []

        # attempt_counts tracks how many times each task has been retried
        attempt_counts: dict[str, int] = {}
        terminated = False

        # ── Step 4: Adaptive execution loop ──────────────────────────────
        while not graph.is_complete() and not terminated:
            ready_tasks = graph.get_ready_tasks()
            if not ready_tasks:
                logger.warning(
                    "SupervisorOrchestrator: no ready tasks but graph not complete",
                    goal_id=goal.id,
                )
                break

            for task in ready_tasks:
                if terminated:
                    break

                emitter.emit(EventType.TASK_STARTED, task_id=task.id, details=task.name)
                logger.info(
                    "SupervisorOrchestrator: executing task",
                    task_id=task.id,
                    task_name=task.name,
                    capability=task.required_capability,
                    attempt=attempt_counts.get(task.id, 0),
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

                collector.end_task(task.id, result.agent_id, result)

                # ── Evaluate and decide ───────────────────────────────────
                evaluation = self._evaluator.evaluate(task, result)
                attempt = attempt_counts.get(task.id, 0)

                decision_ctx = DecisionContext(
                    task_id=task.id,
                    evaluation=evaluation,
                    attempt_count=attempt,
                    pending_count=len(graph.get_remaining_tasks()),
                    failed_count=len(graph.get_failed_tasks()),
                )
                decision = self._decision_engine.make_decision(decision_ctx)

                # Log every decision
                log_entry = DecisionLogEntry(
                    task_id=task.id,
                    decision=decision,
                    evaluation=evaluation,
                    attempt_count=attempt,
                )
                collector.record_decision(log_entry)

                logger.info(
                    "SupervisorOrchestrator: decision",
                    task_id=task.id,
                    decision=decision.decision_type.value,
                    reason=decision.reason,
                )

                # ── Apply decision ────────────────────────────────────────
                terminated = await self._apply_decision(
                    decision=decision,
                    task=task,
                    result=result,
                    evaluation=evaluation,
                    graph=graph,
                    collector=collector,
                    emitter=emitter,
                    context=context,
                    task_results=task_results,
                    attempt_counts=attempt_counts,
                    goal=goal,
                )
                if terminated:
                    break

            # Advance: promote PENDING tasks whose deps are now resolved
            graph.advance()

            # Record any newly-skipped tasks
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
                    emitter.emit(
                        EventType.TASK_SKIPPED,
                        task_id=skipped_task.id,
                        details="Dependency cascade skip.",
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

        logger.info(
            "SupervisorOrchestrator: execution complete",
            goal_id=goal.id,
            status=execution_result.status,
            execution_time_ms=metrics.execution_time_ms,
            retries=collector.retry_count,
            inserted_tasks=collector.inserted_task_count,
            decisions=len(collector.get_decision_log()),
        )
        return execution_result

    async def _apply_decision(
        self,
        decision: Decision,
        task: Task,
        result: TaskResult,
        evaluation: TaskEvaluation,
        graph: ExecutionGraph,
        collector: MetricsCollector,
        emitter: EventEmitter,
        context: ExecutionContext,
        task_results: list[TaskResult],
        attempt_counts: dict[str, int],
        goal: Goal,
    ) -> bool:
        """
        Apply a supervisor Decision and return True when execution should terminate.

        Args:
            decision:       The Decision from DecisionEngine.
            task:           The task just executed.
            result:         The raw TaskResult.
            evaluation:     Structured evaluation used to produce the decision.
            graph:          Live ExecutionGraph to mutate if needed.
            collector:      MetricsCollector for telemetry.
            emitter:        EventEmitter for lifecycle events.
            context:        ExecutionContext for cross-task sharing.
            task_results:   Accumulated list of TaskResult records.
            attempt_counts: Per-task retry counter dict.
            goal:           The parent Goal for replanning context.

        Returns:
            True if execution should be terminated, False otherwise.
        """
        dt = decision.decision_type

        # ── CONTINUE ─────────────────────────────────────────────────────
        if dt == DecisionType.CONTINUE:
            graph.mark_task_success(task.id, result)
            context.results[task.id] = result
            task_results.append(result)
            emitter.emit(
                EventType.TASK_COMPLETED,
                task_id=task.id,
                details="Success.",
            )
            return False

        # ── RETRY ─────────────────────────────────────────────────────────
        if dt == DecisionType.RETRY:
            attempt_counts[task.id] = attempt_counts.get(task.id, 0) + 1
            category = evaluation.failure_category or FailureCategory.UNKNOWN
            collector.record_retry(task.id, category)
            # Safety cap
            if attempt_counts[task.id] >= _GLOBAL_MAX_RETRIES:
                logger.warning(
                    "SupervisorOrchestrator: global retry cap hit, forcing SKIP",
                    task_id=task.id,
                )
                graph.mark_task_failed(task.id, result)
                context.results[task.id] = result
                task_results.append(result)
                emitter.emit(
                    EventType.TASK_FAILED,
                    task_id=task.id,
                    details="Global retry cap reached.",
                )
                return False
            # Put the task back in READY for the next loop iteration
            graph.mark_task_failed(task.id, result)
            graph.mark_task_ready(task.id)
            emitter.emit(
                EventType.TASK_RETRIED,
                task_id=task.id,
                details=f"Attempt {attempt_counts[task.id]}. Reason: {decision.reason}",
            )
            return False

        # ── SKIP ──────────────────────────────────────────────────────────
        if dt == DecisionType.SKIP:
            graph.mark_task_failed(task.id, result)
            context.results[task.id] = result
            task_results.append(result)
            emitter.emit(
                EventType.TASK_FAILED,
                task_id=task.id,
                details=f"Skipped by supervisor. Reason: {decision.reason}",
            )
            return False

        # ── REPLAN ────────────────────────────────────────────────────────
        if dt == DecisionType.REPLAN:
            context_summary = "; ".join(
                f"{tid}: {r.status.value}" for tid, r in context.results.items()
            )
            replan_request = ReplanRequest(
                goal_id=goal.id,
                failed_task_id=task.id,
                evaluation=evaluation,
                context_summary=context_summary,
            )
            logger.info(
                "SupervisorOrchestrator: replanning",
                failed_task_id=replan_request.failed_task_id,
            )
            try:
                new_tasks = await self.planner.create_recovery_tasks(replan_request)
            except Exception as exc:
                logger.warning(
                    "SupervisorOrchestrator: replanning failed, falling back to SKIP",
                    task_id=task.id,
                    error=str(exc),
                )
                graph.mark_task_failed(task.id, result)
                context.results[task.id] = result
                task_results.append(result)
                emitter.emit(
                    EventType.TASK_FAILED,
                    task_id=task.id,
                    details="Replan failed, task skipped.",
                )
                return False

            if new_tasks:
                mutation = GraphMutation(
                    new_tasks=new_tasks,
                    before_task_ids=[],  # new tasks run independently; original task is skipped
                )
                try:
                    graph.apply_mutation(mutation)
                    for new_task in new_tasks:
                        collector.record_inserted_task(new_task.id)
                        emitter.emit(
                            EventType.TASK_INSERTED,
                            task_id=new_task.id,
                            details=f"Inserted via replan for failed task {task.id}.",
                        )
                except ValueError as exc:
                    logger.warning(
                        "SupervisorOrchestrator: graph mutation rejected",
                        error=str(exc),
                    )

            # Mark the original failed task as failed (it triggered the replan)
            graph.mark_task_failed(task.id, result)
            context.results[task.id] = result
            task_results.append(result)
            return False

        # ── TERMINATE ─────────────────────────────────────────────────────
        if dt == DecisionType.TERMINATE:
            logger.warning(
                "SupervisorOrchestrator: terminating execution",
                task_id=task.id,
                reason=decision.reason,
            )
            graph.mark_task_failed(task.id, result)
            context.results[task.id] = result
            task_results.append(result)
            emitter.emit(
                EventType.TASK_FAILED,
                task_id=task.id,
                details=f"Execution terminated. Reason: {decision.reason}",
            )
            return True  # signal the outer loop to stop

        # Unreachable — all DecisionType values handled above
        return False

    @staticmethod
    def _error_result(goal: Goal, message: str) -> ExecutionResult:
        """Helper constructing a failed ExecutionResult fallback payload."""
        return ExecutionResult(
            goal_id=goal.id,
            status="failed",
            response=message,
            tasks=[],
        )
