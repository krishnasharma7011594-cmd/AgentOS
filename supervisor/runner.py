"""
Supervisor Task Runner

Responsible for executing the ExecutionGraph task loops, both sequentially
and in parallel, and coordinating with the DecisionHandler for failure recovery.
"""

from typing import Optional

from core.exceptions.base import AgentOSError
from core.execution.events import EventEmitter
from core.execution.graph import ExecutionGraph
from core.execution.metrics import MetricsCollector
from core.logging.logger import logger
from core.models.domain import (
    DecisionContext,
    DecisionLogEntry,
    EventType,
    ExecutionContext,
    Goal,
    TaskResult,
    TaskStatus,
)
from core.parallel.analyzer import ExecutionDependencyResolver
from core.parallel.engine import ParallelExecutionEngine
from supervisor.decision_engine import DecisionEngine
from supervisor.decision_handler import SupervisorDecisionHandler
from supervisor.evaluator import TaskEvaluator
from supervisor.router import SupervisorRouter


class SupervisorTaskRunner:
    """Manages the graph execution loops."""

    def __init__(
        self,
        router: SupervisorRouter,
        evaluator: TaskEvaluator,
        decision_engine: DecisionEngine,
        decision_handler: SupervisorDecisionHandler,
        parallel_engine: Optional[ParallelExecutionEngine] = None,
        dependency_resolver: Optional[ExecutionDependencyResolver] = None,
    ):
        self.router = router
        self._evaluator = evaluator
        self._decision_engine = decision_engine
        self._decision_handler = decision_handler
        self._parallel_engine = parallel_engine
        self._dependency_resolver = dependency_resolver

    async def run_parallel_loop(
        self,
        goal: Goal,
        graph: ExecutionGraph,
        context: ExecutionContext,
        collector: MetricsCollector,
        emitter: EventEmitter,
        task_results: list[TaskResult],
        attempt_counts: dict[str, int],
    ) -> bool:
        from core.models.parallel import ExecutionCancellationToken

        assert self._dependency_resolver is not None
        assert self._parallel_engine is not None

        terminated = False

        while not graph.is_complete() and not terminated:
            batch_plan = self._dependency_resolver.resolve(graph)

            if batch_plan.is_empty:
                if self._dependency_resolver.has_deadlock(graph):
                    logger.error(
                        "SupervisorTaskRunner: execution deadlock detected.",
                        goal_id=goal.id,
                    )
                else:
                    logger.warning(
                        "SupervisorTaskRunner: no ready tasks but graph not complete",
                        goal_id=goal.id,
                    )
                break

            cancel_token = ExecutionCancellationToken()

            for task in batch_plan.tasks:
                emitter.emit(EventType.TASK_STARTED, task_id=task.id, details=task.name)
                graph.mark_task_running(task.id)
                collector.start_task(task.id)
                logger.info(
                    "SupervisorTaskRunner: queueing task in batch",
                    task_id=task.id,
                    task_name=task.name,
                    attempt=attempt_counts.get(task.id, 0),
                )

            batch_result = await self._parallel_engine.execute_batch(
                plan=batch_plan,
                context=context,
                cancellation_token=cancel_token,
                event_emitter=emitter,
            )

            all_results = batch_result.successful_results + batch_result.failed_results

            for result in all_results:
                task = graph._tasks[result.task_id]
                collector.end_task(task.id, result.agent_id, result)

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

                log_entry = DecisionLogEntry(
                    task_id=task.id,
                    decision=decision,
                    evaluation=evaluation,
                    attempt_count=attempt,
                )
                collector.record_decision(log_entry)

                logger.info(
                    "SupervisorTaskRunner: decision",
                    task_id=task.id,
                    decision=decision.decision_type.value,
                    reason=decision.reason,
                )

                terminated = await self._decision_handler.apply_decision(
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

            # Record any newly-skipped tasks
            graph.advance()
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

        return terminated

    async def run_sequential_loop(
        self,
        goal: Goal,
        graph: ExecutionGraph,
        context: ExecutionContext,
        collector: MetricsCollector,
        emitter: EventEmitter,
        task_results: list[TaskResult],
        attempt_counts: dict[str, int],
    ) -> bool:
        terminated = False

        while not graph.is_complete() and not terminated:
            ready_tasks = graph.get_ready_tasks()
            if not ready_tasks:
                running = graph.get_running_tasks()
                if not running:
                    logger.error(
                        "SupervisorTaskRunner: execution deadlock detected.",
                        goal_id=goal.id,
                    )
                else:
                    logger.warning(
                        "SupervisorTaskRunner: no ready tasks but graph not complete",
                        goal_id=goal.id,
                    )
                break
            task = ready_tasks[0]

            emitter.emit(EventType.TASK_STARTED, task_id=task.id, details=task.name)
            logger.info(
                "SupervisorTaskRunner: executing task",
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
                    "SupervisorTaskRunner: task routing failed",
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

            log_entry = DecisionLogEntry(
                task_id=task.id,
                decision=decision,
                evaluation=evaluation,
                attempt_count=attempt,
            )
            collector.record_decision(log_entry)

            logger.info(
                "SupervisorTaskRunner: decision",
                task_id=task.id,
                decision=decision.decision_type.value,
                reason=decision.reason,
            )

            terminated = await self._decision_handler.apply_decision(
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

            graph.advance()

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
        return terminated
