"""Workflow state enumeration."""

from enum import Enum


class WorkflowState(str, Enum):
    """Execution states for tasks moving through AgentOS workflow engine."""

    PLANNING = "Planning"
    QUEUED = "Queued"
    RUNNING = "Running"
    WAITING = "Waiting"
    COMPLETED = "Completed"
    FAILED = "Failed"
    CANCELLED = "Cancelled"
