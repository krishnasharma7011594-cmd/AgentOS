"""
EventEmitter

Lightweight execution event system for the AgentOS Adaptive Supervisor.

Phase 5 scope: Events are emitted to the structured logger and accumulated
in an internal list for inclusion in the final ExecutionReport.
No async infrastructure or subscriber registration is introduced yet.

Architecture Layer: Core / Execution / Events (Phase 5)
"""

from core.logging.logger import logger
from core.models.domain import EventType, ExecutionEvent


class EventEmitter:
    """
    Emits and stores ExecutionEvents for the current goal lifecycle.

    Events are written to the structured logger and stored in-memory so
    they can be included in the ExecutionReport at the end of execution.

    No async callbacks, queues, or subscriber patterns are introduced in
    Phase 5. Future phases may extend this class with a subscribe() method.

    Usage::

        emitter = EventEmitter(goal_id="goal-1")
        emitter.emit(EventType.TASK_STARTED, task_id="t1")
        events = emitter.get_events()
    """

    def __init__(self, goal_id: str) -> None:
        self._goal_id = goal_id
        self._events: list[ExecutionEvent] = []

    def emit(
        self,
        event_type: EventType,
        task_id: str | None = None,
        details: str = "",
    ) -> ExecutionEvent:
        """
        Create, log, and store an ExecutionEvent.

        Args:
            event_type: The type of lifecycle event.
            task_id:    Optional associated task ID.
            details:    Optional human-readable detail string.

        Returns:
            The created ExecutionEvent.
        """
        event = ExecutionEvent(
            event_type=event_type,
            task_id=task_id,
            details=details,
        )
        self._events.append(event)
        logger.info(
            "ExecutionEvent",
            goal_id=self._goal_id,
            event_type=event_type.value,
            task_id=task_id,
            details=details,
        )
        return event

    def get_events(self) -> list[ExecutionEvent]:
        """Return all events emitted so far (in chronological order)."""
        return list(self._events)

    def get_events_for_task(self, task_id: str) -> list[ExecutionEvent]:
        """Return all events associated with a specific task ID."""
        return [e for e in self._events if e.task_id == task_id]
