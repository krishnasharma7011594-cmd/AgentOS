"""
Parallel Execution Domain Models

Defines the core data structures for the Phase 9 Parallel Execution Engine.
All models are strictly serializable.

Architecture Layer: Core / Models
"""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from core.models.domain import Task, TaskResult
from core.utils.helpers import generate_uuid


class WorkerStatus(str, Enum):
    """Current state of a TaskExecutor / Worker."""

    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"


class BatchStatus(str, Enum):
    """Lifecycle status of an ExecutionBatch."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ExecutionPolicy(BaseModel):
    """
    Configuration policy dictating parallel execution constraints.
    Injectable for dynamic environment adjustments.
    """

    max_workers: int = Field(default=4, description="Maximum number of active task executors.")
    timeout_ms: int = Field(default=60000, description="Default timeout per task in ms.")
    max_parallelism: int = Field(
        default=10, description="Hard cap on concurrent tasks across all pools."
    )


class ExecutionCancellationToken(BaseModel):
    """
    Cooperative cancellation flag for future-proofing task interruption.
    """

    is_cancelled: bool = Field(default=False)
    reason: Optional[str] = None

    def cancel(self, reason: str) -> None:
        self.is_cancelled = True
        self.reason = reason


class WorkerException(BaseModel):
    """Captures an exception that occurred in an isolated worker."""

    task_id: str
    error_type: str
    message: str
    traceback_str: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BatchResult(BaseModel):
    """Aggregated result of a single parallel execution batch."""

    batch_id: str
    successful_results: List[TaskResult] = Field(default_factory=list)
    failed_results: List[TaskResult] = Field(default_factory=list)
    exceptions: List[WorkerException] = Field(default_factory=list)

    @property
    def has_failures(self) -> bool:
        return len(self.failed_results) > 0 or len(self.exceptions) > 0


class ExecutionMetrics(BaseModel):
    """Telemetry for the parallel execution engine."""

    utilization_percent: float = 0.0
    queue_length: int = 0
    idle_workers: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    average_batch_size: float = 0.0


class BatchExecutionPlan(BaseModel):
    """
    An immutable snapshot of tasks ready to execute simultaneously.
    Returned by the ExecutionDependencyResolver.
    """

    model_config = ConfigDict(frozen=True)

    tasks: List[Task] = Field(..., description="Independent tasks ready for execution.")

    @property
    def is_empty(self) -> bool:
        return len(self.tasks) == 0


class ExecutionBatch(BaseModel):
    """
    A live execution batch managed by the scheduler and synchronized via a barrier.
    """

    id: str = Field(default_factory=generate_uuid)
    plan: BatchExecutionPlan
    status: BatchStatus = Field(default=BatchStatus.PENDING)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    result: Optional[BatchResult] = None
