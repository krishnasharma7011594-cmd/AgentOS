"""Supervisor Memory Bridge interface and concrete implementation."""

from abc import ABC, abstractmethod

from core.logging.logger import logger
from core.memory.interfaces.base import BaseMemory
from core.memory.service import MemoryService
from core.models.domain import ExecutionResult, Goal


class BaseSupervisorMemoryBridge(ABC):
    """Abstract interface for bridging Supervisor actions with core layered memory."""

    def __init__(self, memory: BaseMemory):
        self.memory = memory

    @abstractmethod
    async def record_goal(self, goal: Goal) -> None:
        """Store goal in memory."""
        pass

    @abstractmethod
    async def record_execution(self, result: ExecutionResult) -> None:
        """Store execution result in memory."""
        pass


class SupervisorMemoryBridge:
    """Concrete memory bridge used by the orchestrator to persist outcomes."""

    def __init__(self, memory_service: MemoryService):
        self._memory_service = memory_service

    def persist_to_memory(
        self,
        goal: Goal,
        execution_result: ExecutionResult,
        metrics: object,
    ) -> None:
        """
        Persist execution summary and reflection artifacts to MemoryService.

        Called after execution + reflection complete. Never raises — any
        storage failure is logged and suppressed to preserve execution purity.
        """
        svc = self._memory_service

        try:
            # Persist execution summary
            exec_summary = (
                execution_result.response
                if isinstance(execution_result.response, str)
                else str(execution_result.response)
            )
            exec_attrs = {
                "execution_time_ms": getattr(metrics, "execution_time_ms", None),
                "total_tasks": getattr(metrics, "total_tasks", None),
                "failed_tasks": getattr(metrics, "failed_tasks", None),
            }
            svc.store_execution(
                goal_id=goal.id,
                summary=exec_summary,
                status=execution_result.status,
                attributes={k: v for k, v in exec_attrs.items() if v is not None},
            )
            logger.debug(
                "MemoryService: execution summary stored",
                goal_id=goal.id,
                status=execution_result.status,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "MemoryService: failed to store execution summary",
                goal_id=goal.id,
                error=str(exc),
            )

        # Persist reflection report if present
        if execution_result.report and execution_result.report.reflection_report:
            try:
                rr = execution_result.report.reflection_report
                reflection_content = rr.model_dump_json(indent=2)
                score = rr.scores.overall_score if rr.scores else None
                svc.store_reflection(
                    goal_id=goal.id,
                    content=reflection_content,
                    score=score,
                    attributes={
                        "reflection_version": rr.reflection_version,
                        "observation_count": len(rr.observations),
                        "recommendation_count": len(rr.recommendations),
                    },
                )
                logger.debug(
                    "MemoryService: reflection report stored",
                    goal_id=goal.id,
                    score=score,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "MemoryService: failed to store reflection report",
                    goal_id=goal.id,
                    error=str(exc),
                )
