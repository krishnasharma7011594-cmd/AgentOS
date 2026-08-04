"""
Supervisor Decision Handler

Responsible for taking a Decision (from the DecisionEngine) and mutating
the ExecutionGraph, emitting telemetry, and updating attempt counts.
"""

from typing import Optional

from core.context.engine import ContextEngine
from core.execution.events import EventEmitter
from core.execution.graph import ExecutionGraph
from core.execution.metrics import MetricsCollector
from core.logging.logger import logger
from core.models.domain import (
    Decision,
    DecisionType,
    EventType,
    ExecutionContext,
    FailureCategory,
    Goal,
    GraphMutation,
    ReplanRequest,
    Task,
    TaskEvaluation,
    TaskResult,
)
from supervisor.planner import SupervisorPlanner

# Maximum retry budget as a hard safety cap (independent of per-category policy)
_GLOBAL_MAX_RETRIES = 10


class SupervisorDecisionHandler:
    """Applies decisions from the DecisionEngine to the execution workflow."""

    def __init__(
        self,
        planner: SupervisorPlanner,
        context_engine: Optional[ContextEngine] = None,
    ):
        self.planner = planner
        self._context_engine = context_engine

    async def apply_decision(
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
                    "SupervisorDecisionHandler: global retry cap hit, forcing SKIP",
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
            replan_context = None
            if self._context_engine:
                from core.models.context import ContextRequest, ContextScope

                replan_context = self._context_engine.build_context(
                    ContextRequest(
                        goal_id=goal.id,
                        goal_description=goal.description,
                        task_id=task.id,
                        task_description=task.description,
                        scope=ContextScope.SUPERVISOR,
                    )
                )

            replan_request = ReplanRequest(
                goal_id=goal.id,
                failed_task_id=task.id,
                evaluation=evaluation,
                context_summary=context_summary,
                context_bundle=replan_context,
            )
            logger.info(
                "SupervisorDecisionHandler: replanning",
                failed_task_id=replan_request.failed_task_id,
            )
            try:
                new_tasks = await self.planner.create_recovery_tasks(replan_request)
            except Exception as exc:
                logger.warning(
                    "SupervisorDecisionHandler: replanning failed, falling back to SKIP",
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
                        "SupervisorDecisionHandler: graph mutation rejected",
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
                "SupervisorDecisionHandler: terminating execution",
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
